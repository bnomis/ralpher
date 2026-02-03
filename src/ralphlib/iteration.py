import subprocess
import sys
import threading
from typing import TYPE_CHECKING, Any

import colorama
import orjson

import ralphlib.logger
import ralphlib.types

if TYPE_CHECKING:
    import io

    from ralphlib.options import RalpherOptions

globals_lock = threading.Lock()
complete_value = False
error_value = False

print_lock = threading.Lock()
message_type_queue: list[ralphlib.types.MessageType] = []
tools_used_set = set()


def set_complete(value: bool) -> bool:
    global complete_value
    with globals_lock:
        complete_value = value
    return value


def get_complete() -> bool:
    global complete_value
    with globals_lock:
        value = complete_value
    return value


def set_error(value: bool) -> bool:
    global error_value
    with globals_lock:
        error_value = value
    return value


def get_error() -> bool:
    global error_value
    with globals_lock:
        value = error_value
    return value


def run(options: RalpherOptions, prompt: str, iteration: int) -> tuple[bool, bool]:
    context = make_context(options, prompt, iteration)
    try:
        process(options, context)
    except Exception as e:
        raise Exception(f'Exception: {e}') from e
    finally:
        summary(options, context)
        unmake_context(context)
    return get_complete(), get_error()


def make_context(options: RalpherOptions, prompt: str, iteration: int) -> dict[str, Any]:
    cmd = [options.agent]
    cmd.extend(options.args.split())
    cmd.append(prompt)
    context: dict[str, Any] = {
        'iteration': iteration,
        'prompt': prompt,
        'cmd': cmd,
        'stdout': None,
        'stderr': None,
        'progress': None,
    }
    try:
        if options.stdout:
            context['stdout'] = ralphlib.logger.log_file(options, options.stdout, iteration)
        if options.stderr:
            context['stderr'] = ralphlib.logger.log_file(options, options.stderr, iteration)
        if options.progress:
            context['progress'] = ralphlib.logger.log_file(options, options.progress, iteration)
    except Exception as e:
        raise Exception(f'Exception: {e}') from e
    finally:
        unmake_context(context)
    return context


def unmake_context(context: dict[str, Any]) -> None:
    pass


def summary(options: RalpherOptions, context: dict[str, Any]) -> None:
    lines = []
    if tools_used_set:
        tools = []
        for t in sorted(tools_used_set):
            tools.append(f'- {t}')
        tools_summary = '\n'.join(tools)
        lines.append(f'\n= Tools used:\n{tools_summary}\n')

    if lines:
        if context['progress']:
            with context['progress'].open('a', encoding='utf-8') as fd:
                for line in lines:
                    fd.write(line)
        if not options.quiet:
            for line in lines:
                print(line, end='', flush=True)


def process(options: RalpherOptions, context: dict[str, Any]) -> None:
    kwargs = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'bufsize': 1,  # line-buffered
        'text': True,
        'errors': 'replace',
    }
    if options.cwd:
        kwargs['cwd'] = options.cwd

    proc = subprocess.Popen(  # noqa: S603
        context['cmd'],
        **kwargs,
    )

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
    proc.wait()

    # Join threads to ensure all output is read
    stdout_thread.join()
    stderr_thread.join()


def newline_required(message_type: ralphlib.types.MessageType) -> bool:
    newline_types = [
        ralphlib.types.MessageType.COMPLETE,
        ralphlib.types.MessageType.ERROR,
        ralphlib.types.MessageType.SYSTEM,
        ralphlib.types.MessageType.TOOL_USE,
    ]
    if message_type in newline_types:
        return True
    if message_type == ralphlib.types.MessageType.CONTENT_STOP:
        last_type = message_type_queue[-1] if message_type_queue else None
        if last_type in [ralphlib.types.MessageType.CONTENT_START, ralphlib.types.MessageType.CONTENT_DELTA]:
            return True
    return False


def process_stdout(
    options: RalpherOptions,
    context: dict[str, Any],
    pipe: io.TextIOWrapper,
) -> None:
    logfd: io.TextIOWrapper | None = None
    progressfd: io.TextIOWrapper | None = None
    if context['stdout']:
        logfd = context['stdout'].open('a', encoding='utf-8')
    if context['progress']:
        progressfd = context['progress'].open('a', encoding='utf-8')

    for line in iter(pipe.readline, ''):
        line = line.strip()
        if not line:
            continue

        if logfd:
            logfd.write(line + '\n')

        message_type, message = process_line(options, line)
        if message_type == ralphlib.types.MessageType.NONE:
            continue

        if progressfd:
            if message:
                progressfd.write(message)
            if newline_required(message_type):
                progressfd.write('\n')
                progressfd.flush()

        if not options.quiet:
            if message:
                print_progress(message_type, message)
            if newline_required(message_type):
                print_progress_eol()

        message_type_queue.append(message_type)


