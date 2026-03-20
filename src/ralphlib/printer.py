from typing import TYPE_CHECKING

import rich.console

import ralphlib.logger
import ralphlib.types

console = rich.console.Console(highlight=False)

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

    console_print(message, message_type)


def console_print(
    message: str,
    message_type: ralphlib.types.MessageType = ralphlib.types.MessageType.REGULAR,
) -> None:
    console.print(message, style=type_to_style(message_type), end='', soft_wrap=True)


def type_to_style(message_type: ralphlib.types.MessageType) -> str:
    return {
        ralphlib.types.MessageType.REGULAR: 'grey30',
        ralphlib.types.MessageType.CONTENT_DELTA: 'cyan',
        ralphlib.types.MessageType.ERROR: 'red',
        ralphlib.types.MessageType.SYSTEM: 'yellow',
        ralphlib.types.MessageType.TOOL_USE: 'magenta',
        ralphlib.types.MessageType.ALERT: 'bold red',
    }.get(message_type, 'grey30')
