from typing import TYPE_CHECKING

import jinja2

import ralphlib.exceptions

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions


def render(options: RalpherOptions, prompt: str, iteration: int) -> str:
    context: dict[str, str] = {
        'iteration': str(iteration),
    }
    if options.task_file:
        context['task_file'] = options.task_file
    for var in options.vars:
        if '=' not in var:
            raise ralphlib.exceptions.InvalidVarFormat(f"Invalid var format: '{var}', expected key=value")
        key, value = var.split('=', 1)
        context[key] = value

    template = jinja2.Template(prompt)
    prompt = template.render(**context)
    return prompt
