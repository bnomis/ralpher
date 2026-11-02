import json
import typing
import unittest.mock

import pytest

import ralphlib.exceptions
import ralphlib.options
import ralphlib.settings
import tests.helpers

ECHO_HI = ('echo hi',)
NOTIFY = ('notify',)


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
