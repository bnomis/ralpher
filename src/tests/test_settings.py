import json
import pathlib
import tempfile
import typing
import unittest.mock

import hypothesis
import hypothesis.strategies
import pytest

import ralphlib.exceptions
import ralphlib.options
import ralphlib.settings
import tests.helpers

ECHO_HI = ('echo hi',)
NOTIFY = ('notify',)
SETUP_FIRST = ['pre-commit install', 'uv sync']
SETUP_SECOND = ['make env']


class TestLoadSettingsFromFile:
    def test_nonexistent_file_is_noop(self, tmp_path: typing.Any) -> None:
        options = tests.helpers.make_options_with_settings(settings={'existing': 'value'})
        result = ralphlib.settings.load_settings_from_file(options, str(tmp_path / 'missing.json'))
        assert result.settings == {'existing': 'value'}

    def test_valid_json_file_merges_into_settings(self, tmp_path: typing.Any) -> None:
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'hooks': {'start': list(ECHO_HI)}}))
        options = tests.helpers.make_options_with_settings(settings={'existing': 'value'})
        result = ralphlib.settings.load_settings_from_file(options, str(settings_file))
        assert result.settings == {'existing': 'value', 'hooks': {'start': list(ECHO_HI)}}

    def test_overwrites_existing_keys_on_conflict(self, tmp_path: typing.Any) -> None:
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'key': 'new'}))
        options = tests.helpers.make_options_with_settings(settings={'key': 'old'})
        result = ralphlib.settings.load_settings_from_file(options, str(settings_file))
        assert result.settings['key'] == 'new'

    def test_non_object_top_level_raises_settings_error(self, tmp_path: typing.Any) -> None:
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps(['not', 'an', 'object']))
        options = tests.helpers.make_options_with_settings()
        with pytest.raises(ralphlib.exceptions.SettingsError, match='settings.json'):
            ralphlib.settings.load_settings_from_file(options, str(settings_file))


class TestHookShapes:
    @pytest.mark.parametrize(
        ('content', 'key'),
        [
            ({'hooks': list(NOTIFY)}, 'hooks'),
            ({'hooks': {'end': 'notify'}}, 'hooks.end'),
            ({'hooks': {'end': [*NOTIFY, 3]}}, 'hooks.end'),
            ({'hook_templates': 'false'}, 'hook_templates'),
            ({'theme': 'red'}, 'theme'),
        ],
    )
    def test_wrong_shape_raises_settings_error(self, tmp_path: typing.Any, content: dict[str, typing.Any], key: str) -> None:
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps(content))
        options = tests.helpers.make_options_with_settings()
        with pytest.raises(ralphlib.exceptions.SettingsError, match=rf'settings\.json.*{key}'):
            ralphlib.settings.load_settings_from_file(options, str(settings_file))

    def test_valid_shapes_are_accepted(self, tmp_path: typing.Any) -> None:
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'hooks': {'end': list(NOTIFY)}, 'hook_templates': False, 'theme': {'alert': 'red'}}))
        options = tests.helpers.make_options_with_settings()
        result = ralphlib.settings.load_settings_from_file(options, str(settings_file))
        assert result.settings['hooks'] == {'end': list(NOTIFY)}


