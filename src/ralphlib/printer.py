from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions


def prt(options: RalpherOptions, s: str) -> None:
    if options.quiet:
        return
    print(s)
