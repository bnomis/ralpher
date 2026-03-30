import datetime
import signal
from unittest.mock import patch

import pytest

import ralphlib.options
import ralphlib.settings
from ralphlib import signals
from ralphlib.signals import GracefulTerminator


def make_options(**kwargs) -> ralphlib.options.RalpherOptions:
    options = ralphlib.options.RalpherOptions(**kwargs)
    return ralphlib.settings.load_settings(options)


@pytest.fixture(autouse=True)
def reset_should_exit() -> None:
    signals.set_should_exit(False)


@pytest.fixture
def terminator() -> GracefulTerminator:
    with patch('ralphlib.signals.signal.signal'):
        return GracefulTerminator(make_options())


class TestGracefulTerminatorFirstSigint:
    def test_first_sigint_sets_first_press(self, terminator: GracefulTerminator) -> None:
        assert terminator.first_press is None
        terminator.handler(signal.SIGINT, None)
        assert terminator.first_press is not None

    def test_first_sigint_does_not_shut_down(self, terminator: GracefulTerminator) -> None:
        terminator.handler(signal.SIGINT, None)
        assert terminator.is_shutting_down is False
        assert signals.get_should_exit() is False


class TestGracefulTerminatorSecondSigint:
    def test_second_sigint_within_interval_triggers_shutdown(self, terminator: GracefulTerminator) -> None:
        terminator.handler(signal.SIGINT, None)
        terminator.handler(signal.SIGINT, None)
        assert terminator.is_shutting_down is True
        assert signals.get_should_exit() is True

    def test_second_sigint_within_interval_sets_should_exit(self, terminator: GracefulTerminator) -> None:
        terminator.handler(signal.SIGINT, None)
        terminator.handler(signal.SIGINT, None)
        assert signals.get_should_exit() is True

    def test_second_sigint_after_interval_resets(self, terminator: GracefulTerminator) -> None:
        terminator.handler(signal.SIGINT, None)
        terminator.first_press = datetime.datetime.now() - datetime.timedelta(seconds=GracefulTerminator.CTRL_C_PRESS_INTERVAL + 1)
        terminator.handler(signal.SIGINT, None)
        assert terminator.is_shutting_down is False
        assert terminator.first_press is not None


class TestGracefulTerminatorSigterm:
    def test_sigterm_immediately_triggers_shutdown(self, terminator: GracefulTerminator) -> None:
        terminator.handler(signal.SIGTERM, None)
        assert terminator.is_shutting_down is True
        assert signals.get_should_exit() is True


class TestGracefulTerminatorAlreadyShuttingDown:
    def test_handler_when_shutting_down_calls_sys_exit(self, terminator: GracefulTerminator) -> None:
        terminator.is_shutting_down = True
        with pytest.raises(SystemExit, match='1'):
            terminator.handler(signal.SIGINT, None)


class TestShouldExitRoundTrip:
    def test_set_and_get_should_exit(self) -> None:
        signals.set_should_exit(False)
        assert signals.get_should_exit() is False
        signals.set_should_exit(True)
        assert signals.get_should_exit() is True
        signals.set_should_exit(False)
        assert signals.get_should_exit() is False
