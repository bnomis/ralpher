import datetime
import os.path
import pathlib
import re
import shlex
import subprocess
import time
from typing import TYPE_CHECKING, Any

import loguru
import tzlocal
from jinja2.sandbox import SandboxedEnvironment

import ralphlib.types

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions
    from ralphlib.types import RalpherEventType


def event(
    options: RalpherOptions,
    event_type: RalpherEventType,
    event_context: dict[str, Any],
) -> None:
    hooks = options.settings.get('hooks', {})
    if not hooks:
        return
    event_type_string = ralphlib.types.ralpher_event_type_to_str.get(event_type, 'unknown')
    if event_type_string not in hooks:
        return

    hook_templates = options.settings.get('hook_templates', True)
    context = {}
    if hook_templates:
        context = make_context(options, event_type, event_context)

    for cmd in hooks[event_type_string]:
        if hook_templates:
            cmd = preprocess_hook(cmd, context)
        run_hook(cmd)


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
    cwd = task_file = task_file_number_str = ''
    if options.cwd:
        cwd_path = pathlib.Path(options.cwd).resolve().expanduser()
        cwd = str(cwd_path)
    if options.task_file:
        task_file = options.task_file
        _, tail = os.path.split(task_file)
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
        'cwd_basename': pathlib.PurePosixPath(cwd).name if cwd else '',
        'cwd_dirname': str(pathlib.PurePosixPath(cwd).parent) if cwd else '',
        'cwd': cwd,
        'datetime_local': now_local.isoformat(),
        'datetime_utc': now_utc.isoformat().replace('+00:00', 'Z'),
        'event_type': ralphlib.types.ralpher_event_type_to_str[event_type],
        'iteration_count': str(options.iteration_count),
        'iterations': str(options.iterations),
        'ralpher_root': str(ralpher_root()),
        'task_file_basename': pathlib.PurePosixPath(task_file).name if task_file else '',
        'task_file_dir_basename': pathlib.PurePosixPath(task_file).parent.name if task_file else '',
        'task_file_dirname': str(pathlib.PurePosixPath(task_file).parent) if task_file else '',
        'task_file_number': task_file_number_str,
        'task_file_stem': pathlib.PurePosixPath(task_file).stem if task_file else '',
        'task_file_suffix': pathlib.PurePosixPath(task_file).suffix if task_file else '',
        'task_file': task_file,
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


def preprocess_hook(cmd: str, context: dict[str, Any]) -> str:
    env = SandboxedEnvironment()

    env.filters['basename'] = lambda p: pathlib.PurePosixPath(p).name
    env.filters['dirname'] = lambda p: str(pathlib.PurePosixPath(p).parent)
    env.filters['stem'] = lambda p: pathlib.PurePosixPath(p).stem
    env.filters['suffix'] = lambda p: pathlib.PurePosixPath(p).suffix

    template = env.from_string(cmd)
    return template.render(**context)


def run_hook(cmd: str) -> None:
    # double spaces
    cmd = re.sub(r'\s+', ' ', cmd)
    args = shlex.split(cmd)
    try:
        subprocess.Popen(  # noqa: S603
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        loguru.logger.exception(f'Exception running hook: "{cmd}": {e}')
