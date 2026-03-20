from typing import TYPE_CHECKING

import colorama

import ralphlib.logger
import ralphlib.types

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions


def prt(
    options: RalpherOptions,
    message: str,
    iteration: int,
    dont_print: bool = False,
    message_type: ralphlib.types.MessageType = ralphlib.types.MessageType.REGULAR,
) -> None:
    if options.progress:
        path = ralphlib.logger.log_file(options, options.progress, iteration)
        with path.open('a', encoding='utf-8') as f:
            f.write(message)

    if options.quiet or dont_print:
        return

    msg_color = {
        ralphlib.types.MessageType.REGULAR: colorama.Fore.WHITE,
        ralphlib.types.MessageType.CONTENT_DELTA: colorama.Fore.CYAN,
        ralphlib.types.MessageType.ERROR: colorama.Fore.RED,
        ralphlib.types.MessageType.SYSTEM: colorama.Fore.YELLOW,
        ralphlib.types.MessageType.TOOL_USE: colorama.Fore.MAGENTA,
    }
    print(msg_color.get(message_type, colorama.Fore.WHITE) + message + colorama.Style.RESET_ALL, end='', flush=True)
