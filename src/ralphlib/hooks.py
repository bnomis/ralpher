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
    cwd = task_file = ''
    if options.cwd:
        cwd_path = pathlib.Path(options.cwd).resolve().expanduser()
        cwd = str(cwd_path)
    if options.task_file:
        task_file = options.task_file

    context: dict[str, str] = {
        'cwd': cwd,
        'datetime_local': now_local.isoformat(),
        'datetime_utc': now_utc.isoformat().replace('+00:00', 'Z'),
        'event_type': ralphlib.types.ralpher_event_type_to_str[event_type],
        'iterations': str(options.iterations),
        'ralpher_root': str(ralpher_root()),
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
