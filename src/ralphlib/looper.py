import datetime
import sys
from typing import TYPE_CHECKING

import colorama

import ralphlib.iteration
import ralphlib.logger
import ralphlib.printer
import ralphlib.templater

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions


def loop(options: RalpherOptions) -> None:
    colorama.just_fix_windows_console()

    content = ''
    if options.prompt:
        with open(options.prompt, 'r', encoding='utf-8') as f:
            content = f.read()
    elif options.prompts:
        content = options.prompts
    if not content:
        sys.exit('Error: No prompt provided. Use --prompt or provide a prompt as a positional argument.')

    ralphlib.logger.init(options)

    ralphlib.printer.prt(options, 'Start\n')
    ralphlib.printer.prt(options, f'Agent:\n{options.agent}\n')
    ralphlib.printer.prt(options, f'Prompt:\n{content}\n')
    ralphlib.printer.prt(options, f'Iterations: {options.iterations}\n')

    for i in range(1, options.iterations + 1):
        now = datetime.datetime.now().isoformat()
        ralphlib.printer.prt(options, f'Iteration {i}/{options.iterations} at {now}\n')
        p = ralphlib.templater.render(options, content, i)

        ralphlib.iteration.run(options, prompt=p, iteration=i)
        ralphlib.printer.prt(options, '\n')

    ralphlib.printer.prt(options, '\nDone')
