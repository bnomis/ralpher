import importlib.util
import pathlib
import types
import unittest.mock

import pytest

import ralphlib.exceptions
import ralphlib.looper
import ralphlib.options

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / 'bin' / 'ralpher.py'


@pytest.fixture
def ralpher() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location('ralpher_script', SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def options() -> ralphlib.options.RalpherOptions:
    return ralphlib.options.RalpherOptions(prompts='p')


class TestMain:
    def test_cleanup_prints_the_commands_and_exits_zero(self, ralpher: types.ModuleType, options: ralphlib.options.RalpherOptions) -> None:
        options.cleanup = True
        with (
            unittest.mock.patch('ralphlib.options.load_options', return_value=options),
            unittest.mock.patch('ralphlib.looper.print_cleanup_cmds') as cleanup,
            unittest.mock.patch('ralphlib.looper.loop') as loop,
            pytest.raises(SystemExit) as exit_info,
        ):
            ralpher.main()
        assert exit_info.value.code == 0
        cleanup.assert_called_once_with(options)
        loop.assert_not_called()

    def test_ralpher_error_exits_with_an_error_message(self, ralpher: types.ModuleType) -> None:
        with (
            unittest.mock.patch('ralphlib.options.load_options', side_effect=ralphlib.exceptions.SettingsError('bad settings')),
            pytest.raises(SystemExit) as exit_info,
        ):
            ralpher.main()
        assert exit_info.value.code == 'Error: bad settings'

    def test_loop_error_exits_one(self, ralpher: types.ModuleType, options: ralphlib.options.RalpherOptions) -> None:
        with (
            unittest.mock.patch('ralphlib.options.load_options', return_value=options),
            unittest.mock.patch('ralphlib.looper.loop', return_value=True),
            pytest.raises(SystemExit) as exit_info,
        ):
            ralpher.main()
        assert exit_info.value.code == 1

    def test_clean_loop_exits_zero(self, ralpher: types.ModuleType, options: ralphlib.options.RalpherOptions) -> None:
        with (
            unittest.mock.patch('ralphlib.options.load_options', return_value=options),
            unittest.mock.patch('ralphlib.looper.loop', return_value=False),
            pytest.raises(SystemExit) as exit_info,
        ):
            ralpher.main()
        assert exit_info.value.code == 0
