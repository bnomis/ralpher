import json
import pathlib
import typing

if typing.TYPE_CHECKING:
    import ralphlib.options


def default_settings() -> dict[str, typing.Any]:
    """Return a fresh copy of the built-in settings, nested dicts included.

    Replaces the module-level dict `default_settings`, whose shallow `.copy()`
    shared the nested `theme` dict between every caller.
    """
    return {
        'theme': {
            'alert': 'bold red',
            'content_delta': 'cyan',
            'default': 'grey30',
            'error': 'red',
            'progress': 'yellow',
            'regular': 'grey30',
            'system': 'yellow',
            'tool_use': 'magenta',
        },
    }


def load_settings(options: ralphlib.options.RalpherOptions) -> ralphlib.options.RalpherOptions:
    options.settings = default_settings()
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


def load_settings_from_file(options: ralphlib.options.RalpherOptions, paths: str | pathlib.Path) -> ralphlib.options.RalpherOptions:
    path = pathlib.Path(paths).expanduser().resolve()
    if path.is_file():
        with path.open('r', encoding='utf-8') as f:
            file_settings = json.load(f)
        options.settings.update(file_settings)
    return options