class TestLoadSettings:
    def test_applies_default_then_home_then_custom_in_order(self, tmp_path: typing.Any) -> None:
        custom_file = tmp_path / 'custom_settings.json'
        custom_file.write_text(json.dumps({'source': 'custom', 'custom_only': True}))
        options = tests.helpers.make_options_with_settings(settings_file=str(custom_file))
        call_paths: list[str] = []

        def tracking_load(opts: ralphlib.options.RalpherOptions, paths: str) -> ralphlib.options.RalpherOptions:
            call_paths.append(paths)
            if paths == '~/.ralpher/settings.json':
                opts.settings.update({'source': 'home', 'home_only': True})
            else:
                opts.settings.update({'source': 'custom', 'custom_only': True})
            return opts

        with (
            unittest.mock.patch.object(
                ralphlib.settings,
                'default_settings',
                return_value={'source': 'default', 'default_only': True},
            ),
            unittest.mock.patch.object(
                ralphlib.settings,
                'load_settings_from_file',
                side_effect=tracking_load,
            ),
        ):
            result = ralphlib.settings.load_settings(options)

        assert call_paths == ['~/.ralpher/settings.json', str(custom_file)]
        assert result.settings['default_only'] is True
        assert result.settings['home_only'] is True
        assert result.settings['custom_only'] is True
        assert result.settings['source'] == 'custom'

    def test_no_settings_file_only_loads_home_config(self) -> None:
        options = tests.helpers.make_options_with_settings()
        with unittest.mock.patch.object(
            ralphlib.settings,
            'load_settings_from_file',
            wraps=ralphlib.settings.load_settings_from_file,
        ) as mock_load:
            mock_load.return_value = options
            ralphlib.settings.load_settings(options)
        mock_load.assert_called_once_with(options, '~/.ralpher/settings.json')

    def test_settings_file_overrides_home_config_values(self, tmp_path: typing.Any) -> None:
        home_file = tmp_path / '.ralpher' / 'settings.json'
        home_file.parent.mkdir()
        home_file.write_text(json.dumps({'key': 'home', 'home_only': True}))

        custom_file = tmp_path / 'custom.json'
        custom_file.write_text(json.dumps({'key': 'custom', 'custom_only': True}))

        options = tests.helpers.make_options_with_settings(settings_file=str(custom_file))

        home_path = str(home_file)
        original_load = ralphlib.settings.load_settings_from_file

        def patched_load(opts: ralphlib.options.RalpherOptions, paths: str) -> ralphlib.options.RalpherOptions:
            if paths == '~/.ralpher/settings.json':
                return original_load(opts, home_path)
            return original_load(opts, paths)

        with unittest.mock.patch.object(ralphlib.settings, 'load_settings_from_file', side_effect=patched_load):
            result = ralphlib.settings.load_settings(options)

        assert result.settings['key'] == 'custom'
        assert result.settings['home_only'] is True
        assert result.settings['custom_only'] is True


def test_load_settings_theme_is_not_shared(tmp_path: typing.Any) -> None:
    first = tests.helpers.make_options_with_settings(cwd=str(tmp_path))
    second = tests.helpers.make_options_with_settings(cwd=str(tmp_path))
    with unittest.mock.patch.object(ralphlib.settings, 'load_settings_from_file', side_effect=lambda opts, paths: opts):
        ralphlib.settings.load_settings(first)
        ralphlib.settings.load_settings(second)
    assert first.settings['theme'] is not second.settings['theme']
    first.settings['theme']['alert'] = 'changed'
    assert second.settings['theme']['alert'] != 'changed'


class TestDomainErrors:
    def test_invalid_json_raises_settings_error(self, tmp_path: typing.Any) -> None:
        path = tmp_path / 'settings.json'
        path.write_text('{not json')
        options = tests.helpers.make_plain_options()
        options.settings = ralphlib.settings.default_settings()
        with pytest.raises(ralphlib.exceptions.SettingsError, match='settings.json'):
            ralphlib.settings.load_settings_from_file(options, path)

    def test_unreadable_file_raises_settings_error(self, tmp_path: typing.Any) -> None:
        path = tmp_path / 'settings.json'
        path.write_bytes(b'\xff\xfe\x00')
        options = tests.helpers.make_plain_options()
        options.settings = ralphlib.settings.default_settings()
        with pytest.raises(ralphlib.exceptions.SettingsError):
            ralphlib.settings.load_settings_from_file(options, path)


JSON_LEAVES = hypothesis.strategies.none() | hypothesis.strategies.booleans() | hypothesis.strategies.integers() | hypothesis.strategies.text(max_size=8)
JSON_VALUES = hypothesis.strategies.recursive(
    JSON_LEAVES,
    lambda children: (
        hypothesis.strategies.lists(children, max_size=3) | hypothesis.strategies.dictionaries(hypothesis.strategies.text(max_size=8), children, max_size=3)
    ),
    max_leaves=8,
)
THEMES = hypothesis.strategies.dictionaries(hypothesis.strategies.text(min_size=1, max_size=8), hypothesis.strategies.text(max_size=8), max_size=4)


