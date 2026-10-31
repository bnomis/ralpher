import datetime
import json
import pathlib

import loguru
import pytest
from hypothesis import given, strategies as st

import ralphlib.iteration
import ralphlib.looper
import ralphlib.settings
from ralphlib.looper import timedelta_to_readable
from ralphlib.options import RalpherOptions


class TestTimedeltaToReadableExplicit:
    def test_zero_timedelta_returns_zero(self) -> None:
        assert timedelta_to_readable(datetime.timedelta(0)) == '0'

    def test_sub_second_timedelta_returns_zero(self) -> None:
        assert timedelta_to_readable(datetime.timedelta(milliseconds=500)) == '0'
        assert timedelta_to_readable(datetime.timedelta(microseconds=1)) == '0'

    def test_seconds_singular(self) -> None:
        assert timedelta_to_readable(datetime.timedelta(seconds=1)) == '1 second'

    def test_seconds_plural(self) -> None:
        assert timedelta_to_readable(datetime.timedelta(seconds=45)) == '45 seconds'

    def test_minutes_and_seconds(self) -> None:
        result = timedelta_to_readable(datetime.timedelta(minutes=2, seconds=30))
        assert result == '2 minutes 30 seconds'

    def test_hours_minutes_seconds(self) -> None:
        result = timedelta_to_readable(datetime.timedelta(hours=1, minutes=5, seconds=10))
        assert result == '1 hour 5 minutes 10 seconds'

    def test_days_hours_minutes_seconds_with_zero_intermediate(self) -> None:
        result = timedelta_to_readable(datetime.timedelta(days=2, hours=3, minutes=0, seconds=5))
        assert result == '2 days 3 hours 0 minutes 5 seconds'

    def test_negative_timedelta(self) -> None:
        result = timedelta_to_readable(datetime.timedelta(seconds=-90))
        assert result.startswith('-')
        assert '1 minute' in result
        assert '30 seconds' in result

    def test_show_seconds_false_suppresses_seconds(self) -> None:
        result = timedelta_to_readable(datetime.timedelta(minutes=5, seconds=30), show_seconds=False)
        assert 'second' not in result
        assert '5 minutes' in result

    def test_show_seconds_false_still_shows_seconds_as_only_unit(self) -> None:
        result = timedelta_to_readable(datetime.timedelta(seconds=45), show_seconds=False)
        assert result == '45 seconds'

    @pytest.mark.parametrize(
        'td, expected',
        [
            (datetime.timedelta(days=1), '1 day 0 hours 0 minutes 0 seconds'),
            (datetime.timedelta(hours=1), '1 hour 0 minutes 0 seconds'),
            (datetime.timedelta(minutes=1), '1 minute 0 seconds'),
            (datetime.timedelta(seconds=1), '1 second'),
        ],
        ids=['1_day', '1_hour', '1_minute', '1_second'],
    )
    def test_exact_one_unit_boundaries(self, td: datetime.timedelta, expected: str) -> None:
        assert timedelta_to_readable(td) == expected


class TestTimedeltaToReadableHypothesis:
    @given(td=st.timedeltas(min_value=datetime.timedelta(seconds=1), max_value=datetime.timedelta(days=365)))
    def test_positive_timedelta_never_empty(self, td: datetime.timedelta) -> None:
        result = timedelta_to_readable(td)
        assert len(result) > 0
        assert not result.startswith('-')

    @given(td=st.timedeltas(min_value=datetime.timedelta(days=-365), max_value=datetime.timedelta(seconds=-1)))
    def test_negative_timedelta_has_leading_minus(self, td: datetime.timedelta) -> None:
        result = timedelta_to_readable(td)
        assert result.startswith('-')

    @given(td=st.timedeltas(min_value=datetime.timedelta(seconds=1), max_value=datetime.timedelta(days=365)))
    def test_show_seconds_false_no_seconds_when_other_units(self, td: datetime.timedelta) -> None:
        total = int(td.total_seconds())
        result = timedelta_to_readable(td, show_seconds=False)
        if total >= 60:
            assert 'second' not in result
        else:
            assert 'second' in result


TASKS_UNFINISHED = '## Task 1: A\n**Status:** done\n## Task 2: Second thing\n**Status:** todo\n## Task 3: Third\n'
TASKS_DONE = '## Task 1: A\n**Status:** done\n'


class LoopRun:
    def __init__(self, calls: list[int], out: str, state: dict) -> None:
        self.calls = list(calls)
        self.out = out
        self.state = dict(state)


def run_loop(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tasks_text: str,
    iterations: int = 3,
    no_verify_stop: bool = False,
    remove_tasks_file: bool = False,
) -> LoopRun:
    """Run the loop with every iteration reporting a stop marker."""
    task_file = tmp_path / 'tasks.md'
    task_file.write_text(tasks_text)
    calls: list[int] = []

    def fake_run(options: RalpherOptions, prompt: str, iteration: int) -> tuple[bool, bool]:
        calls.append(iteration)
        if remove_tasks_file:
            task_file.unlink()
        return True, False

    monkeypatch.setattr(ralphlib.iteration, 'run', fake_run)
    options = RalpherOptions(
        prompts='p',
        task_file=str(task_file),
        iterations=iterations,
        skip_git_check=True,
        no_verify_stop=no_verify_stop,
        state='state.json',
        logdir=str(tmp_path / 'logs'),
        cwd=str(tmp_path),
    )
    options.settings = ralphlib.settings.default_settings()
    ralphlib.looper.loop(options)
    state = json.loads((tmp_path / 'logs' / 'state.json').read_text())
    return LoopRun(calls, capsys.readouterr().out, state)


def test_loop_rejects_stop_while_tasks_unfinished(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    result = run_loop(tmp_path, monkeypatch, capsys, TASKS_UNFINISHED, iterations=2)
    assert result.calls == [1, 2]
    assert 'Loop complete signal rejected, 2 of 3 tasks not done' in result.out
    assert '  Task 2: Second thing (todo)' in result.out
    assert '  Task 3: Third (no status)' in result.out
    assert result.state['iterations']['1']['stop_rejected'] == {'total': 3, 'not_done': [2, 3]}


def test_loop_rejected_stop_on_last_iteration_completes_all_iterations(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    result = run_loop(tmp_path, monkeypatch, capsys, TASKS_UNFINISHED, iterations=1)
    assert result.calls == [1]
    assert result.state['exit_reason'] == 'completed all iterations'
    assert 'signal received' not in result.out


def test_loop_stops_when_all_tasks_done(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    result = run_loop(tmp_path, monkeypatch, capsys, TASKS_DONE)
    assert result.calls == [1]
    assert result.state['exit_reason'] == 'complete'
    assert 'rejected' not in result.out


def test_loop_no_verify_stop_trusts_the_marker(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    result = run_loop(tmp_path, monkeypatch, capsys, TASKS_UNFINISHED, no_verify_stop=True)
    assert result.calls == [1]
    assert 'rejected' not in result.out


def test_loop_stops_and_warns_when_tasks_file_unreadable(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    messages: list[str] = []
    sink = loguru.logger.add(messages.append, level='WARNING')
    try:
        result = run_loop(tmp_path, monkeypatch, capsys, TASKS_UNFINISHED, remove_tasks_file=True)
    finally:
        loguru.logger.remove(sink)
    assert result.calls == [1]
    assert any('Cannot verify stop signal' in m for m in messages)
