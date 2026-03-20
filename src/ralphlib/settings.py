import json
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions

default_settings = {}


def load_settings(options: RalpherOptions) -> RalpherOptions:
    options.settings = default_settings.copy()
    options = load_settings_from_file(options, '~/.ralpher/settings.json')
    if options.settings_file:
        return load_settings_from_file(options, options.settings_file)
    return options


def load_settings_from_file(options: RalpherOptions, paths: str) -> RalpherOptions:
    path = pathlib.Path(paths)
    path = path.expanduser()
    path = path.resolve()
    if path.is_file():
        with path.open('r', encoding='utf-8') as f:
            file_settings = json.load(f)
        options.settings.update(file_settings)
    return options
