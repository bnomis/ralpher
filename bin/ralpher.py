#!/usr/bin/env python
import sys

import ralphlib.exceptions
import ralphlib.looper
import ralphlib.options


def main() -> None:
    try:
        options = ralphlib.options.load_options()
        if options.cleanup:
            ralphlib.looper.print_cleanup_cmds(options)
            sys.exit(0)
        error = ralphlib.looper.loop(options)
    except ralphlib.exceptions.RalpherError as e:
        # auditme: accept[except-interpolation] the message goes to the console, which shows no traceback
        sys.exit(f'Error: {e}')
    if error:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
