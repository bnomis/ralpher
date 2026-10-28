import datetime
import pathlib
import re
import shlex
import subprocess
import time
from typing import TYPE_CHECKING, Any

import loguru
import tzlocal
from jinja2.sandbox import SandboxedEnvironment

import ralphlib.giter
import ralphlib.signals
import ralphlib.types
import ralphlib.verifier

if TYPE_CHECKING:
    from collections.abc import Callable

    from ralphlib.options import RalpherOptions
    from ralphlib.types import RalpherEventType

HOOK_VALUE_SENTINEL = '\x00'
HOOK_VALUE_RE = re.compile(f'{HOOK_VALUE_SENTINEL}(\\d+){HOOK_VALUE_SENTINEL}')

processed_hooks: set[str] = set()
seen_task_ids = {}


def event(
    options: RalpherOptions,
    event_type: RalpherEventType,
    event_context: dict[str, Any],
) -> None:
    task_id = event_context.get('task_id')
    task_status = event_context.get('task_status')
    event_type_string = ralphlib.types.ralpher_event_type_to_str.get(event_type, 'unknown')

    # don't process the same hook twice
    ev_str = event_type_string + str(event_context)
    ev_str_hash = str(hash(ev_str))
    tf = ralphlib.verifier.worktree_task_file(options)

    # unblock prompt
    if not tf:
        tf = options.task_file
    wt = ''
    if options.worktree:
        wt = ' worktree'
    prompt = f'unblock task {task_id} in{wt} task file {tf}'

    if ev_str_hash in processed_hooks:
        if event_type == ralphlib.types.RalpherEventType.LLM_TASK_PROGRESS:
            if task_id:
                if task_id in seen_task_ids and seen_task_ids[task_id] == task_status and task_status == 'blocked':
                    loguru.logger.debug(f'Already processed task_id {task_id} with status {task_status}: looks like a loop')
                    ralphlib.signals.set_should_exit(
                        True,
                        reason=f'Loop detected for task {task_id} with status {task_status}',
                        prompt=prompt,
                    )
                    return

                seen_task_ids[task_id] = task_status
        return

    # record the hooks we've seen
    processed_hooks.add(ev_str_hash)

    # check if there are any hooks defined for this event type
    hooks = options.settings.get('hooks', {})
    if hooks and event_type_string in hooks:
        # prepare the context for the hook templates
        hook_templates = options.settings.get('hook_templates', True)
        context = {}
        if hook_templates:
            context = make_context(options, event_type, event_context)

        # run each hook command with the prepared context
        for cmd in hooks[event_type_string]:
            run_hook(cmd, context if hook_templates else None)

    # handle operator input required status
    if task_status == 'operator':
        ralphlib.signals.set_should_exit(
            True,
            reason=f'Operator input required for task {task_id}',
            prompt=prompt,
        )


def ralpher_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent.parent


