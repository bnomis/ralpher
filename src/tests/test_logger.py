import pathlib

import pytest

import ralphlib.exceptions
import ralphlib.logger
import ralphlib.options
import tests.helpers


@pytest.fixture(autouse=True)
def clear_log_file_cache() -> None:
    ralphlib.logger.log_file_cache.clear()


class TestIterationToStr:
    def test_zero_pads_based_on_max_iterations(self) -> None:
        options = tests.helpers.make_plain_options(iterations=100)
        assert ralphlib.logger.iteration_to_str(options, 3) == '003'

    def test_single_digit_max_no_padding(self) -> None:
        options = tests.helpers.make_plain_options(iterations=5)
        assert ralphlib.logger.iteration_to_str(options, 3) == '3'


class TestLogFile:
    def test_correct_path_with_logdir(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(logdir=str(tmp_path), iterations=10)
        result = ralphlib.logger.log_file(options, 'output.log', 3)
        assert result == tmp_path / 'output-03.log'

    def test_correct_path_without_logdir(self) -> None:
        options = tests.helpers.make_plain_options(logdir=None, iterations=10)
        result = ralphlib.logger.log_file(options, 'output.log', 3)
        assert result == pathlib.Path('output-03.log')

    def test_cache_is_per_logdir(self, tmp_path: pathlib.Path) -> None:
        first = ralphlib.logger.log_file(tests.helpers.make_plain_options(logdir=str(tmp_path / 'a'), iterations=10), 'output.log', 3)
        second = ralphlib.logger.log_file(tests.helpers.make_plain_options(logdir=str(tmp_path / 'b'), iterations=10), 'output.log', 3)
        assert first == tmp_path / 'a' / 'output-03.log'
        assert second == tmp_path / 'b' / 'output-03.log'

    def test_filename_with_multiple_dots(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(logdir=str(tmp_path), iterations=10)
        result = ralphlib.logger.log_file(options, 'output.log.txt', 3)
        assert result == tmp_path / 'output.log-03.txt'


class TestStateFile:
    def test_returns_none_when_state_not_set(self) -> None:
        options = tests.helpers.make_plain_options(state=None)
        assert ralphlib.logger.state_file(options) is None

    def test_prepends_logdir_when_set(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        result = ralphlib.logger.state_file(options)
        assert result == tmp_path / 'state.json'

    def test_returns_plain_path_when_logdir_not_set(self) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=None)
        result = ralphlib.logger.state_file(options)
        assert result == pathlib.Path('state.json')


class TestStateLockFile:
    def test_returns_none_when_state_not_set(self) -> None:
        options = tests.helpers.make_plain_options(state=None)
        assert ralphlib.logger.state_lock_file(options) is None

    def test_prepends_logdir_and_appends_lock_when_both_set(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        result = ralphlib.logger.state_lock_file(options)
        assert result == tmp_path / 'state.json.lock'

    def test_returns_plain_path_with_lock_when_logdir_not_set(self) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=None)
        result = ralphlib.logger.state_lock_file(options)
        assert result == pathlib.Path('state.json.lock')


class TestInit:
    def test_creates_log_directory_when_logdir_set(self, tmp_path: pathlib.Path) -> None:
        log_path = tmp_path / 'nested' / 'logs'
        options = tests.helpers.make_plain_options(logdir=str(log_path))
        ralphlib.logger.init(options)
        assert log_path.is_dir()

    def test_noop_when_logdir_not_set(self) -> None:
        options = tests.helpers.make_plain_options(logdir=None)
        ralphlib.logger.init(options)


class TestLogDir:
    def test_raises_log_file_error_when_logdir_not_set(self) -> None:
        options = tests.helpers.make_plain_options(logdir=None)
        with pytest.raises(ralphlib.exceptions.LogFileError, match='logdir is not set'):
            ralphlib.logger.log_dir(options)


class TestStatePathContainment:
    @pytest.mark.parametrize('state', ['/etc/state.json', '../state.json', 'a/../../state.json'])
    def test_state_file_rejects_paths_outside_logdir(self, tmp_path: pathlib.Path, state: str) -> None:
        options = tests.helpers.make_plain_options(state=state, logdir=str(tmp_path))
        with pytest.raises(ralphlib.exceptions.LogFileError):
            ralphlib.logger.state_file(options)

    @pytest.mark.parametrize('state', ['/etc/state.json', '../state.json'])
    def test_state_lock_file_rejects_paths_outside_logdir(self, tmp_path: pathlib.Path, state: str) -> None:
        options = tests.helpers.make_plain_options(state=state, logdir=str(tmp_path))
        with pytest.raises(ralphlib.exceptions.LogFileError):
            ralphlib.logger.state_lock_file(options)

    def test_nested_relative_state_is_accepted(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='sub/state.json', logdir=str(tmp_path))
        assert ralphlib.logger.state_file(options) == tmp_path / 'sub' / 'state.json'


class TestDomainErrors:
    def test_init_translates_mkdir_error(self, tmp_path: pathlib.Path) -> None:
        blocker = tmp_path / 'file'
        blocker.write_text('x')
        options = tests.helpers.make_plain_options(logdir=str(blocker / 'logs'))
        with pytest.raises(ralphlib.exceptions.LogFileError):
            ralphlib.logger.init(options)
