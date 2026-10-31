import typing

import ralphlib.options
import ralphlib.settings


def make_options(**kwargs: typing.Any) -> ralphlib.options.RalpherOptions:
    options = ralphlib.options.RalpherOptions(**kwargs)
    return ralphlib.settings.load_settings(options)


def make_plain_options(**kwargs: typing.Any) -> ralphlib.options.RalpherOptions:
    return ralphlib.options.RalpherOptions(**kwargs)


def make_options_with_settings(**kwargs: typing.Any) -> ralphlib.options.RalpherOptions:
    settings = kwargs.pop('settings', {})
    options = ralphlib.options.RalpherOptions(**kwargs)
    options.settings = settings
    return options
