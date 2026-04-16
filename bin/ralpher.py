#!/usr/bin/env python
import sys

import ralphlib.looper
import ralphlib.options


def main() -> None:
    error = ralphlib.looper.loop(ralphlib.options.parse_options())
    if error:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
