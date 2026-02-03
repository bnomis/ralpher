from typing import TYPE_CHECKING

import ralphlib.logger

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions


def prt(options: RalpherOptions, s: str, iteration: int) -> None:
    if options.progress:
        path = ralphlib.logger.log_file(options, options.progress, iteration)
        with path.open('a', encoding='utf-8') as f:
            f.write(s)

    if options.quiet:
        return
    print(s, end='', flush=True)
