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

    console_print(options, message, message_type)


def console_print(
    options: RalpherOptions,
    message: str,
    message_type: ralphlib.types.MessageType = ralphlib.types.MessageType.REGULAR,
) -> None:
    console.print(message, style=type_to_style(options, message_type), end='', soft_wrap=True)


def type_to_style(
    options: RalpherOptions,
    message_type: ralphlib.types.MessageType,
) -> str:
    s = ralphlib.types.message_type_to_str.get(message_type, 'regular')
    if s in options.settings['theme']:
        return options.settings['theme'][s]
    return options.settings['theme'].get('default', 'grey30')
