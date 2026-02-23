import dataclasses
import os
import pathlib
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
from typing import TYPE_CHECKING, Any

import colorama
import loguru
import orjson

import ralphlib.logger
import ralphlib.signals
import ralphlib.state
import ralphlib.types

if TYPE_CHECKING:
    import io

    from ralphlib.options import RalpherOptions


@dataclasses.dataclass
class IterationContext:
    cmd: list[str]
    iteration: int
    prompt: str
    background_id_to_tool: dict[str, str] = dataclasses.field(default_factory=dict)
    background_tools: dict[str, dict[str, str]] = dataclasses.field(default_factory=dict)
    complete: bool = False
    error: bool = False
    gil: threading.Lock = dataclasses.field(default_factory=threading.Lock)
    message_type_queue: list[ralphlib.types.MessageType] = dataclasses.field(default_factory=list)
    progress: pathlib.Path | None = None
    errors: pathlib.Path | None = None
    stderr: pathlib.Path | None = None
    stdout: pathlib.Path | None = None
    tools_used_set: set[str] = dataclasses.field(default_factory=set)
    unknown_tools: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)
    progressfd: io.TextIOWrapper | None = None
    stdoutfd: io.TextIOWrapper | None = None
    stderrfd: io.TextIOWrapper | None = None
    errorsfd: io.TextIOWrapper | None = None
    unknown_ptype_set: set[str] = dataclasses.field(default_factory=set)


SUBPROCESS_POLL_INTERVAL = 3

# regex to extract tool IDs from tool results that indicate a background tool has started, e.g. "Command running in background with ID: abc123."
tool_id_regex = re.compile(r'Command running in background with ID: (?P<id>\w+)\.')
# list of tools that are known to run in the background, and thus should be tracked for their IDs
background_tools_list = ['Bash']
# list tool names used to track background tasks
background_task_tool_name = ['TaskOutput', 'TaskStop']


def set_complete(context: IterationContext, value: bool) -> bool:
    with context.gil:
        context.complete = value
    return value


def get_complete(context: IterationContext) -> bool:
    with context.gil:
        value = context.complete
    return value


def set_error(context: IterationContext, value: bool) -> bool:
    with context.gil:
        context.error = value
    return value


def get_error(context: IterationContext) -> bool:
    with context.gil:
        value = context.error
    return value


def add_unknown_ptype(context: IterationContext, ptype: str) -> None:
    with context.gil:
        context.unknown_ptype_set.add(ptype)


def add_unknown_tool(context: IterationContext, tool_name: str, input_values: dict) -> None:
    with context.gil:
        if tool_name not in context.unknown_tools:
            context.unknown_tools[tool_name] = input_values


def add_background_tool(context: IterationContext, tool_name: str, tool_input: str, tool_id: str) -> None:
    with context.gil:
        context.background_tools[tool_id] = {
            'name': tool_name,
            'input': tool_input,
        }


def add_background_tool_id(context: IterationContext, tool_id: str, tid: str) -> None:
    with context.gil:
        context.background_id_to_tool[tid] = tool_id


def append_message_type(context: IterationContext, message_type: ralphlib.types.MessageType) -> None:
    with context.gil:
        context.message_type_queue.append(message_type)


def last_message_type(context: IterationContext) -> ralphlib.types.MessageType | None:
    with context.gil:
        if context.message_type_queue:
            return context.message_type_queue[-1]
    return None


def run(options: RalpherOptions, prompt: str, iteration: int) -> tuple[bool, bool]:
    context = make_context(options, prompt, iteration)
    try:
        process(options, context)
    except Exception as e:
        loguru.logger.exception(f'Exception in run: {e}')
        raise
    finally:
        summary(options, context, iteration)
        unmake_context(context)
    return get_complete(context), get_error(context)


