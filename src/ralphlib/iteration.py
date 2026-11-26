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
import typing

import loguru
import orjson

import ralphlib.exceptions
import ralphlib.hooks
import ralphlib.logger
import ralphlib.printer
import ralphlib.signals
import ralphlib.state
import ralphlib.templater
import ralphlib.types
import ralphlib.verifier

if typing.TYPE_CHECKING:
    import io

    import ralphlib.options


TASK_PROGRESS_RE = re.compile(
    r'<task>\s*<id>(?P<id>\d+)</id>\s*<title>(?P<title>.*?)</title>\s*<index>(?P<index>\d+)</index>\s*<count>(?P<count>\d+)</count>\s*<status>(?P<status>(start|done|blocked|operator))</status>\s*</task>'
)


@dataclasses.dataclass
class TaskEntry:
    id: str
    title: str
    index: int
    count: int
    status: str


@dataclasses.dataclass
class IterationContext:
    cmd: list[str]
    iteration: int
    prompt: str
    background_id_to_tool: dict[str, str] = dataclasses.field(default_factory=dict)
    background_tools: dict[str, dict[str, str]] = dataclasses.field(default_factory=dict)
    complete: bool = False
    """Set at run time when the agent reports completion."""
    error: bool = False
    """Set at run time when the agent run fails."""
    stdout_seen: bool = False
    """Set at run time when the agent writes its first non-empty stdout line."""
    gil: threading.Lock = dataclasses.field(default_factory=threading.Lock)
    message_type_queue: list[ralphlib.types.MessageType] = dataclasses.field(default_factory=list)
    started_tasks: set[str] = dataclasses.field(default_factory=set)
    """Task ids whose start line has been printed this iteration."""
    in_progress_tasks: set[str] = dataclasses.field(default_factory=set)
    """Set at run time: task ids seen `in-progress` in the tasks file, seeded before the agent starts."""
    tasks_signature: tuple[int, int] | None = None
    """Set at run time: modification time and size of the tasks file at the last poll read."""
    progress: pathlib.Path | None = None
    errors: pathlib.Path | None = None
    stderr: pathlib.Path | None = None
    stdout: pathlib.Path | None = None
    tools_used_set: set[str] = dataclasses.field(default_factory=set)
    unknown_tools: dict[str, dict[str, typing.Any]] = dataclasses.field(default_factory=dict)
    progressfd: io.TextIOWrapper | None = None
    stdoutfd: io.TextIOWrapper | None = None
    stderrfd: io.TextIOWrapper | None = None
    errorsfd: io.TextIOWrapper | None = None
    unknown_ptype_set: set[str] = dataclasses.field(default_factory=set)


SUBPROCESS_POLL_INTERVAL = 3
MAX_KILL_ATTEMPTS = 3

# regex to extract tool IDs from tool results that indicate a background tool has started, e.g. "Command running in background with ID: abc123."
TOOL_ID_REGEX = re.compile(r'Command running in background with ID: (?P<id>\w+)\.')
# list of tools that are known to run in the background, and thus should be tracked for their IDs
BACKGROUND_TOOLS = frozenset(['Agent', 'Bash'])
# list tool names used to track background tasks
BACKGROUND_TASK_TOOL_NAMES = frozenset(['TaskOutput', 'TaskStop'])
# message types that should trigger a newline before the next message
NEWLINE_TYPES = frozenset(
    [
        ralphlib.types.MessageType.ALERT,
        ralphlib.types.MessageType.COMPLETE,
        ralphlib.types.MessageType.ERROR,
        ralphlib.types.MessageType.PROGRESS,
        ralphlib.types.MessageType.SYSTEM,
        ralphlib.types.MessageType.TOOL_USE,
    ]
)


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


def add_tool_used(context: IterationContext, tool_name: str) -> None:
    with context.gil:
        context.tools_used_set.add(tool_name)


def add_unknown_ptype(context: IterationContext, ptype: str) -> None:
    with context.gil:
        context.unknown_ptype_set.add(ptype)


