import datetime
import functools
import pathlib
import re
import shlex
import subprocess
import time
import typing

import jinja2
import jinja2.exceptions
import jinja2.runtime
import jinja2.sandbox
import loguru
import tzlocal

import ralphlib.exceptions
import ralphlib.giter
import ralphlib.signals
import ralphlib.types
import ralphlib.verifier

if typing.TYPE_CHECKING:
    import ralphlib.options

HOOK_VALUE_SENTINEL = '\x00'
TASK_FILE_NUMBER_RE = re.compile(r'-([0-9]+)$')
HOOK_VALUE_RE = re.compile(f'{HOOK_VALUE_SENTINEL}(\\d+){HOOK_VALUE_SENTINEL}')

# auditme: accept[mutable-module-level-exported] process-lifetime cache, mutated at run time; tests reset it
processed_hooks: set[str] = set()
# auditme: accept[mutable-module-level-exported] process-lifetime cache, mutated at run time; tests reset it
seen_task_ids = {}
SPLICE_VALUES_KEY = 'ralpher_splice_values'


def event(
    options: ralphlib.options.RalpherOptions,
    event_type: ralphlib.types.RalpherEventType,
    event_context: dict[str, typing.Any],
) -> None:
    task_id = event_context.get('task_id')
    task_status = event_context.get('task_status')
    event_type_string = ralphlib.types.ralpher_event_type_to_str.get(event_type, 'unknown')

    # don't process the same hook twice
    ev_str = event_type_string + str(event_context)
    ev_str_hash = str(hash(ev_str))

    if ev_str_hash in processed_hooks:
        if event_type == ralphlib.types.RalpherEventType.LLM_TASK_PROGRESS:
            if task_id:
                if task_id in seen_task_ids and seen_task_ids[task_id] == task_status and task_status == 'blocked':
                    loguru.logger.debug(f'Already processed task_id {task_id} with status {task_status}: looks like a loop')
                    ralphlib.signals.set_should_exit(
                        True,
                        reason=f'Loop detected for task {task_id} with status {task_status}',
                        prompt=unblock_prompt(options, task_id),
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
            context = make_context(options, event_type, event_context, hooks[event_type_string])

        # run each hook command with the prepared context
        for cmd in hooks[event_type_string]:
            run_hook(cmd, context if hook_templates else None)

    # handle operator input required status
    if task_status == 'operator':
        ralphlib.signals.set_should_exit(
            True,
            reason=f'Operator input required for task {task_id}',
            prompt=unblock_prompt(options, task_id),
        )


def unblock_prompt(options: ralphlib.options.RalpherOptions, task_id: str | None) -> str:
    try:
        tf = ralphlib.verifier.agent_task_file(options)
    except ralphlib.verifier.READ_ERRORS:
        return f'unblock task {task_id} in task file {options.task_file} (the worktree tasks file could not be found, so this is the main tasks file)'
    wt = ' worktree' if options.worktree else ''
    return f'unblock task {task_id} in{wt} task file {tf}'


@functools.cache
def ralpher_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent.parent


def make_context(
    options: ralphlib.options.RalpherOptions,
    event_type: ralphlib.types.RalpherEventType,
    event_context: dict[str, typing.Any],
    commands: list[str] | None = None,
) -> dict[str, typing.Any]:
    """Build the template context. Given `commands`, `last_commit_summary` is looked up only if a command or the icon/sound setting names it.

    Raises:
        RalpherError: the local time zone cannot be determined.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_local = datetime.datetime.now(local_timezone())
    context: dict[str, str] = {
        **fixed_context(options.cwd, options.task_file),
        'current_iteration': str(options.current_iteration),
        'datetime_local': now_local.isoformat(),
        'datetime_utc': now_utc.isoformat().replace('+00:00', 'Z'),
        'event_type': ralphlib.types.ralpher_event_type_to_str[event_type],
        'iteration_count': str(options.iteration_count),
        'iterations': str(options.iterations),
        'last_commit_summary': last_commit_summary(options, commands),
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


@functools.cache
def local_timezone() -> datetime.tzinfo:
    """Return the local time zone, looked up once per process.

    Raises:
        RalpherError: the local time zone cannot be determined.
    """
    try:
        return tzlocal.get_localzone()
    except (OSError, LookupError, ValueError) as e:
        raise ralphlib.exceptions.RalpherError('Cannot determine the local time zone') from e


@functools.cache
def fixed_context(cwd: str, task_file: str) -> dict[str, str]:
    """Return the context values that depend only on the working directory and tasks file, which do not change during a run."""
    task_file_number_str = ''
    cwd_path = task_file_path = task_file_relative_path = None
    if cwd:
        cwd_path = pathlib.Path(cwd).resolve().expanduser()

    if task_file:
        task_file_relative_path = task_file_path = pathlib.Path(task_file).resolve().expanduser()
        if cwd_path and task_file_path.is_relative_to(cwd_path):
            task_file_relative_path = task_file_path.relative_to(cwd_path)

        number_match = TASK_FILE_NUMBER_RE.search(task_file_path.stem)
        if number_match:
            task_file_number_str = number_match.group(1)

    return {
        'cwd': str(cwd_path) if cwd_path else '',
        'cwd_basename': cwd_path.name if cwd_path else '',
        'cwd_dirname': str(cwd_path.parent) if cwd_path else '',
        'ralpher_root': str(ralpher_root()),
        'task_file': str(task_file_path) if task_file_path else '',
        'task_file_basename': task_file_path.name if task_file_path else '',
        'task_file_dir_basename': task_file_path.parent.name if task_file_path else '',
        'task_file_dirname': str(task_file_path.parent) if task_file_path else '',
        'task_file_number': task_file_number_str,
        'task_file_relative_path': str(task_file_relative_path) if task_file_relative_path else '',
        'task_file_stem': task_file_path.stem if task_file_path else '',
        'task_file_suffix': task_file_path.suffix if task_file_path else '',
    }


def clear_caches() -> None:
    """Drop every per-run cache; tests call this between cases."""
    ralpher_root.cache_clear()
    local_timezone.cache_clear()
    fixed_context.cache_clear()
    compile_template.cache_clear()
    hook_environment.cache_clear()


def last_commit_summary(options: ralphlib.options.RalpherOptions, commands: list[str] | None) -> str:
    if commands is not None:
        texts = [*commands, str(options.settings.get('hook_icon', '')), str(options.settings.get('hook_sound', ''))]
        if not any('last_commit_summary' in text for text in texts):
            return ''
    return ralphlib.giter.last_commit_summary()


@jinja2.pass_context
def stash(context: jinja2.runtime.Context, value: typing.Any) -> str:
    """Finalizer for `render_hook_args`. Taking the context stops Jinja folding constants at compile time, so a cached template stays valid."""
    values = context[SPLICE_VALUES_KEY]
    values.append(str(value).replace(HOOK_VALUE_SENTINEL, ''))
    return f'{HOOK_VALUE_SENTINEL}{len(values) - 1}{HOOK_VALUE_SENTINEL}'


@functools.cache
def hook_environment(splicing: bool = False) -> jinja2.sandbox.SandboxedEnvironment:
    """Return the shared sandbox. With `splicing`, context values render as sentinels, see `render_hook_args`."""
    env = jinja2.sandbox.SandboxedEnvironment(finalize=stash if splicing else None)

    env.filters['basename'] = lambda p: pathlib.PurePosixPath(p).name
    env.filters['dirname'] = lambda p: str(pathlib.PurePosixPath(p).parent)
    env.filters['stem'] = lambda p: pathlib.PurePosixPath(p).stem
    env.filters['suffix'] = lambda p: pathlib.PurePosixPath(p).suffix

    return env


@functools.cache
# auditme: accept[passthrough-shim] the wrapper exists to cache each compiled template
def compile_template(cmd: str, splicing: bool = False) -> jinja2.Template:
    return hook_environment(splicing).from_string(cmd)


def preprocess_hook(cmd: str, context: dict[str, typing.Any]) -> str:
    """Render a template to a plain string. For values used as paths, not as commands."""
    return compile_template(cmd).render(**context)


def render_hook_args(cmd: str, context: dict[str, typing.Any]) -> list[str]:
    """Render a hook command template into an argument list.

    Context values render as sentinels and are spliced back in after the
    command is split, so a value containing quotes, spaces or newlines can
    neither break the parse nor turn into extra arguments.
    """
    values: list[str] = []
    rendered = compile_template(cmd, True).render({**context, SPLICE_VALUES_KEY: values})
    return [HOOK_VALUE_RE.sub(lambda m: values[int(m.group(1))], arg) for arg in shlex.split(rendered)]


def run_hook(cmd: str, context: dict[str, typing.Any] | None = None) -> None:
    """Start a hook detached. stdout and stderr both go to `DEVNULL` on purpose: nothing reads a hook's output."""
    try:
        args = shlex.split(cmd) if context is None else render_hook_args(cmd, context)
        subprocess.Popen(  # noqa: S603
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except ValueError, OSError, jinja2.exceptions.TemplateError:
        loguru.logger.opt(exception=True).warning(f'Cannot run hook: "{cmd}"')