def make_context(options: RalpherOptions, prompt: str, iteration: int) -> IterationContext:
    cmd = [options.agent]
    cmd.extend(shlex.split(options.args))
    cmd.append(prompt)
    context = IterationContext(
        cmd=cmd,
        iteration=iteration,
        prompt=prompt,
    )
    try:
        if options.stdout:
            context.stdout = ralphlib.logger.log_file(options, options.stdout, iteration)
            context.stdoutfd = context.stdout.open('a', encoding='utf-8')
        if options.stderr:
            context.stderr = ralphlib.logger.log_file(options, options.stderr, iteration)
            context.stderrfd = context.stderr.open('a', encoding='utf-8')
        if options.progress:
            context.progress = ralphlib.logger.log_file(options, options.progress, iteration)
            context.progressfd = context.progress.open('a', encoding='utf-8')
        if options.errors:
            context.errors = ralphlib.logger.log_file(options, options.errors, iteration)
            context.errorsfd = context.errors.open('a', encoding='utf-8')
    except Exception as e:
        loguru.logger.exception(f'Exception in make_context: {e}')
        raise
    return context


def unmake_context(context: IterationContext) -> None:
    if context.stdoutfd:
        context.stdoutfd.flush()
        context.stdoutfd.close()
    if context.stderrfd:
        context.stderrfd.flush()
        context.stderrfd.close()
    if context.progressfd:
        context.progressfd.flush()
        context.progressfd.close()
    if context.errorsfd:
        context.errorsfd.flush()
        context.errorsfd.close()


def summary(options: RalpherOptions, context: IterationContext, iteration: int) -> None:
    state_payload = {}
    lines = []
    if context.tools_used_set:
        state_payload['tools_used'] = sorted(context.tools_used_set)
        tools = []
        for t in sorted(context.tools_used_set):
            tools.append(f'- {t}')
        tools_summary = '\n'.join(tools)
        lines.append(f'\nTools used:\n{tools_summary}\n')

    if context.unknown_tools:
        state_payload['unknown_tools'] = {}
        tools = []
        for t in sorted(context.unknown_tools.keys()):
            state_payload['unknown_tools'][t] = context.unknown_tools[t]
            tools.append(f'- {t}')
            keys = sorted(context.unknown_tools[t].keys())
            for k in keys:
                v = context.unknown_tools[t][k]
                tools.append(f'  - {k}: {v}')

        tools_summary = '\n'.join(tools)
        lines.append(f'\nUnknown tools used:\n{tools_summary}\n')

    if context.unknown_ptype_set:
        state_payload['unknown_ptypes'] = sorted(context.unknown_ptype_set)
        ptypes_summary = '\n'.join(f'- {t}' for t in sorted(context.unknown_ptype_set))
        lines.append(f'\nUnknown message types received:\n{ptypes_summary}\n')

    if lines:
        print_progress_lines(options, context, lines)
        write_progress_lines(options, context, lines)

        ralphlib.state.add_to_state(
            options,
            state_payload,
            key1='iterations',
            key2=ralphlib.logger.iteration_to_str(options, iteration),
        )


def print_progress_lines(options: RalpherOptions, context: IterationContext, lines: list[str]) -> None:
    if options.quiet:
        return
    with context.gil:
        for line in lines:
            print(line, end='', flush=True)


def print_progress(
    options: RalpherOptions,
    context: IterationContext,
    message_type: ralphlib.types.MessageType,
    message: str,
) -> None:
    if options.quiet:
        return
    msg_color = {
        ralphlib.types.MessageType.CONTENT_DELTA: colorama.Fore.CYAN,
        ralphlib.types.MessageType.ERROR: colorama.Fore.RED,
        ralphlib.types.MessageType.SYSTEM: colorama.Fore.YELLOW,
        ralphlib.types.MessageType.TOOL_USE: colorama.Fore.MAGENTA,
    }
    with context.gil:
        print(msg_color.get(message_type, colorama.Fore.WHITE) + message + colorama.Style.RESET_ALL, end='', flush=True)


def print_progress_eol(options: RalpherOptions, context: IterationContext) -> None:
    if options.quiet:
        return
    with context.gil:
        print('', flush=True)