def add_unknown_tool(context: IterationContext, tool_name: str, input_values: dict[str, typing.Any]) -> None:
    with context.gil:
        if tool_name not in context.unknown_tools:
            context.unknown_tools[tool_name] = {'input_bytes': len(orjson.dumps(input_values))}


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


def run(options: ralphlib.options.RalpherOptions, prompt: str, iteration: int) -> tuple[bool, bool]:
    context = make_context(options, prompt, iteration)
    try:
        process(options, context)
    except Exception:
        loguru.logger.exception('Exception in run')
        raise
    finally:
        summary(options, context)
        unmake_context(context)
    return get_complete(context), get_error(context)


def add_settings(options: ralphlib.options.RalpherOptions, cmd: list[str]) -> list[str]:
    base_ref = options.worktree_base_ref
    if base_ref:
        cmd.append('--settings')
        cmd.append(orjson.dumps({'worktree': {'baseRef': base_ref}}).decode())
    return cmd


def add_worktree_arg(options: ralphlib.options.RalpherOptions, cmd: list[str]) -> list[str]:
    if options.worktree:
        cmd.append('--worktree')
        if options.task_file:
            cmd.append(ralphlib.templater.task_file_slug(options.task_file))
    return cmd


def make_context(options: ralphlib.options.RalpherOptions, prompt: str, iteration: int) -> IterationContext:
    options.worktree_task_path = None
    cmd = [options.agent]
    cmd.extend(shlex.split(options.args))
    cmd = add_settings(options, cmd)
    cmd = add_worktree_arg(options, cmd)
    cmd.append(prompt)
    opened: list[io.TextIOWrapper] = []
    try:
        stdout, stdoutfd = open_log_file(options.stdout, options, iteration, opened)
        stderr, stderrfd = open_log_file(options.stderr, options, iteration, opened)
        progress, progressfd = open_log_file(options.progress, options, iteration, opened)
        errors, errorsfd = open_log_file(options.errors, options, iteration, opened)
    except Exception:
        loguru.logger.exception('Exception in make_context')
        close_all(opened)
        raise
    return IterationContext(
        cmd=cmd,
        iteration=iteration,
        prompt=prompt,
        errors=errors,
        errorsfd=errorsfd,
        progress=progress,
        progressfd=progressfd,
        stderr=stderr,
        stderrfd=stderrfd,
        stdout=stdout,
        stdoutfd=stdoutfd,
    )


def open_log_file(
    name: str | None,
    options: ralphlib.options.RalpherOptions,
    iteration: int,
    opened: list[io.TextIOWrapper],
) -> tuple[pathlib.Path | None, io.TextIOWrapper | None]:
    """Open the iteration log file `name` for appending, recording the handle in `opened` so a later failure can close it.

    Raises:
        LogFileError: the file cannot be opened.
    """
    if not name:
        return None, None
    path = ralphlib.logger.log_file(options, name, iteration)
    try:
        fd = path.open('a', encoding='utf-8')
    except OSError as e:
        raise ralphlib.exceptions.LogFileError(f'Cannot open the iteration log file {path}') from e
    opened.append(fd)
    return path, fd


def close_all(fds: list[io.TextIOWrapper]) -> None:
    for fd in fds:
        flush_and_close_fd(fd)


def flush_and_close_fd(fd: io.TextIOWrapper | None) -> None:
    try:
        if fd:
            fd.flush()
            fd.close()
    except OSError:
        loguru.logger.opt(exception=True).warning('Cannot flush and close a log file')


def unmake_context(context: IterationContext) -> None:
    if context.stdoutfd:
        flush_and_close_fd(context.stdoutfd)
    if context.stderrfd:
        flush_and_close_fd(context.stderrfd)
    if context.progressfd:
        flush_and_close_fd(context.progressfd)
    if context.errorsfd:
        flush_and_close_fd(context.errorsfd)


def summary(options: ralphlib.options.RalpherOptions, context: IterationContext) -> None:
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
        write_progress_lines(context, lines)

        ralphlib.state.add_to_state(
            options,
            state_payload,
            key1='iterations',
            key2=ralphlib.logger.iteration_to_str(options, context.iteration),
        )


