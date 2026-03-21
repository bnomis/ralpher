import json
from typing import Any
from unittest.mock import patch

import ralphlib.options
import ralphlib.settings


def make_options(**kwargs: Any) -> ralphlib.options.RalpherOptions:
    settings = kwargs.pop('settings', {})
    options = ralphlib.options.RalpherOptions(**kwargs)
    options.settings = settings
    return options


class TestLoadSettingsFromFile:
    def test_nonexistent_file_is_noop(self, tmp_path: Any) -> None:
        options = make_options(settings={'existing': 'value'})
        result = ralphlib.settings.load_settings_from_file(options, str(tmp_path / 'missing.json'))
        assert result.settings == {'existing': 'value'}

    def test_valid_json_file_merges_into_settings(self, tmp_path: Any) -> None:
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'hooks': {'start': ['echo hi']}}))
        options = make_options(settings={'existing': 'value'})
        result = ralphlib.settings.load_settings_from_file(options, str(settings_file))
        assert result.settings == {'existing': 'value', 'hooks': {'start': ['echo hi']}}

    def test_overwrites_existing_keys_on_conflict(self, tmp_path: Any) -> None:
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'key': 'new'}))
        options = make_options(settings={'key': 'old'})
        result = ralphlib.settings.load_settings_from_file(options, str(settings_file))
        assert result.settings['key'] == 'new'


class TestLoadSettings:
    def test_applies_default_then_home_then_custom_in_order(self, tmp_path: Any) -> None:
        custom_file = tmp_path / 'custom_settings.json'
        custom_file.write_text(json.dumps({'source': 'custom', 'custom_only': True}))
        options = make_options(settings_file=str(custom_file))
        call_paths: list[str] = []

        def tracking_load(opts: ralphlib.options.RalpherOptions, paths: str) -> ralphlib.options.RalpherOptions:
            call_paths.append(paths)
            if paths == '~/.ralpher/settings.json':
                opts.settings.update({'source': 'home', 'home_only': True})
            else:
                opts.settings.update({'source': 'custom', 'custom_only': True})
            return opts

        with (
            patch.object(
                ralphlib.settings,
                'default_settings',
                {'source': 'default', 'default_only': True},
            ),
            patch.object(
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
        options = make_options()
        with patch.object(
            ralphlib.settings,
            'load_settings_from_file',
            wraps=ralphlib.settings.load_settings_from_file,
        ) as mock_load:
            mock_load.return_value = options
            ralphlib.settings.load_settings(options)
        mock_load.assert_called_once_with(options, '~/.ralpher/settings.json')

    def test_settings_file_overrides_home_config_values(self, tmp_path: Any) -> None:
        home_file = tmp_path / '.ralpher' / 'settings.json'
        home_file.parent.mkdir()
        home_file.write_text(json.dumps({'key': 'home', 'home_only': True}))

        custom_file = tmp_path / 'custom.json'
        custom_file.write_text(json.dumps({'key': 'custom', 'custom_only': True}))

        options = make_options(settings_file=str(custom_file))

        home_path = str(home_file)
        original_load = ralphlib.settings.load_settings_from_file

        def patched_load(opts: ralphlib.options.RalpherOptions, paths: str) -> ralphlib.options.RalpherOptions:
            if paths == '~/.ralpher/settings.json':
                return original_load(opts, home_path)
            return original_load(opts, paths)

        with patch.object(ralphlib.settings, 'load_settings_from_file', side_effect=patched_load):
            result = ralphlib.settings.load_settings(options)

        assert result.settings['key'] == 'custom'
        assert result.settings['home_only'] is True
        assert result.settings['custom_only'] is True
