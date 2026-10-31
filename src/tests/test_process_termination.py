"""Integration tests for subprocess termination via GracefulTerminator.

Confirms that:
- Setting should_exit causes process() to SIGTERM the child and return
- The child subprocess actually dies (is not left orphaned)
- The GracefulTerminator double-SIGINT flow triggers subprocess termination
- The child is in a different process group (start_new_session isolation)
"""

import os
import signal
import subprocess
import sys
import threading
import time
from unittest.mock import patch

import pytest

import ralphlib.iteration
import ralphlib.options
import ralphlib.settings
import ralphlib.signals
import tests.helpers
from ralphlib.signals import GracefulTerminator

SLEEP_SCRIPT = 'import time; time.sleep(60)'


@pytest.fixture
def fast_poll():
    """Reduce poll interval so tests don't wait 3 seconds per cycle."""
    with patch.object(ralphlib.iteration, 'SUBPROCESS_POLL_INTERVAL', 0.05):
        yield


def make_context(cmd):
    return ralphlib.iteration.IterationContext(
        cmd=cmd,
        iteration=1,
        prompt='test',
    )


def child_is_alive(pid: int) -> bool:
    """Check if a process with the given pid exists."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


real_popen = subprocess.Popen


def capturing_popen(holder):
    """Return a Popen wrapper that stores the child PID in holder['pid']."""

    def wrapper(*args, **kwargs):
        proc = real_popen(*args, **kwargs)
        holder['pid'] = proc.pid
        return proc

    return wrapper


@pytest.mark.usefixtures('fast_poll')
class TestProcessTerminatesOnShouldExit:
    """process() should terminate the child when should_exit is set."""

    def test_process_returns_after_should_exit_set(self):
        options = tests.helpers.make_options(quiet=True)
        cmd = [sys.executable, '-c', SLEEP_SCRIPT]
        context = make_context(cmd)

        def set_exit_after_delay():
            time.sleep(0.2)
            ralphlib.signals.set_should_exit(True)

        timer = threading.Thread(target=set_exit_after_delay)
        timer.start()

        # process() blocks until the subprocess ends; it should return
        # promptly once should_exit is set
        ralphlib.iteration.process(options, context)

        timer.join()
        assert ralphlib.signals.get_should_exit() is True

    def test_child_process_is_dead_after_termination(self):
        options = tests.helpers.make_options(quiet=True)
        cmd = [sys.executable, '-c', SLEEP_SCRIPT]
        context = make_context(cmd)

        holder: dict = {}

        def set_exit_after_delay():
            time.sleep(0.2)
            ralphlib.signals.set_should_exit(True)

        timer = threading.Thread(target=set_exit_after_delay)

        with patch('ralphlib.iteration.subprocess.Popen', side_effect=capturing_popen(holder)):
            timer.start()
            ralphlib.iteration.process(options, context)

        timer.join()

        assert 'pid' in holder
        # Give the OS a moment to reap
        time.sleep(0.1)
        assert not child_is_alive(holder['pid']), f'Child process {holder["pid"]} still alive after termination'


@pytest.mark.usefixtures('fast_poll')
class TestGracefulTerminatorTerminatesSubprocess:
    """Full integration: GracefulTerminator handler -> should_exit -> child killed."""

    def test_double_sigint_terminates_subprocess(self):
        options = tests.helpers.make_options(quiet=True)
        cmd = [sys.executable, '-c', SLEEP_SCRIPT]
        context = make_context(cmd)

        with patch('ralphlib.signals.signal.signal'):
            terminator = GracefulTerminator(options)

        def send_double_sigint():
            time.sleep(0.2)
            terminator.handler(signal.SIGINT, None)
            terminator.handler(signal.SIGINT, None)

        timer = threading.Thread(target=send_double_sigint)
        timer.start()

        ralphlib.iteration.process(options, context)

        timer.join()
        assert terminator.is_shutting_down is True
        assert ralphlib.signals.get_should_exit() is True


@pytest.mark.usefixtures('fast_poll')
class TestChildSessionIsolation:
    """With start_new_session=True, the child is in a different session/process group."""

    def test_child_has_different_process_group(self):
        # The child script prints its process group ID to stdout, then sleeps.
        child_script = 'import os, sys; sys.stdout.write(str(os.getpgrp()) + "\\n"); sys.stdout.flush(); import time; time.sleep(60)'

        options = tests.helpers.make_options(quiet=True)
        cmd = [sys.executable, '-c', child_script]
        context = make_context(cmd)

        child_pgid_lines: list[str] = []

        def capturing_process_stdout(options, context, pipe):
            for line in iter(pipe.readline, ''):
                line = line.strip()
                if line:
                    child_pgid_lines.append(line)

        def set_exit_after_delay():
            time.sleep(0.3)
            ralphlib.signals.set_should_exit(True)

        timer = threading.Thread(target=set_exit_after_delay)
        timer.start()

        with patch.object(ralphlib.iteration, 'process_stdout', capturing_process_stdout):
            ralphlib.iteration.process(options, context)

        timer.join()

        assert len(child_pgid_lines) >= 1, 'Child did not report its pgid'
        child_pgid = int(child_pgid_lines[0])
        parent_pgid = os.getpgrp()

        assert child_pgid != parent_pgid, f'Child pgid ({child_pgid}) matches parent pgid ({parent_pgid}) — start_new_session is not working'
