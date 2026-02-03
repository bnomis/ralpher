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

    start = datetime.datetime.now()
    now = start.isoformat()

    ralphlib.printer.prt(options, f'Start at {now}\n\n', 0)
    ralphlib.printer.prt(options, f'Agent:\n{options.agent}\n\n', 0)
    ralphlib.printer.prt(options, f'Args:\n{options.args}\n\n', 0)
    ralphlib.printer.prt(options, f'Prompt:\n{content}\n\n', 0)
    ralphlib.printer.prt(options, f'Iterations: {options.iterations}\n\n', 0)
    for i in range(1, options.iterations + 1):
        loop_start = datetime.datetime.now()
        now = loop_start.isoformat()

        p = ralphlib.templater.render(options, content, i)
        s = f'\nStarting iteration {i}/{options.iterations} at {now}\nPrompt:\n{p}\n\n'
        ralphlib.printer.prt(options, s, 0)
        ralphlib.printer.prt(options, s, i)

        complete = ralphlib.iteration.run(options, prompt=p, iteration=i)

        loop_end = datetime.datetime.now()
        now = loop_end.isoformat()
        loop_td = loop_end - loop_start

        s = f'\nEnding iteration {i}/{options.iterations} at {now}\n'
        ralphlib.printer.prt(options, s, 0)
        ralphlib.printer.prt(options, s, i)

        s = f'Time for iteration {i}: {timedelta_to_readable(loop_td)}\n\n'
        ralphlib.printer.prt(options, s, 0)
        ralphlib.printer.prt(options, s, i)

        if complete:
            s = f'\n{"=" * 5} Loop complete signal received, stopping after {i} iteration{"s" if i != 1 else ""}. {"=" * 5}\n\n'
            ralphlib.printer.prt(options, s, 0)
            ralphlib.printer.prt(options, s, i)
            break

    end = datetime.datetime.now()
    now = end.isoformat()
    td = end - start

    ralphlib.printer.prt(options, f'\n\nEnd at {now}\n', 0)
    ralphlib.printer.prt(options, f'Total time: {timedelta_to_readable(td)}\n', 0)


def timedelta_to_readable(td: datetime.timedelta, show_seconds: bool = True) -> str:
    if td == datetime.timedelta(0):
        return '0'

    total_seconds = int(td.total_seconds())
    if total_seconds == 0:
        return '0'

    # Handle negative durations
    sign = '-' if total_seconds < 0 else ''
    total_seconds = abs(total_seconds)

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f'{days} days')
    if hours or days:  # show hours if there are days
        parts.append(f'{hours} hours')
    if minutes or hours or days:
        parts.append(f'{minutes} minutes')
    if show_seconds or not parts:  # always show seconds if nothing else
        parts.append(f'{seconds} seconds')

    return sign + ' '.join(parts)