def make_context(
    options: RalpherOptions,
    event_type: RalpherEventType,
    event_context: dict[str, Any],
) -> dict[str, Any]:
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    local_tz = tzlocal.get_localzone()
    now_local = datetime.datetime.now(local_tz)
    cwd = task_file_number_str = ''
    cwd_path = task_file_path = task_file_relative_path = None
    if options.cwd:
        cwd_path = pathlib.Path(options.cwd).resolve().expanduser()
        cwd = str(cwd_path)

    if options.task_file:
        task_file_relative_path = task_file_path = pathlib.Path(options.task_file).resolve().expanduser()
        if cwd_path and task_file_path.is_relative_to(cwd_path):
            task_file_relative_path = task_file_path.relative_to(cwd_path)

        tail = task_file_path.name
        # try to extract a number from the end of the task file name
        # e.g. "task-1.md" -> "1"
        if tail:
            parts = tail.split('.')
            if len(parts) > 1:
                name_parts = parts[0].split('-')
                if len(name_parts) > 1:
                    try:
                        task_file_number = int(name_parts[-1])
                    except:
                        task_file_number = 0
                    if task_file_number:
                        task_file_number_str = str(task_file_number)

    context: dict[str, str] = {
        'current_iteration': str(options.current_iteration),
        'cwd_basename': cwd_path.name if cwd_path else '',
        'cwd_dirname': str(cwd_path.parent) if cwd_path else '',
        'cwd': cwd,
        'datetime_local': now_local.isoformat(),
        'datetime_utc': now_utc.isoformat().replace('+00:00', 'Z'),
        'event_type': ralphlib.types.ralpher_event_type_to_str[event_type],
        'iteration_count': str(options.iteration_count),
        'iterations': str(options.iterations),
        'last_commit_summary': ralphlib.giter.last_commit_summary(),
        'ralpher_root': str(ralpher_root()),
        'task_file_basename': task_file_path.name if task_file_path else '',
        'task_file_dir_basename': task_file_path.parent.name if task_file_path else '',
        'task_file_dirname': str(task_file_path.parent) if task_file_path else '',
        'task_file_number': task_file_number_str,
        'task_file_stem': task_file_path.stem if task_file_path else '',
        'task_file_suffix': task_file_path.suffix if task_file_path else '',
        'task_file': str(task_file_path) if task_file_path else '',
        'task_file_relative_path': str(task_file_relative_path) if task_file_relative_path else '',
        'time_epoch': str(int(time.time())),
    }

    hook_icon = options.settings.get('hook_icon', '')
    if hook_icon:
        hook_icon = preprocess_hook(hook_icon, context).strip()
        if hook_icon:
            hook_icon_path = pathlib.Path(hook_icon).resolve().expanduser()
            if hook_icon_path.is_file():
                context['hook_icon'] = str(hook_icon_path)
            else:
                loguru.logger.warning(f'Hook icon file "{hook_icon}" does not exist. Ignoring.')

    hook_sound = options.settings.get('hook_sound', '')
    if hook_sound:
        hook_sound = preprocess_hook(hook_sound, context).strip()
        if hook_sound:
            index = hook_sound.find('/')
            if index != -1:
                hook_sound_path = pathlib.Path(hook_sound).resolve().expanduser()
                if not hook_sound_path.is_file():
                    loguru.logger.warning(f'Hook sound looks like a file but "{hook_sound}" does not exist.')
            context['hook_sound'] = hook_sound

    context.update(event_context)
    return context


def hook_environment(finalize: Callable[[Any], str] | None = None) -> SandboxedEnvironment:
    env = SandboxedEnvironment(finalize=finalize)

    env.filters['basename'] = lambda p: pathlib.PurePosixPath(p).name
    env.filters['dirname'] = lambda p: str(pathlib.PurePosixPath(p).parent)
    env.filters['stem'] = lambda p: pathlib.PurePosixPath(p).stem
    env.filters['suffix'] = lambda p: pathlib.PurePosixPath(p).suffix

    return env


def preprocess_hook(cmd: str, context: dict[str, Any]) -> str:
    """Render a template to a plain string. For values used as paths, not as commands."""
    return hook_environment().from_string(cmd).render(**context)


def render_hook_args(cmd: str, context: dict[str, Any]) -> list[str]:
    """Render a hook command template into an argument list.

    Context values render as sentinels and are spliced back in after the
    command is split, so a value containing quotes, spaces or newlines can
    neither break the parse nor turn into extra arguments.
    """
    values: list[str] = []

    def stash(value: Any) -> str:
        values.append(str(value).replace(HOOK_VALUE_SENTINEL, ''))
        return f'{HOOK_VALUE_SENTINEL}{len(values) - 1}{HOOK_VALUE_SENTINEL}'

    rendered = hook_environment(finalize=stash).from_string(cmd).render(**context)
    return [HOOK_VALUE_RE.sub(lambda m: values[int(m.group(1))], arg) for arg in shlex.split(rendered)]


def run_hook(cmd: str, context: dict[str, Any] | None = None) -> None:
    try:
        args = shlex.split(cmd) if context is None else render_hook_args(cmd, context)
        subprocess.Popen(  # noqa: S603
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        loguru.logger.exception(f'Exception running hook: "{cmd}": {e}')