def hooks_are_valid(content: dict[str, typing.Any]) -> bool:
    hooks = content.get('hooks', {})
    if not isinstance(hooks, dict):
        return False
    return all(isinstance(c, list) and all(isinstance(x, str) for x in c) for c in hooks.values())


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(content=JSON_VALUES)
def test_load_settings_from_file_accepts_exactly_the_valid_shapes(content: typing.Any) -> None:
    options = tests.helpers.make_options_with_settings(settings={})
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / 'settings.json'
        path.write_text(json.dumps(content))
        valid = (
            isinstance(content, dict)
            and hooks_are_valid(content)
            and isinstance(content.get('hook_templates', True), bool)
            and isinstance(content.get('theme', {}), dict)
        )
        if valid:
            assert ralphlib.settings.load_settings_from_file(options, path).settings == content
        else:
            with pytest.raises(ralphlib.exceptions.SettingsError):
                ralphlib.settings.load_settings_from_file(options, path)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(theme=THEMES)
def test_load_settings_applies_the_cli_settings_file_last(theme: dict[str, str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / 'settings.json'
        path.write_text(json.dumps({'theme': theme}))
        options = tests.helpers.make_plain_options(settings_file=str(path))
        assert ralphlib.settings.load_settings(options).settings['theme'] == theme


class TestValidateSettings:
    PATH = pathlib.Path('settings.json')

    def test_valid_settings_pass(self) -> None:
        # auditme: accept[duplicate-side-effect-per-target] one test per validation branch
        ralphlib.settings.validate_settings({'hooks': {'start': ['echo greet']}, 'hook_templates': False, 'theme': {'a': 'b'}}, self.PATH)

    def test_empty_settings_pass(self) -> None:
        ralphlib.settings.validate_settings({}, self.PATH)

    def test_hooks_not_an_object_raises(self) -> None:
        with pytest.raises(ralphlib.exceptions.SettingsError, match='hooks must be an object'):
            ralphlib.settings.validate_settings({'hooks': ['echo salute']}, self.PATH)

    def test_hook_commands_not_a_list_raises(self) -> None:
        with pytest.raises(ralphlib.exceptions.SettingsError, match=r'hooks\.start must be a list of strings'):
            ralphlib.settings.validate_settings({'hooks': {'start': 'echo hi'}}, self.PATH)

    def test_hook_command_not_a_string_raises(self) -> None:
        with pytest.raises(ralphlib.exceptions.SettingsError, match=r'hooks\.end must be a list of strings'):
            ralphlib.settings.validate_settings({'hooks': {'end': ['echo hi', 3]}}, self.PATH)

    def test_hook_templates_not_a_bool_raises(self) -> None:
        with pytest.raises(ralphlib.exceptions.SettingsError, match='hook_templates must be true or false'):
            ralphlib.settings.validate_settings({'hook_templates': 'yes'}, self.PATH)

    def test_theme_not_an_object_raises(self) -> None:
        with pytest.raises(ralphlib.exceptions.SettingsError, match='theme must be an object'):
            ralphlib.settings.validate_settings({'theme': 'dark'}, self.PATH)

    def test_error_names_the_file(self) -> None:
        with pytest.raises(ralphlib.exceptions.SettingsError, match='settings.json'):
            ralphlib.settings.validate_settings({'theme': 1}, self.PATH)

    def test_worktree_setup_list_of_strings_passes(self) -> None:
        ralphlib.settings.validate_settings({'worktree_setup': SETUP_FIRST}, self.PATH)

    @pytest.mark.parametrize('value', ['uv sync', ['uv sync', 3], {'cmd': 'uv sync'}])
    def test_worktree_setup_wrong_shape_raises(self, value: typing.Any) -> None:
        with pytest.raises(
            ralphlib.exceptions.SettingsError,
            match=r'^Settings file settings\.json: worktree_setup must be a list of strings$',
        ):
            ralphlib.settings.validate_settings({'worktree_setup': value}, self.PATH)


def test_later_file_worktree_setup_replaces_earlier_whole(tmp_path: typing.Any) -> None:
    first = tmp_path / 'first.json'
    first.write_text(json.dumps({'worktree_setup': SETUP_FIRST}))
    second = tmp_path / 'second.json'
    second.write_text(json.dumps({'worktree_setup': SETUP_SECOND}))
    options = tests.helpers.make_options_with_settings()
    ralphlib.settings.load_settings_from_file(options, str(first))
    result = ralphlib.settings.load_settings_from_file(options, str(second))
    assert result.settings['worktree_setup'] == SETUP_SECOND
