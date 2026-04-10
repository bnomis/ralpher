import json
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions

default_settings = {
    'theme': {
        'alert': 'bold red',
        'content_delta': 'cyan',
        'default': 'grey30',
        'error': 'red',
        'regular': 'grey30',
        'system': 'yellow',
        'tool_use': 'magenta',
    },
}


def load_settings(options: RalpherOptions) -> RalpherOptions:
    options.settings = default_settings.copy()
    # home
    options = load_settings_from_file(options, '~/.ralpher/settings.json')
    # cwd
    if options.cwd:
        cwd = pathlib.Path(options.cwd).resolve()
        options = load_settings_from_file(options, cwd / '.ralpher/settings.json')
    # cli
    if options.settings_file:
        return load_settings_from_file(options, options.settings_file)
    return options


def load_settings_from_file(options: RalpherOptions, paths: str | pathlib.Path) -> RalpherOptions:
    path = pathlib.Path(paths).expanduser().resolve()
    if path.is_file():
        with path.open('r', encoding='utf-8') as f:
            file_settings = json.load(f)
        options.settings.update(file_settings)
    return options
