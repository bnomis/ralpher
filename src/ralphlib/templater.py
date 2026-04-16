import pathlib
import re
from typing import TYPE_CHECKING

import jinja2

import ralphlib.exceptions

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions


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


def render(options: RalpherOptions, prompt: str, iteration: int) -> str:
    context: dict[str, str | bool] = {
        'iteration': str(iteration),
        'iterations': str(options.iterations),
        'worktree': False,
        'worktree_name': '',
    }
    if options.task_file:
        context['task_file'] = options.task_file
    if options.worktree:
        context['worktree'] = True
        if options.task_file:
            context['worktree_name'] = task_file_slug(options.task_file)

    for var in options.vars:
        if '=' not in var:
            raise ralphlib.exceptions.InvalidVarFormat(f"Invalid var format: '{var}', expected key=value")
        key, value = var.split('=', 1)
        context[key] = value

    template = jinja2.Template(prompt)
    prompt = template.render(**context)
    return prompt
