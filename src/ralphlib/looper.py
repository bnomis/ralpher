import datetime
import os
import signal
import sys
import threading
import types
from typing import TYPE_CHECKING

import colorama
from loguru import logger

import ralphlib.iteration
import ralphlib.logger
import ralphlib.printer
import ralphlib.state
import ralphlib.templater

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions

should_exit = False
should_exit_lock = threading.Lock()


def set_should_exit(value: bool) -> None:
    global should_exit
    with should_exit_lock:
        should_exit = value


def get_should_exit() -> bool:
    with should_exit_lock:
        return should_exit


class GracefulTerminator:
    CTRL_C_PRESS_INTERVAL = 2.5  # seconds
    FIRST_MESSAGE = 'Ctrl+C pressed → Press **once more** to exit'
    SECOND_MESSAGE = '→ Exiting now!'
    EXIT_CODE = 130

    def __init__(self) -> None:
        self.first_press = None
        self.is_shutting_down = False
        signal.signal(signal.SIGINT, self.handler)
        signal.signal(signal.SIGTERM, self.handler)

    def handler(self, signum: int, frame: types.FrameType | None) -> None:
        if self.is_shutting_down:
            print('\nAlready shutting down — forceful exit!')
            sys.exit(1)

        sig_name = signal.Signals(signum).name
        if signum == signal.SIGTERM:
            print(f'\nReceived {sig_name} → shutting down gracefully...')
            self.perform_shutdown()
            return

        now = datetime.datetime.now()
        if self.first_press:
            time_since_first_press = (now - self.first_press).total_seconds()
            if time_since_first_press < self.CTRL_C_PRESS_INTERVAL:
                print(f'\n{self.SECOND_MESSAGE}\n')
                self.perform_shutdown()

        print(f'\n{self.FIRST_MESSAGE}\n')
        self.first_press = now

    def perform_shutdown(self) -> None:
        self.is_shutting_down = True
        set_should_exit(True)


def loop(options: RalpherOptions) -> None:
    colorama.just_fix_windows_console()
    _terminator = GracefulTerminator()

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

    ralphlib.printer.prt(options, f'\n\n{"-" * 80}\n\n', 0)
    ralphlib.printer.prt(options, f'Start at {now}\n\n', 0)
    ralphlib.printer.prt(options, f'Agent:\n{options.agent}\n\n', 0)
    ralphlib.printer.prt(options, f'Args:\n{options.args}\n\n', 0)
    ralphlib.printer.prt(options, f'Prompt:\n{content}\n\n', 0)
    ralphlib.printer.prt(options, f'Iterations: {options.iterations}\n\n', 0)

    # state json
    new_state = {
        'start': now,
        'agent': options.agent,
        'args': options.args,
        'prompt': content,
        'max_iterations': options.iterations,
    }
    ralphlib.state.add_to_state(options, new_state)

    loop_times = []

    for i in range(1, options.iterations + 1):
        loop_start = datetime.datetime.now()
        now = loop_start.isoformat()

        print_both(options, f'\n\n{"-" * 80}\n\n', i)
        p = ralphlib.templater.render(options, content, i)
        s = f'\nStarting iteration {i}/{options.iterations} at {now}\n\nPrompt:\n{p}\n\n'
        print_both(options, s, i)

        # state json
        iterations_key = ralphlib.logger.iteration_to_str(options, i)
        state_payload = {
            'start': loop_start.isoformat(),
        }
        ralphlib.state.add_to_state(options, state_payload, key1='iterations', key2=iterations_key)

        # run the iteration
        try:
            complete, error = ralphlib.iteration.run(options, prompt=p, iteration=i)
        except Exception as e:
            logger.exception(f'Exception during iteration {i}: {e}')
            s = f'\nException during iteration {i}\n'
            ralphlib.printer.prt(options, s, 0)
            ralphlib.printer.prt(options, s, i)
            break

        loop_end = datetime.datetime.now()
        now = loop_end.isoformat()
        loop_td = loop_end - loop_start

        s = f'\nEnding iteration {i}/{options.iterations} at {now}\n'
        print_both(options, s, i)

        loop_time_str = timedelta_to_readable(loop_td)
        loop_times.append(loop_time_str)
        s = f'Time for iteration {i}: {loop_time_str}\n\n'
        print_both(options, s, i)
        print_both(options, f'\n\n{"-" * 80}\n\n', i)

        # state json
        state_payload = {
            'end': loop_end.isoformat(),
            'time_readable': loop_time_str,
            'time_seconds': loop_td.total_seconds(),
        }
        ralphlib.state.add_to_state(options, state_payload, key1='iterations', key2=iterations_key)

        if complete or error or get_should_exit():
            words = []
            if complete:
                words.append('complete')
            if error:
                words.append('error')
            if get_should_exit():
                words.append('termination')

            s = f'\n{"=" * 5} Loop {", ".join(words)} signal received, stopping after {i} iteration{"s" if i != 1 else ""}. {"=" * 5}\n\n'
            print_both(options, s, i)
            break

    ralphlib.printer.prt(options, '\n\nLoop times\n\n', 0)
    num_loops = len(loop_times)
    num_loops_str_len = len(str(num_loops))
    for i, loop_time_str in enumerate(loop_times, start=1):
        s = f'{i:>{num_loops_str_len}}: {loop_time_str}\n'
        ralphlib.printer.prt(options, s, 0)

    end = datetime.datetime.now()
    now = end.isoformat()
    td = end - start
    readable = timedelta_to_readable(td)

    ralphlib.printer.prt(options, f'\n\nEnd at {now}\n', 0)
    ralphlib.printer.prt(options, f'Total time: {readable}\n', 0)

    # state json
    new_state = {
        'end': now,
        'total_time_readable': readable,
        'total_time_seconds': td.total_seconds(),
    }
    ralphlib.state.add_to_state(options, new_state)


def print_both(options: RalpherOptions, s: str, iteration: int) -> None:
    ralphlib.printer.prt(options, s, 0)
    ralphlib.printer.prt(options, s, iteration, dont_print=True)


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
        parts.append(f'{days} day{"s" if days != 1 else ""}')
    if hours or days:  # show hours if there are days
        parts.append(f'{hours} hour{"s" if hours != 1 else ""}')
    if minutes or hours or days:
        parts.append(f'{minutes} minute{"s" if minutes != 1 else ""}')
    if show_seconds or not parts:  # always show seconds if nothing else
        parts.append(f'{seconds} second{"s" if seconds != 1 else ""}')

    return sign + ' '.join(parts)
