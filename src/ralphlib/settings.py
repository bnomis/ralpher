import json
import pathlib
import typing

import ralphlib.exceptions

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
    options = load_settings_from_file(options, '~/.ralpher/settings.json')
    if options.cwd:
        cwd = pathlib.Path(options.cwd).resolve()
        options = load_settings_from_file(options, cwd / '.ralpher/settings.json')
    if options.settings_file:
        return load_settings_from_file(options, options.settings_file)
    return options


def load_settings_from_file(options: ralphlib.options.RalpherOptions, paths: str | pathlib.Path) -> ralphlib.options.RalpherOptions:
    path = pathlib.Path(paths).expanduser().resolve()
    if path.is_file():
        try:
            with path.open('r', encoding='utf-8') as f:
                file_settings = json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ralphlib.exceptions.SettingsError(f'Cannot read settings file {path}') from e
        if not isinstance(file_settings, dict):
            raise ralphlib.exceptions.SettingsError(f'Settings file {path} must hold a JSON object')
        validate_settings(file_settings, path)
        options.settings.update(file_settings)
    return options


def validate_settings(file_settings: dict[str, typing.Any], path: pathlib.Path) -> None:
    """Raise SettingsError when `hooks`, `hook_templates`, `theme` or `worktree_setup` has the wrong shape."""
    hooks = file_settings.get('hooks', {})
    if not isinstance(hooks, dict):
        raise ralphlib.exceptions.SettingsError(f'Settings file {path}: hooks must be an object')
    for event, commands in hooks.items():
        if not isinstance(commands, list) or not all(isinstance(c, str) for c in commands):
            raise ralphlib.exceptions.SettingsError(f'Settings file {path}: hooks.{event} must be a list of strings')
    if not isinstance(file_settings.get('hook_templates', True), bool):
        raise ralphlib.exceptions.SettingsError(f'Settings file {path}: hook_templates must be true or false')
    if not isinstance(file_settings.get('theme', {}), dict):
        raise ralphlib.exceptions.SettingsError(f'Settings file {path}: theme must be an object')
    worktree_setup = file_settings.get('worktree_setup', [])
    if not isinstance(worktree_setup, list) or not all(isinstance(c, str) for c in worktree_setup):
        raise ralphlib.exceptions.SettingsError(f'Settings file {path}: worktree_setup must be a list of strings')
