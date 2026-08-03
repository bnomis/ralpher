#!/usr/bin/env python
import sys

import ralphlib.looper
import ralphlib.options


def main() -> None:
    options = ralphlib.options.parse_options()
    if options.cleanup:
        ralphlib.looper.print_cleanup_cmds(options)
        sys.exit(0)

    error = ralphlib.looper.loop(options)
    if error:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