def print_error(options: RalpherOptions, context: IterationContext, message: str) -> None:
    if options.quiet:
        return
    with context.gil:
        print(colorama.Fore.RED + message + colorama.Style.RESET_ALL, file=sys.stderr)


def print_error_eol(options: RalpherOptions, context: IterationContext, message: str) -> None:
    if options.quiet:
        return
    with context.gil:
        print('\n', file=sys.stderr)


def log_msg(options: RalpherOptions, context: IterationContext, msg: str) -> None:
    write_progress(options, context, msg)
    write_progress_eol(options, context)

    print_progress(options, context, ralphlib.types.MessageType.SYSTEM, msg)
    print_progress_eol(options, context)


def log_error(options: RalpherOptions, context: IterationContext, msg: str) -> None:
    write_error(options, context, msg)
    write_error_eol(options, context)

    print_error(options, context, msg)
    print_error_eol(options, context, msg)


def write_progress(options: RalpherOptions, context: IterationContext, message: str) -> None:
    if context.progressfd:
        with context.gil:
            context.progressfd.write(message)


def write_progress_lines(options: RalpherOptions, context: IterationContext, lines: list[str]) -> None:
    if context.progressfd:
        with context.gil:
            for line in lines:
                context.progressfd.write(line)


def write_progress_eol(options: RalpherOptions, context: IterationContext) -> None:
    if context.progressfd:
        with context.gil:
            context.progressfd.write('\n')
            context.progressfd.flush()


def write_error(options: RalpherOptions, context: IterationContext, message: str) -> None:
    if context.errorsfd:
        with context.gil:
            context.errorsfd.write(message)


def write_error_eol(options: RalpherOptions, context: IterationContext) -> None:
    if context.errorsfd:
        with context.gil:
            context.errorsfd.write('\n')
            context.errorsfd.flush()


def write_stdout(options: RalpherOptions, context: IterationContext, message: str) -> None:
    if context.stdoutfd:
        with context.gil:
            context.stdoutfd.write(message)


def write_stderr(options: RalpherOptions, context: IterationContext, message: str) -> None:
    if context.stderrfd:
        with context.gil:
            context.stderrfd.write(message)


def newline_required(context: IterationContext, message_type: ralphlib.types.MessageType) -> bool:
    newline_types = [
        ralphlib.types.MessageType.COMPLETE,
        ralphlib.types.MessageType.ERROR,
        ralphlib.types.MessageType.SYSTEM,
        ralphlib.types.MessageType.TOOL_USE,
    ]
    if message_type in newline_types:
        return True
    if message_type == ralphlib.types.MessageType.CONTENT_STOP:
        last_type = last_message_type(context)
        if last_type and last_type in [ralphlib.types.MessageType.CONTENT_START, ralphlib.types.MessageType.CONTENT_DELTA]:
            return True
    return False


def process(options: RalpherOptions, context: IterationContext) -> None:
    kwargs = {
        'stdin': subprocess.DEVNULL,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'bufsize': 1,  # line-buffered
        'text': True,
        'errors': 'replace',
        'start_new_session': True,
    }
    if options.cwd:
        kwargs['cwd'] = options.cwd

    proc = subprocess.Popen(  # noqa: S603
        context.cmd,
        **kwargs,
    )
    log_msg(options, context, f'Started subprocess {proc.pid}')

    # Threads to read and print from each pipe concurrently
    stdout_thread = threading.Thread(
        target=process_stdout,
        args=(
            options,
            context,
            proc.stdout,
        ),
    )
    stderr_thread = threading.Thread(
        target=process_stderr,
        args=(
            options,
            context,
            proc.stderr,
        ),
    )

    stdout_thread.start()
    stderr_thread.start()

    # Wait for the process to complete
    while True:
        if ralphlib.signals.get_should_exit():
            log_msg(options, context, f'Received termination signal. Terminating subprocess {proc.pid}...')
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except OSError:
                proc.terminate()
            break

        if proc.poll() is not None:
            break

        time.sleep(SUBPROCESS_POLL_INTERVAL)

    # Join threads to ensure all output is read
    stdout_thread.join()
    stderr_thread.join()

    log_msg(options, context, f'Process {proc.pid} exited with code {proc.returncode}')


