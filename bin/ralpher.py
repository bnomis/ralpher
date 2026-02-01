#!/usr/bin/env python
import ralphlib.looper
import ralphlib.options


def main() -> None:
    ralphlib.looper.loop(ralphlib.options.parse_options())


if __name__ == '__main__':
    main()
