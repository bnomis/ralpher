import datetime
import signal
import unittest.mock

import pytest

import ralphlib.signals
import tests.helpers


@pytest.fixture
def terminator() -> ralphlib.signals.GracefulTerminator:
    with unittest.mock.patch('ralphlib.signals.signal.signal'):
        return ralphlib.signals.GracefulTerminator(tests.helpers.make_options())


class TestGracefulTerminatorFirstSigint:
    def test_first_sigint_sets_first_press(self, terminator: ralphlib.signals.GracefulTerminator) -> None:
        assert terminator.first_press is None
        terminator.handler(signal.SIGINT, None)
        assert terminator.first_press is not None

    def test_first_sigint_does_not_shut_down(self, terminator: ralphlib.signals.GracefulTerminator) -> None:
        terminator.handler(signal.SIGINT, None)
        assert terminator.is_shutting_down is False
        assert ralphlib.signals.get_should_exit() is False


class TestGracefulTerminatorSecondSigint:
    def test_second_sigint_within_interval_triggers_shutdown(self, terminator: ralphlib.signals.GracefulTerminator) -> None:
        terminator.handler(signal.SIGINT, None)
        terminator.handler(signal.SIGINT, None)
        assert terminator.is_shutting_down is True
        assert ralphlib.signals.get_should_exit() is True

    def test_second_sigint_within_interval_sets_should_exit(self, terminator: ralphlib.signals.GracefulTerminator) -> None:
        terminator.handler(signal.SIGINT, None)
        terminator.handler(signal.SIGINT, None)
        assert ralphlib.signals.get_should_exit() is True

    def test_second_sigint_after_interval_resets(self, terminator: ralphlib.signals.GracefulTerminator) -> None:
        terminator.handler(signal.SIGINT, None)
        terminator.first_press = datetime.datetime.now() - datetime.timedelta(seconds=ralphlib.signals.GracefulTerminator.CTRL_C_PRESS_INTERVAL + 1)
        terminator.handler(signal.SIGINT, None)
        assert terminator.is_shutting_down is False
        assert terminator.first_press is not None


class TestGracefulTerminatorSigterm:
    def test_sigterm_immediately_triggers_shutdown(self, terminator: ralphlib.signals.GracefulTerminator) -> None:
        terminator.handler(signal.SIGTERM, None)
        assert terminator.is_shutting_down is True
        assert ralphlib.signals.get_should_exit() is True


class TestGracefulTerminatorAlreadyShuttingDown:
    def test_handler_when_shutting_down_calls_sys_exit(self, terminator: ralphlib.signals.GracefulTerminator) -> None:
        terminator.is_shutting_down = True
        with pytest.raises(SystemExit, match='1'):
            terminator.handler(signal.SIGINT, None)


class TestShouldExitRoundTrip:
    def test_set_and_get_should_exit(self) -> None:
        ralphlib.signals.set_should_exit(False)
        assert ralphlib.signals.get_should_exit() is False
        ralphlib.signals.set_should_exit(True)
        assert ralphlib.signals.get_should_exit() is True
        ralphlib.signals.set_should_exit(False)
        assert ralphlib.signals.get_should_exit() is False