def print_progress(message_type: ralphlib.types.MessageType, message: str) -> None:
    msg_color = {
        ralphlib.types.MessageType.CONTENT_DELTA: colorama.Fore.CYAN,
        ralphlib.types.MessageType.ERROR: colorama.Fore.RED,
        ralphlib.types.MessageType.SYSTEM: colorama.Fore.YELLOW,
        ralphlib.types.MessageType.TOOL_USE: colorama.Fore.MAGENTA,
    }
    with print_lock:
        print(msg_color.get(message_type, colorama.Fore.WHITE) + message + colorama.Style.RESET_ALL, end='', flush=True)


def print_progress_eol() -> None:
    with print_lock:
        print('', flush=True)


def process_stderr(
    options: RalpherOptions,
    context: dict[str, Any],
    pipe: io.TextIOWrapper,
) -> None:
    logfd: io.TextIOWrapper | None = None
    if context['stderr']:
        logfd = context['stderr'].open('a', encoding='utf-8')

    for line in iter(pipe.readline, ''):
        line = line.strip()
        if not line:
            continue

        if logfd:
            logfd.write(line + '\n')

        if not options.quiet:
            print_error(line)


def print_error(message: str) -> None:
    with print_lock:
        print(colorama.Fore.RED + message + colorama.Style.RESET_ALL, file=sys.stderr)


def process_line(options: RalpherOptions, line: str) -> tuple[ralphlib.types.MessageType, str]:
    try:
        payload = orjson.loads(line)
        ptype = payload.get('type')
        if ptype == 'system':
            content = payload.get('subtype', '')
            return ralphlib.types.MessageType.SYSTEM, content

        if ptype == 'assistant':
            return process_assisstant(options, payload, line)

        if ptype == 'result':
            return process_result(options, payload, line)

        if ptype == 'user':
            return ralphlib.types.MessageType.NONE, line

        if ptype == 'stream_event':
            return process_stream_event(options, payload, line)

        print_error(f'\nprocess_line: unknown ptype: {ptype}\n{line}\n')
    except Exception as e:
        print_error(f'\nprocess_line: exception: {e}\n{line}\n')
        return ralphlib.types.MessageType.ERROR, line
    return ralphlib.types.MessageType.NONE, line


def process_assisstant(
    options: RalpherOptions,
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
                            set_complete(True)
                            return ralphlib.types.MessageType.COMPLETE, ''
                if ctype == 'tool_use':
                    tool_name = c.get('name', 'UNKNOWN-TOOL')
                    tools_used_set.add(tool_name)
                    vals = [tool_name]
                    tool_input = get_tool_input(c)
                    if tool_input:
                        vals.append(tool_input)
                    return ralphlib.types.MessageType.TOOL_USE, '\n'.join(vals)

    return ralphlib.types.MessageType.NONE, line


def indent_lines(s: str, indent: str = '  ') -> str:
    if not s:
        return ''
    return '\n'.join(f'{indent}{line}' for line in s.splitlines())


def get_tool_input(content: dict[str, Any]) -> str:
    tool_input = ''
    input_field = content.get('input', {})
    if input_field:
        tool_input = input_field_to_content(input_field)
    return indent_lines(tool_input)


def input_field_to_content(input_field: dict[str, Any]) -> str:
    command = input_field.get('command', '')
    if command:
        return command

    file_path = input_field.get('file_path', '')
    if file_path:
        return file_path

    todos = input_field.get('todos', [])
    if todos:
        td_contents = []
        for td in todos:
            td_content = td.get('content', '')
            if td_content:
                td_contents.append(f'- {td_content}')
        return '\n'.join(td_contents)

    pattern = input_field.get('pattern', '')
    if pattern:
        return pattern

    return ''


def process_result(
    options: RalpherOptions,
    payload: dict[str, Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    subtype = payload.get('subtype', '')
    is_error = payload.get('is_error', False)
    result = payload.get('result', '')

    # errors
    if subtype == 'success' and is_error:
        set_error(True)
        return ralphlib.types.MessageType.ERROR, result

    if result:
        # stopping
        for stop in options.stops:
            if stop in result:
                set_complete(True)
                return ralphlib.types.MessageType.COMPLETE, ''

    return ralphlib.types.MessageType.NONE, line


def process_stream_event(
    options: RalpherOptions,
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