def print_progress_lines(options: ralphlib.options.RalpherOptions, context: IterationContext, lines: list[str]) -> None:
    if options.quiet:
        return
    with context.gil:
        for line in lines:
            ralphlib.printer.console.print(line, end='', soft_wrap=True)


def print_progress(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    message_type: ralphlib.types.MessageType,
    message: str,
) -> None:
    if options.quiet:
        return

    with context.gil:
        ralphlib.printer.console.print(message, style=ralphlib.printer.type_to_style(options, message_type), end='', soft_wrap=True)


def print_progress_eol(options: ralphlib.options.RalpherOptions, context: IterationContext) -> None:
    if options.quiet:
        return
    with context.gil:
        ralphlib.printer.console.print('')


def print_error(options: ralphlib.options.RalpherOptions, context: IterationContext, message: str) -> None:
    if options.quiet:
        return
    with context.gil:
        ralphlib.printer.console_stderr.print(
            message,
            style=ralphlib.printer.type_to_style(options, ralphlib.types.MessageType.ERROR),
            end='',
            soft_wrap=True,
        )


def print_error_eol(options: ralphlib.options.RalpherOptions, context: IterationContext) -> None:
    if options.quiet:
        return
    with context.gil:
        ralphlib.printer.console_stderr.print('\n')


def log_msg(options: ralphlib.options.RalpherOptions, context: IterationContext, msg: str) -> None:
    write_progress(context, msg)
    write_progress_eol(context)

    print_progress(options, context, ralphlib.types.MessageType.SYSTEM, msg)
    print_progress_eol(options, context)


def log_error(options: ralphlib.options.RalpherOptions, context: IterationContext, msg: str) -> None:
    write_error(context, msg)
    write_error_eol(context)

    print_error(options, context, msg)
    print_error_eol(options, context)


def write_log(context: IterationContext, fd: io.TextIOWrapper | None, text: str, flush: bool = False) -> None:
    """Write `text` to the log file `fd` under the context lock.

    Raises:
        LogFileError: the write or flush fails.
    """
    if not fd:
        return
    with context.gil:
        try:
            fd.write(text)
            if flush:
                fd.flush()
        except OSError as e:
            raise ralphlib.exceptions.LogFileError(f'Cannot write to the iteration log file {fd.name}') from e


def write_progress(context: IterationContext, message: str) -> None:
    write_log(context, context.progressfd, message)


def write_progress_lines(context: IterationContext, lines: list[str]) -> None:
    write_log(context, context.progressfd, ''.join(lines))


def write_progress_eol(context: IterationContext) -> None:
    write_log(context, context.progressfd, '\n', flush=True)


def write_error(context: IterationContext, message: str) -> None:
    write_log(context, context.errorsfd, message)


def write_error_eol(context: IterationContext) -> None:
    write_log(context, context.errorsfd, '\n', flush=True)


def write_stdout(context: IterationContext, message: str) -> None:
    write_log(context, context.stdoutfd, message)


def write_stderr(context: IterationContext, message: str) -> None:
    write_log(context, context.stderrfd, message)


def newline_required(context: IterationContext, message_type: ralphlib.types.MessageType) -> bool:
    if message_type in NEWLINE_TYPES:
        return True
    if message_type == ralphlib.types.MessageType.CONTENT_STOP:
        last_type = last_message_type(context)
        if last_type and last_type in [ralphlib.types.MessageType.CONTENT_DELTA, ralphlib.types.MessageType.CONTENT_START]:
            return True
    return False