def process_stdout(
    options: RalpherOptions,
    context: IterationContext,
    pipe: io.TextIOWrapper,
) -> None:
    for line in iter(pipe.readline, ''):
        line = line.strip()
        if not line:
            continue

        write_stdout(options, context, line + '\n')

        message_type, message = process_line(options, context, line)
        if message_type == ralphlib.types.MessageType.NONE:
            continue

        if message:
            write_progress(options, context, message)
            print_progress(options, context, message_type, message)

        if newline_required(context, message_type):
            write_progress_eol(options, context)
            print_progress_eol(options, context)

        append_message_type(context, message_type)


def process_stderr(
    options: RalpherOptions,
    context: IterationContext,
    pipe: io.TextIOWrapper,
) -> None:
    for line in iter(pipe.readline, ''):
        line = line.strip()
        if not line:
            continue

        write_stderr(options, context, line + '\n')
        print_error(options, context, line)


def process_line(
    options: RalpherOptions,
    context: IterationContext,
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    try:
        payload = orjson.loads(line)
        ptype = payload.get('type', 'MISSING_PTYPE')
        if ptype == 'system':
            content = payload.get('subtype', '')
            return ralphlib.types.MessageType.SYSTEM, content

        if ptype == 'assistant':
            return process_assistant(options, context, payload, line)

        if ptype == 'result':
            return process_result(options, context, payload, line)

        if ptype == 'user':
            return process_user(options, context, payload, line)

        if ptype == 'stream_event':
            return process_stream_event(options, context, payload, line)

        if ptype == 'rate_limit_event':
            return process_rate_limit_event(options, context, payload, line)

        log_error(options, context, f'\nprocess_line: unknown ptype: {ptype}\n{line}\n')
        add_unknown_ptype(context, ptype)
    except Exception as e:
        loguru.logger.exception(f'Exception in process_line: {e}')
        log_error(options, context, f'\nprocess_line: exception: {e}\n{line}\n')
        return ralphlib.types.MessageType.ERROR, line
    return ralphlib.types.MessageType.NONE, line


def process_user(
    options: RalpherOptions,
    context: IterationContext,
    payload: dict[str, Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    message = payload.get('message', {})
    if message:
        role = message.get('role', '')
        if role == 'user':
            content = message.get('content', [])
            if content:
                for c in content:
                    tool_use_id = c.get('tool_use_id')
                    if tool_use_id and tool_use_id in context.background_tools:
                        tool_type = c.get('type', '')
                        if tool_type == 'tool_result':
                            cs = c.get('content', '')
                            if cs:
                                m = tool_id_regex.match(cs)
                                if m:
                                    tool_id = m.group('id')
                                    if tool_id:
                                        add_background_tool_id(context, tool_use_id, tool_id)

    return ralphlib.types.MessageType.NONE, line


def process_assistant(
    options: RalpherOptions,
    context: IterationContext,
    payload: dict[str, Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    message = payload.get('message', {})
    if message:
        content = message.get('content', [])
        if content:
            for c in content:
                ctype = c.get('type', '')
                if ctype == 'text':
                    text = c.get('text', '')
                    for stop in options.stops:
                        if stop in text:
                            set_complete(context, True)
                            return ralphlib.types.MessageType.COMPLETE, ''

                if ctype == 'tool_use':
                    run_in_background = get_run_in_background(c)

                    tool_name = c.get('name', 'UNKNOWN-TOOL')
                    if tool_name == 'UNKNOWN-TOOL':
                        loguru.logger.warning(f'Tool use without name: {line}')

                    context.tools_used_set.add(tool_name)
                    vals = [tool_name]
                    tool_input = get_tool_input(c)
                    if tool_input:
                        if tool_name in background_task_tool_name and tool_input in context.background_id_to_tool:
                            tool_id = context.background_id_to_tool[tool_input]
                            vals.append(context.background_tools[tool_id]['name'])
                            vals.append(context.background_tools[tool_id]['input'])
                        else:
                            vals.append(tool_input)
                            if run_in_background:
                                vals.append('(running in background)')
                    else:
                        loguru.logger.warning(f'Tool {tool_name} without input: {line}')
                        add_unknown_tool(context, tool_name, c.get('input', {}))

                    # catch starting background tool uses
                    if run_in_background:
                        if tool_name in background_tools_list:
                            add_background_tool(context, tool_name, tool_input, c.get('id', ''))
                        else:
                            loguru.logger.warning(f'Tool {tool_name} not in known background tools list: {line}')

                    return ralphlib.types.MessageType.TOOL_USE, '\n'.join(vals)

    return ralphlib.types.MessageType.NONE, line


def indent_lines(s: str, indent: str = '  ') -> str:
    if not s:
        return ''
    return '\n'.join(f'{indent}{line}' for line in s.splitlines())


def get_run_in_background(content: dict[str, Any]) -> bool:
    input_field = content.get('input', {})
    if input_field:
        run_in_background = input_field.get('run_in_background', False)
        if isinstance(run_in_background, bool):
            return run_in_background
    return False


def get_tool_input(content: dict[str, Any]) -> str:
    tool_input = ''
    input_field = content.get('input', {})
    if input_field:
        tool_input = input_field_to_content(input_field)
    return indent_lines(tool_input)


def input_field_to_content(input_field: dict[str, Any]) -> str:
    regular_fields = ['command', 'description', 'file_path', 'pattern', 'query', 'url', 'task_id']
    for f in regular_fields:
        if f in input_field and input_field[f]:
            return str(input_field[f])

    todos = input_field.get('todos', [])
    if todos:
        td_contents = []
        for td in todos:
            td_content = td.get('content', '')
            if td_content:
                td_contents.append(f'- {td_content}')
        return '\n'.join(td_contents)

    return ''


def process_result(
    options: RalpherOptions,
    context: IterationContext,
    payload: dict[str, Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    subtype = payload.get('subtype', '')
    is_error = payload.get('is_error', False)
    result = payload.get('result', '')

    # errors
    if subtype == 'success' and is_error:
        set_error(context, True)
        return ralphlib.types.MessageType.ERROR, result

    if result:
        # stopping
        for stop in options.stops:
            if stop in result:
                set_complete(context, True)
                return ralphlib.types.MessageType.COMPLETE, ''

    return ralphlib.types.MessageType.NONE, line


def process_stream_event(
    options: RalpherOptions,
    context: IterationContext,
    payload: dict[str, Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    event = payload.get('event', {})
    etype = event.get('type', '')

    if etype in ['message_start', 'message_stop', 'message_delta']:
        return ralphlib.types.MessageType.NONE, ''

    if etype == 'content_block_start':
        content_block = event.get('content_block', {})
        cb_type = content_block.get('type', '')
        if cb_type == 'text':
            return ralphlib.types.MessageType.CONTENT_START, content_block.get('text', '')
        if cb_type == 'tool_use':
            return ralphlib.types.MessageType.NONE, ''

    if etype == 'content_block_stop':
        return ralphlib.types.MessageType.CONTENT_STOP, ''

    if etype == 'content_block_delta':
        delta = event.get('delta', {})
        cb_type = delta.get('type', '')
        if cb_type == 'text_delta':
            return ralphlib.types.MessageType.CONTENT_DELTA, delta.get('text', '')
        if cb_type == 'input_json_delta':
            return ralphlib.types.MessageType.NONE, ''
    return ralphlib.types.MessageType.NONE, line


def process_rate_limit_event(
    options: RalpherOptions,
    context: IterationContext,
    payload: dict[str, Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    return ralphlib.types.MessageType.NONE, line
