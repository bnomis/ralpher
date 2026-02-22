import pathlib
from typing import Any

import pytest

import ralphlib.logger
import ralphlib.options


def make_options(**kwargs: Any) -> ralphlib.options.RalpherOptions:
    return ralphlib.options.RalpherOptions(**kwargs)


class TestIterationToStr:
    def test_zero_pads_based_on_max_iterations(self) -> None:
        options = make_options(iterations=100)
        assert ralphlib.logger.iteration_to_str(options, 3) == '003'

    def test_single_digit_max_no_padding(self) -> None:
        options = make_options(iterations=5)
        assert ralphlib.logger.iteration_to_str(options, 3) == '3'


class TestLogFile:
    def test_correct_path_with_logdir(self, tmp_path: pathlib.Path) -> None:
        options = make_options(logdir=str(tmp_path), iterations=10)
        result = ralphlib.logger.log_file(options, 'output.log', 3)
        assert result == tmp_path / 'output-03.log'

    def test_correct_path_without_logdir(self) -> None:
        options = make_options(logdir=None, iterations=10)
        result = ralphlib.logger.log_file(options, 'output.log', 3)
        assert result == pathlib.Path('output-03.log')

    def test_filename_with_multiple_dots(self, tmp_path: pathlib.Path) -> None:
        options = make_options(logdir=str(tmp_path), iterations=10)
        result = ralphlib.logger.log_file(options, 'output.log.txt', 3)
        assert result == tmp_path / 'output.log-03.txt'


class TestStateFile:
    def test_returns_none_when_state_not_set(self) -> None:
        options = make_options(state=None)
        assert ralphlib.logger.state_file(options) is None

    def test_prepends_logdir_when_set(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state='state.json', logdir=str(tmp_path))
        result = ralphlib.logger.state_file(options)
        assert result == tmp_path / 'state.json'

    def test_returns_plain_path_when_logdir_not_set(self) -> None:
        options = make_options(state='state.json', logdir=None)
        result = ralphlib.logger.state_file(options)
        assert result == pathlib.Path('state.json')


class TestLogDir:
    def test_raises_valueerror_when_logdir_not_set(self) -> None:
        options = make_options(logdir=None)
        with pytest.raises(ValueError, match='logdir is not set'):
            ralphlib.logger.log_dir(options)
