import pathlib
import re
import typing

import jinja2.exceptions
import jinja2.sandbox

import ralphlib.exceptions

if typing.TYPE_CHECKING:
    import ralphlib.options


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = value.strip().strip('-')
    return value


def task_file_slug(task_file: str) -> str:
    path = pathlib.Path(task_file)
    parts = path.parts
    if len(parts) >= 2:
        slug = parts[-2] + '-' + path.stem
    else:
        slug = path.stem
    return slugify(slug)


BUILTIN_VARS = (
    'iteration',
    'iterations',
    'task_file',
    'task_file_relative_path',
    'worktree',
    'worktree_name',
    'worktree_setup',
)


def parse_vars(options: ralphlib.options.RalpherOptions) -> dict[str, str]:
    """Split the KEY=VALUE entries of --vars.

    Raises:
        InvalidVarFormatError: an entry has no `=` or names a built-in variable.
    """
    parsed: dict[str, str] = {}
    for var in options.vars:
        if '=' not in var:
            raise ralphlib.exceptions.InvalidVarFormatError(f"Invalid var format: '{var}', expected key=value")
        key, value = var.split('=', 1)
        if key in BUILTIN_VARS:
            raise ralphlib.exceptions.InvalidVarFormatError(f"Invalid var: '{key}' is a built-in template variable")
        parsed[key] = value
    return parsed


def render(options: ralphlib.options.RalpherOptions, prompt: str, iteration: int) -> str:
    """Render the prompt template.

    The context includes `worktree_setup`: a new list of the commands from
    `options.settings['worktree_setup']` with `--worktree`, else an empty list.

    Raises:
        InvalidVarFormatError: `--vars` is malformed or names a built-in variable.
        PromptTemplateError: the prompt has a syntax error or uses something the sandbox blocks.
    """
    context: dict[str, str | bool | list[str]] = {
        'iteration': str(iteration),
        'iterations': str(options.iterations),
        'task_file': '',
        'task_file_relative_path': '',
        'worktree': False,
        'worktree_name': '',
        'worktree_setup': [],
    }
    cwd_path = task_file_path = task_file_relative_path = None
    if options.cwd:
        cwd_path = pathlib.Path(options.cwd).resolve().expanduser()

    if options.task_file:
        task_file_path = pathlib.Path(options.task_file).resolve().expanduser()
        context['task_file'] = str(task_file_path)
        context['task_file_relative_path'] = str(task_file_path)
        if cwd_path and task_file_path.is_relative_to(cwd_path):
            task_file_relative_path = task_file_path.relative_to(cwd_path)
            context['task_file_relative_path'] = str(task_file_relative_path)

    if options.worktree:
        context['worktree'] = True
        if options.task_file:
            context['worktree_name'] = task_file_slug(options.task_file)
        context['worktree_setup'] = list(options.settings.get('worktree_setup', []))

    context.update(parse_vars(options))

    try:
        return jinja2.sandbox.SandboxedEnvironment().from_string(prompt).render(**context)
    except jinja2.exceptions.SecurityError as e:
        # auditme: accept[except-interpolation] the message is printed as an Error line, which shows no traceback
        raise ralphlib.exceptions.PromptTemplateError(f'The prompt uses something the template sandbox blocked: {e.message}') from e
    except jinja2.exceptions.TemplateSyntaxError as e:
        # auditme: accept[except-interpolation] the message is printed as an Error line, which shows no traceback
        raise ralphlib.exceptions.PromptTemplateError(f'The prompt has a template syntax error on line {e.lineno}: {e.message}') from e