def agent_environment(environ: dict[str, str], venv: pathlib.Path, src: pathlib.Path) -> dict[str, str]:
    """environ without ralpher's own virtual environment and source directory.

    bin/activate.sh puts ralpher's venv on PATH and its src on PYTHONPATH; left in place,
    `python` and `pytest` in the agent's shell resolve to ralpher's packages, not the project's.
    Entries that are not ralpher's own are kept.
    """
    env = dict(environ)
    venv_bin = venv / 'bin'
    if env.get('VIRTUAL_ENV') and pathlib.Path(env['VIRTUAL_ENV']).resolve() == venv.resolve():
        env.pop('VIRTUAL_ENV')
        env.pop('VIRTUAL_ENV_PROMPT', None)
    for name, own in (('PATH', venv_bin), ('PYTHONPATH', src)):
        if name not in env:
            continue
        kept = [entry for entry in env[name].split(os.pathsep) if not entry or pathlib.Path(entry).resolve() != own.resolve()]
        if any(kept):
            env[name] = os.pathsep.join(kept)
        else:
            env.pop(name)
    return env


def process(options: ralphlib.options.RalpherOptions, context: IterationContext) -> None:
    """Run the agent and stream its output. stdout and stderr both get `PIPE` on purpose: each is read by its own thread.

    Raises:
        RalpherError: the agent cannot be started.
        GitError: `hooks.event` could not open the repository.
        LogFileError: the iteration log file cannot be written.
    """
    kwargs = {
        'bufsize': 1,  # line-buffered
        'env': agent_environment(dict(os.environ), pathlib.Path(sys.prefix), pathlib.Path(__file__).resolve().parents[1]),
        'errors': 'replace',
        'start_new_session': True,
        'stderr': subprocess.PIPE,
        'stdin': subprocess.DEVNULL,
        'stdout': subprocess.PIPE,
        'text': True,
    }
    if options.cwd:
        kwargs['cwd'] = options.cwd

    context.in_progress_tasks = {t.id for t in read_task_statuses(options) if t.status == 'in-progress'}

    try:
        proc = subprocess.Popen(  # noqa: S603
            context.cmd,
            **kwargs,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise ralphlib.exceptions.RalpherError(f'Cannot start the agent "{context.cmd[0]}"') from e
    log_msg(options, context, f'Started agent process {proc.pid}')
    ralphlib.hooks.event(
        options,
        ralphlib.types.RalpherEventType.AGENT_PROCESS_START,
        {
            'agent_process_id': proc.pid,
        },
    )

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

    while True:
        time.sleep(SUBPROCESS_POLL_INTERVAL)

        if proc.poll() is not None:
            break

        announce_started_tasks(options, context)

        if ralphlib.signals.get_should_exit():
            log_msg(options, context, f'Received termination signal. Terminating subprocess {proc.pid}...')
            kill_agent(proc)
            break

        if get_error(context):
            log_msg(options, context, f'Error detected in output. Terminating subprocess {proc.pid}...')
            kill_agent(proc)
            break

    stdout_thread.join()
    stderr_thread.join()

    log_msg(options, context, f'Process {proc.pid} exited with code {proc.returncode}')
    if failed_to_start(context, proc.returncode):
        log_error(options, context, f'The agent exited with code {proc.returncode} without any output; stopping the loop')
        set_error(context, True)
    ralphlib.hooks.event(
        options,
        ralphlib.types.RalpherEventType.AGENT_PROCESS_END,
        {
            'agent_exit_code': proc.returncode,
            'agent_process_id': proc.pid,
        },
    )


def failed_to_start(context: IterationContext, returncode: int | None) -> bool:
    """Whether the agent exited non-zero before writing any stdout, as when it refuses its arguments.

    Every later iteration would pass the same arguments and fail the same way, so the loop stops. An exit after a termination signal, or
    after an error already seen, is not counted.
    """
    if not returncode or ralphlib.signals.get_should_exit() or get_error(context):
        return False
    with context.gil:
        return not context.stdout_seen


def kill_agent(proc: subprocess.Popen) -> None:
    loguru.logger.info(f'Killing agent process {proc.pid}...')
    for _ in range(MAX_KILL_ATTEMPTS):
        if proc.poll() is not None:
            break

        signal_agent(proc)
        time.sleep(SUBPROCESS_POLL_INTERVAL)
        if proc.poll() is not None:
            break

    if proc.poll() is None:
        loguru.logger.warning(f'Process {proc.pid} did not terminate after {MAX_KILL_ATTEMPTS} attempts.')


def signal_agent(proc: subprocess.Popen) -> None:
    loguru.logger.info(f'Signaling agent process {proc.pid}...')
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except OSError:
        proc.terminate()


def process_stdout(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    pipe: io.TextIOWrapper,
) -> None:
    try:
        read_stdout(options, context, pipe)
    except OSError, ralphlib.exceptions.LogFileError:
        loguru.logger.error('I/O error on the agent stdout reader thread')
        set_error(context, True)


def read_stdout(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    pipe: io.TextIOWrapper,
) -> None:
    for line in iter(pipe.readline, ''):
        line = line.strip()
        if not line:
            continue

        with context.gil:
            context.stdout_seen = True
        write_stdout(context, line + '\n')

        message_type, message = process_line(options, context, line)
        if message_type == ralphlib.types.MessageType.NONE:
            continue

        if message:
            write_progress(context, message)
            print_progress(options, context, message_type, message)

        if newline_required(context, message_type):
            write_progress_eol(context)
            print_progress_eol(options, context)

        append_message_type(context, message_type)


def process_stderr(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    pipe: io.TextIOWrapper,
) -> None:
    try:
        for line in iter(pipe.readline, ''):
            line = line.strip()
            if not line:
                continue

            write_stderr(context, line + '\n')
            print_error(options, context, line)
    except OSError, ralphlib.exceptions.LogFileError:
        loguru.logger.error('I/O error on the agent stderr reader thread')
        set_error(context, True)


def process_line(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    try:
        payload = orjson.loads(line)
        ptype = payload.get('type', 'MISSING_PTYPE')
        if ptype == 'system':
            return process_system(options, context, payload, line)

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

        if ptype == 'tool_progress':
            return process_tool_progress(options, context, payload, line)

        if ptype == 'command_lifecycle':
            return process_command_lifecycle(options, context, payload, line)

        log_error(options, context, f'\nprocess_line: unknown ptype: {ptype}\n{line}\n')
        add_unknown_ptype(context, ptype)
    except (orjson.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
        loguru.logger.opt(exception=True).warning('Cannot process an agent output line')
        # auditme: accept[except-interpolation] the message goes to the session error log, which has no traceback
        log_error(options, context, f'\nprocess_line: exception: {e}\n{line}\n')
        return ralphlib.types.MessageType.ERROR, line
    return ralphlib.types.MessageType.NONE, line


def process_system(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    payload: dict[str, typing.Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    skip = [
        'background_tasks_changed',
        'commands_changed',
        'compat_boundary',
        'hook_progress',
        'hook_response',
        'hook_started',
        'init',
        'notification',
        'status',
        'task_notification',
        'task_progress',
        'task_started',
        'task_updated',
        'thinking_tokens',
        'vcs_state_changed',
    ]
    content = payload.get('subtype', '')
    if content and content in skip:
        return ralphlib.types.MessageType.NONE, line
    return ralphlib.types.MessageType.SYSTEM, content


def process_user(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    payload: dict[str, typing.Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    message = payload.get('message', {})
    if message:
        role = message.get('role', '')
        if role == 'user':
            content = message.get('content') or []
            for c in content:
                tool_use_id = c.get('tool_use_id', '')
                tool_type = c.get('type', '')
                cs = c.get('content', '')
                if tool_use_id and tool_use_id in context.background_tools:
                    if tool_type == 'tool_result':
                        if cs:
                            m = TOOL_ID_REGEX.match(cs)
                            if m:
                                tool_id = m.group('id')
                                if tool_id:
                                    add_background_tool_id(context, tool_use_id, tool_id)

                if tool_type == 'tool_result' and cs and '<task>' in cs and '</task>' in cs:
                    return process_task_progress(options, context, payload, cs)

    return ralphlib.types.MessageType.NONE, line


def is_stop(
    options: ralphlib.options.RalpherOptions,
    text: str,
) -> bool:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for stop in options.stops:
            if line == stop:
                return True
    return False


def process_assistant(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    payload: dict[str, typing.Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    message = payload.get('message', {})
    if message:
        content = message.get('content', [])
        if content:
            for c in content:
                ctype = c.get('type', '')

                if ctype == 'tool_result':
                    tool_result = c.get('content', '')
                    if tool_result and '<task>' in tool_result and '</task>' in tool_result:
                        return process_task_progress(options, context, payload, tool_result)

                if ctype == 'text':
                    text = c.get('text', '').strip()
                    if text:
                        if is_stop(options, text):
                            set_complete(context, True)
                            return ralphlib.types.MessageType.COMPLETE, ''

                        if '<task>' in text and '</task>' in text:
                            return process_task_progress(options, context, payload, text)

                if ctype == 'tool_use':
                    run_in_background = get_run_in_background(c)

                    tool_name = c.get('name', 'UNKNOWN-TOOL')
                    if tool_name == 'UNKNOWN-TOOL':
                        loguru.logger.warning(f'Tool use without name: {len(line)} characters')
                        loguru.logger.debug(f'Tool use without name: {line}')

                    add_tool_used(context, tool_name)
                    vals = [tool_name]
                    tool_input = get_tool_input(c)
                    if tool_input:
                        with context.gil:
                            if tool_name in BACKGROUND_TASK_TOOL_NAMES and tool_input in context.background_id_to_tool:
                                tool_id = context.background_id_to_tool[tool_input]
                                vals.append(context.background_tools[tool_id]['name'])
                                vals.append(context.background_tools[tool_id]['input'])
                            else:
                                vals.append(tool_input)
                                if run_in_background:
                                    vals.append('(running in background)')
                    else:
                        loguru.logger.warning(f'Tool {tool_name} without input: {len(line)} characters')
                        loguru.logger.debug(f'Tool {tool_name} without input: {line}')
                        add_unknown_tool(context, tool_name, c.get('input', {}))

                    # catch starting background tool uses
                    if run_in_background:
                        if tool_name in BACKGROUND_TOOLS:
                            add_background_tool(context, tool_name, tool_input, c.get('id', ''))
                        else:
                            loguru.logger.warning(f'Tool {tool_name} not in known background tools list')
                            loguru.logger.debug(f'Tool {tool_name} not in known background tools list: {line}')

                    return ralphlib.types.MessageType.TOOL_USE, '\n'.join(vals)

    return ralphlib.types.MessageType.NONE, line


def process_task_progress(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    payload: dict[str, typing.Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    task = TASK_PROGRESS_RE.search(line)
    if task:
        tid = task.group('id')
        status = task.group('status')
        if status == 'start' and not mark_started(context, tid):
            return ralphlib.types.MessageType.NONE, line
        message = task_progress(options, tid, task.group('title'), task.group('index'), task.group('count'), status)
        return ralphlib.types.MessageType.PROGRESS, message
    return ralphlib.types.MessageType.NONE, line


def task_progress(options: ralphlib.options.RalpherOptions, tid: str, title: str, index: str, count: str, status: str) -> str:
    ralphlib.hooks.event(
        options,
        ralphlib.types.RalpherEventType.LLM_TASK_PROGRESS,
        {
            'task_count': count,
            'task_id': tid,
            'task_index': index,
            'task_status': status,
            'task_title': title,
        },
    )
    return f'\ntask {tid}: {title} {index}/{count} {status}\n'


def mark_started(context: IterationContext, tid: str) -> bool:
    """Record that task `tid` has a start line; False if it already had one this iteration."""
    with context.gil:
        if tid in context.started_tasks:
            return False
        context.started_tasks.add(tid)
        return True


def read_task_statuses(options: ralphlib.options.RalpherOptions) -> list[TaskEntry]:
    """Return the tasks in the file the agent edits, or an empty list when it cannot be read yet."""
    if not options.task_file:
        return []
    try:
        tasks = ralphlib.verifier.read_tasks(options)
    except ralphlib.verifier.READ_ERRORS:
        return []
    return [TaskEntry(str(t.number), t.title, i, len(tasks), t.status) for i, t in enumerate(tasks, start=1)]


def announce_started_tasks(options: ralphlib.options.RalpherOptions, context: IterationContext) -> None:
    """Print a start line for each task the agent has newly marked `in-progress`.

    The agent is asked to write a start `<task>` block but often does not;
    the status change in the tasks file is the reliable signal.
    """
    if not options.task_file:
        return
    try:
        stat = ralphlib.verifier.agent_task_file(options).stat()
    except ralphlib.verifier.READ_ERRORS:
        return
    signature = (stat.st_mtime_ns, stat.st_size)
    if signature == context.tasks_signature:
        return
    context.tasks_signature = signature
    for t in read_task_statuses(options):
        if t.status != 'in-progress' or t.id in context.in_progress_tasks:
            continue
        context.in_progress_tasks.add(t.id)
        if not mark_started(context, t.id):
            continue
        message = task_progress(options, t.id, t.title, str(t.index), str(t.count), 'start')
        write_progress(context, message)
        print_progress(options, context, ralphlib.types.MessageType.PROGRESS, message)
        write_progress_eol(context)
        print_progress_eol(options, context)
        append_message_type(context, ralphlib.types.MessageType.PROGRESS)


def indent_lines(s: str, indent: str = '  ') -> str:
    if not s:
        return ''
    return '\n'.join(f'{indent}{line}' for line in s.splitlines())


def get_run_in_background(content: dict[str, typing.Any]) -> bool:
    input_field = content.get('input', {})
    if input_field:
        run_in_background = input_field.get('run_in_background', False)
        if isinstance(run_in_background, bool):
            return run_in_background
    return False


def get_tool_input(content: dict[str, typing.Any]) -> str:
    tool_input = ''
    input_field = content.get('input', {})
    if input_field:
        tool_input = input_field_to_content(input_field)
    return indent_lines(tool_input)


def input_field_to_content(input_field: dict[str, typing.Any]) -> str:
    regular_fields = [
        'command',
        'description',
        'file_path',
        'pattern',
        'query',
        'question',
        'reason',
        'run_id',
        'skill',
        'stop',
        'task_id',
        'title',
        'url',
    ]
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
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    payload: dict[str, typing.Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    is_error = payload.get('is_error', False)
    result = payload.get('result', '')

    if is_error:
        set_error(context, True)
        return ralphlib.types.MessageType.ERROR, result

    if result:
        if is_stop(options, result):
            set_complete(context, True)
            return ralphlib.types.MessageType.COMPLETE, ''

    return ralphlib.types.MessageType.NONE, line


def process_stream_event(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    payload: dict[str, typing.Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    event = payload.get('event') or {}
    etype = event.get('type', '')

    if etype in ['message_delta', 'message_start', 'message_stop']:
        return ralphlib.types.MessageType.NONE, ''

    if etype == 'content_block_start':
        content_block = event.get('content_block') or {}
        cb_type = content_block.get('type', '')
        if cb_type == 'text':
            return ralphlib.types.MessageType.CONTENT_START, content_block.get('text', '')
        if cb_type == 'tool_use':
            return ralphlib.types.MessageType.NONE, ''

    if etype == 'content_block_stop':
        return ralphlib.types.MessageType.CONTENT_STOP, ''

    if etype == 'content_block_delta':
        delta = event.get('delta') or {}
        cb_type = delta.get('type', '')
        if cb_type == 'text_delta':
            return ralphlib.types.MessageType.CONTENT_DELTA, delta.get('text', '')
        if cb_type == 'input_json_delta':
            return ralphlib.types.MessageType.NONE, ''
    return ralphlib.types.MessageType.NONE, line


def process_rate_limit_event(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    payload: dict[str, typing.Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    return ralphlib.types.MessageType.NONE, line


def process_tool_progress(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    payload: dict[str, typing.Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    return ralphlib.types.MessageType.NONE, line


def process_command_lifecycle(
    options: ralphlib.options.RalpherOptions,
    context: IterationContext,
    payload: dict[str, typing.Any],
    line: str,
) -> tuple[ralphlib.types.MessageType, str]:
    return ralphlib.types.MessageType.NONE, line
