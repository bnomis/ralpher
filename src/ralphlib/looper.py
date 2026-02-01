import datetime
import os
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

    if options.cwd:
        os.chdir(options.cwd)

    content = ''
    if options.prompt:
        with open(options.prompt, 'r', encoding='utf-8') as f:
            content = f.read()
    elif options.prompts:
        content = options.prompts
    if not content:
        sys.exit('Error: No prompt provided. Use --prompt or provide a prompt as a positional argument.')

    ralphlib.logger.init(options)

    now = datetime.datetime.now().isoformat()
    ralphlib.printer.prt(options, f'Start at {now}\n', 0)
    ralphlib.printer.prt(options, f'Agent:\n{options.agent}\n', 0)
    ralphlib.printer.prt(options, f'Args:\n{options.args}\n', 0)
    ralphlib.printer.prt(options, f'Prompt:\n{content}\n', 0)
    ralphlib.printer.prt(options, f'Iterations: {options.iterations}\n', 0)
    for i in range(1, options.iterations + 1):
        now = datetime.datetime.now().isoformat()
        p = ralphlib.templater.render(options, content, i)
        ralphlib.printer.prt(options, f'Iteration {i}/{options.iterations} at {now}\nPrompt:\n{p}\n', i)

        complete = ralphlib.iteration.run(options, prompt=p, iteration=i)
        ralphlib.printer.prt(options, '\n', i)

        if complete:
            ralphlib.printer.prt(options, f'Loop complete signal received, stopping after {i} iteration{"s" if i != 1 else ""}.\n', i)
            break

    now = datetime.datetime.now().isoformat()
    ralphlib.printer.prt(options, f'End at {now}\n', 0)
