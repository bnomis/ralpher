from typing import TYPE_CHECKING

import jinja2

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions


def render(options: RalpherOptions, prompt: str, iteration: int) -> str:
    if not options.vars:
        return prompt

    context: dict[str, str] = {
        'iteration': str(iteration),
    }
    for var in options.vars:
        if '=' not in var:
            continue
        key, value = var.split('=', 1)
        context[key] = value

    template = jinja2.Template(prompt)
    prompt = template.render(**context)
    return prompt
