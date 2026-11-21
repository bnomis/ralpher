import dataclasses
import datetime
import json
import pathlib
import shlex
import sys
import typing
import unittest.mock

import hypothesis
import hypothesis.strategies
import loguru
import pytest

import ralphlib.exceptions
import ralphlib.hooks
import ralphlib.iteration
import ralphlib.logger
import ralphlib.looper
import ralphlib.options
import ralphlib.settings
import ralphlib.signals
import ralphlib.types
import tests.helpers


class TestTimedeltaToReadableExplicit:
    def test_zero_timedelta_returns_zero(self) -> None:
        assert ralphlib.looper.timedelta_to_readable(datetime.timedelta(0)) == '0'

    def test_sub_second_timedelta_returns_zero(self) -> None:
        assert ralphlib.looper.timedelta_to_readable(datetime.timedelta(milliseconds=500)) == '0'
        assert ralphlib.looper.timedelta_to_readable(datetime.timedelta(microseconds=1)) == '0'

    def test_seconds_singular(self) -> None:
        assert ralphlib.looper.timedelta_to_readable(datetime.timedelta(seconds=1)) == '1 second'

    def test_seconds_plural(self) -> None:
        assert ralphlib.looper.timedelta_to_readable(datetime.timedelta(seconds=45)) == '45 seconds'

    def test_minutes_and_seconds(self) -> None:
        result = ralphlib.looper.timedelta_to_readable(datetime.timedelta(minutes=2, seconds=30))
        assert result == '2 minutes 30 seconds'

    def test_hours_minutes_seconds(self) -> None:
        result = ralphlib.looper.timedelta_to_readable(datetime.timedelta(hours=1, minutes=5, seconds=10))
        assert result == '1 hour 5 minutes 10 seconds'

    def test_days_hours_minutes_seconds_with_zero_intermediate(self) -> None:
        result = ralphlib.looper.timedelta_to_readable(datetime.timedelta(days=2, hours=3, minutes=0, seconds=5))
        assert result == '2 days 3 hours 0 minutes 5 seconds'

    def test_negative_timedelta(self) -> None:
        result = ralphlib.looper.timedelta_to_readable(datetime.timedelta(seconds=-90))
        assert result.startswith('-')
        assert '1 minute' in result
        assert '30 seconds' in result

    def test_show_seconds_false_suppresses_seconds(self) -> None:
        result = ralphlib.looper.timedelta_to_readable(datetime.timedelta(minutes=5, seconds=30), show_seconds=False)
        assert 'second' not in result
        assert '5 minutes' in result

    def test_show_seconds_false_still_shows_seconds_as_only_unit(self) -> None:
        result = ralphlib.looper.timedelta_to_readable(datetime.timedelta(seconds=45), show_seconds=False)
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
        assert ralphlib.looper.timedelta_to_readable(td) == expected


class TestTimedeltaToReadableHypothesis:
    @hypothesis.given(td=hypothesis.strategies.timedeltas(min_value=datetime.timedelta(seconds=1), max_value=datetime.timedelta(days=365)))
    def test_positive_timedelta_never_empty(self, td: datetime.timedelta) -> None:
        result = ralphlib.looper.timedelta_to_readable(td)
        assert len(result) > 0
        assert not result.startswith('-')

    @hypothesis.given(td=hypothesis.strategies.timedeltas(min_value=datetime.timedelta(days=-365), max_value=datetime.timedelta(seconds=-1)))
    def test_negative_timedelta_has_leading_minus(self, td: datetime.timedelta) -> None:
        result = ralphlib.looper.timedelta_to_readable(td)
        assert result.startswith('-')

    @hypothesis.given(td=hypothesis.strategies.timedeltas(min_value=datetime.timedelta(seconds=1), max_value=datetime.timedelta(days=365)))
    def test_show_seconds_false_no_seconds_when_other_units(self, td: datetime.timedelta) -> None:
        total = int(td.total_seconds())
        result = ralphlib.looper.timedelta_to_readable(td, show_seconds=False)
        if total >= 60:
            assert 'second' not in result
        else:
            assert 'second' in result


TASKS_UNFINISHED = '## Task 1: A\n**Status:** done\n## Task 2: Second thing\n**Status:** todo\n## Task 3: Third\n'
TASKS_DONE = '## Task 1: A\n**Status:** done\n'


@dataclasses.dataclass
class LoopRun:
    calls: list[int]
    out: str
    state: dict[str, typing.Any]
    result: bool = False
    events: list[str] = dataclasses.field(default_factory=list)


def run_loop(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tasks_text: str,
    iterations: int = 3,
    no_verify_stop: bool = False,
    remove_tasks_file: bool = False,
    raises: bool = False,
    vars: list[str] | None = None,
) -> LoopRun:
    """Run the loop with every iteration reporting a stop marker."""
    task_file = tmp_path / 'tasks.md'
    task_file.write_text(tasks_text)
    calls: list[int] = []

    def fake_run(options: ralphlib.options.RalpherOptions, prompt: str, iteration: int) -> tuple[bool, bool]:
        calls.append(iteration)
        if raises:
            raise RuntimeError('boom')
        if remove_tasks_file:
            task_file.unlink()
        return True, False

    events: list[str] = []

    def fake_event(options: ralphlib.options.RalpherOptions, event_type: typing.Any, event_context: dict[str, typing.Any] | None = None) -> None:
        events.append(event_type.name.lower())

    monkeypatch.setattr(ralphlib.iteration, 'run', fake_run)
    monkeypatch.setattr(ralphlib.hooks, 'event', fake_event)
    options = ralphlib.options.RalpherOptions(
        prompts='p',
        task_file=str(task_file),
        iterations=iterations,
        skip_git_check=True,
        no_verify_stop=no_verify_stop,
        state='state.json',
        logdir=str(tmp_path / 'logs'),
        cwd=str(tmp_path),
        vars=list(vars or []),
    )
    options.settings = ralphlib.settings.default_settings()
    result = ralphlib.looper.loop(options)
    state_path = tmp_path / 'logs' / 'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    return LoopRun(calls, capsys.readouterr().out, state, result, events)


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


def test_loop_exception_in_iteration_is_an_error(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    result = run_loop(tmp_path, monkeypatch, capsys, TASKS_DONE, raises=True)
    assert result.result is True
    assert result.calls == [1]
    assert result.state['exit_reason'] == 'exception during iteration 1'
    assert 'Exit reason: exception during iteration 1' in result.out
    assert 'error' in result.events
    assert 'iteration_end' not in result.events


@pytest.mark.parametrize('bad_var', ['noequals', 'iteration=3'], ids=['no_equals', 'reserved_key'])
def test_loop_rejects_bad_vars_before_starting(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], bad_var: str
) -> None:
    result = run_loop(tmp_path, monkeypatch, capsys, TASKS_DONE, vars=[bad_var])
    assert result.result is True
    assert result.calls == []
    assert result.events == []
    assert result.state == {}
    assert 'Error: Invalid var' in result.out


def test_loop_accepts_good_vars(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    result = run_loop(tmp_path, monkeypatch, capsys, TASKS_DONE, vars=['name=World'])
    assert result.result is False
    assert result.calls == [1]
    assert result.events[0] == 'start'


TASK_FILE = 'agents/tasks/auditme-adoption/tasks-1.md'
BRANCH = 'worktree-auditme-adoption-tasks-1'


class TestCleanupCmds:
    def test_no_commands_without_worktree(self) -> None:
        options = ralphlib.options.RalpherOptions(task_file=TASK_FILE, worktree=False)
        assert ralphlib.looper.cleanup_cmds(options) == []

    def test_no_commands_without_task_file(self) -> None:
        options = ralphlib.options.RalpherOptions(worktree=True)
        assert ralphlib.looper.cleanup_cmds(options) == []

    def test_force_deletes_the_merged_branch(self) -> None:
        # A branch pushed with an upstream that is behind it fails `git branch -d`
        # even though it is merged to HEAD, and stops the chain before `git push`.
        options = ralphlib.options.RalpherOptions(task_file=TASK_FILE, worktree=True)
        cmds = ralphlib.looper.cleanup_cmds(options)
        assert f'git branch -D {BRANCH}' in cmds
        assert f'git branch -d {BRANCH}' not in cmds

    def test_commands_in_order(self) -> None:
        options = ralphlib.options.RalpherOptions(task_file=TASK_FILE, worktree=True)
        assert ralphlib.looper.cleanup_cmds(options) == [
            f'git merge --no-ff --no-edit {BRANCH}',
            '(git worktree unlock auditme-adoption-tasks-1 2>/dev/null || true)',
            'git worktree remove --force auditme-adoption-tasks-1',
            f'git branch -D {BRANCH}',
            'git push',
            f'(git push origin --delete {BRANCH} 2>/dev/null || true)',
        ]


class TestDomainErrors:
    def test_chdir_failure_raises_ralpher_error(self, tmp_path: pathlib.Path) -> None:
        options = ralphlib.options.RalpherOptions(prompts='p', cwd=str(tmp_path / 'missing'), skip_git_check=True)
        with pytest.raises(ralphlib.exceptions.RalpherError, match='change directory'):
            ralphlib.looper.loop(options)

    def test_unreadable_prompt_raises_ralpher_error(self, tmp_path: pathlib.Path) -> None:
        prompt = tmp_path / 'prompt.md'
        prompt.write_bytes(b'\xff\xfe\x00')
        options = ralphlib.options.RalpherOptions(prompt=str(prompt), cwd=str(tmp_path), skip_git_check=True)
        with pytest.raises(ralphlib.exceptions.RalpherError, match='prompt file'):
            ralphlib.looper.loop(options)

    def test_unreadable_tasks_file_raises_tasks_file_error(self, tmp_path: pathlib.Path) -> None:
        tasks = tmp_path / 'tasks.md'
        tasks.write_bytes(b'\xff\xfe\x00')
        options = ralphlib.options.RalpherOptions(prompts='p', task_file=str(tasks), cwd=str(tmp_path), skip_git_check=True)
        with pytest.raises(ralphlib.exceptions.TasksFileError):
            ralphlib.looper.loop(options)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    parent=hypothesis.strategies.from_regex(r'[a-z][a-z0-9]{0,8}', fullmatch=True),
    stem=hypothesis.strategies.from_regex(r'[a-z][a-z0-9]{0,8}', fullmatch=True),
    worktree=hypothesis.strategies.booleans(),
)
def test_cleanup_cmds_name_the_branch_only_with_a_worktree(parent: str, stem: str, worktree: bool) -> None:
    options = ralphlib.options.RalpherOptions(task_file=f'x/{parent}/{stem}.md', worktree=worktree)
    cmds = ralphlib.looper.cleanup_cmds(options)
    if worktree:
        assert f'git branch -D worktree-{parent}-{stem}' in cmds
    else:
        assert cmds == []


def test_cleanup_names_the_worktree_the_run_uses_for_a_one_part_task_file(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    options = ralphlib.options.resolve_paths(ralphlib.options.RalpherOptions(task_file='TASKS.md', worktree=True))
    name = ralphlib.iteration.add_worktree_arg(options, [])[-1]
    assert name.endswith('-tasks')
    assert f'git worktree remove --force {name}' in ralphlib.looper.cleanup_cmds(options)


FAKE_AGENT = pathlib.Path(__file__).parent / 'fixtures' / 'fake_agent.py'

AGENT_EVENTS = (
    ralphlib.types.RalpherEventType.AGENT_PROCESS_END,
    ralphlib.types.RalpherEventType.AGENT_PROCESS_START,
)


class TestLoopEndToEnd:
    """`loop` with the fake agent and a real `iteration.run`; only the hook dispatch is recorded."""

    def run_loop(self, tmp_path: pathlib.Path, prompt: str, iterations: int) -> tuple[bool, list[ralphlib.types.RalpherEventType], dict[str, typing.Any]]:
        ralphlib.logger.log_file_cache.clear()
        options = ralphlib.options.RalpherOptions(
            agent=sys.executable,
            args=shlex.quote(str(FAKE_AGENT)),
            prompts=prompt,
            iterations=iterations,
            cwd=str(tmp_path),
            logdir=str(tmp_path),
            state='state.json',
            quiet=True,
            skip_git_check=True,
        )
        options = ralphlib.settings.load_settings(options)
        with unittest.mock.patch('ralphlib.hooks.event') as event:
            error = ralphlib.looper.loop(options)
        ralphlib.logger.log_file_cache.clear()
        types = [call.kwargs['event_type'] if 'event_type' in call.kwargs else call.args[1] for call in event.call_args_list]
        types = [t for t in types if t not in AGENT_EVENTS]
        state = json.loads((tmp_path / 'state.json').read_text(encoding='utf-8'))
        return error, types, state

    def test_stop_marker_ends_the_loop_after_one_iteration(self, tmp_path: pathlib.Path) -> None:
        error, types, state = self.run_loop(tmp_path, 'stop', iterations=3)
        assert error is False
        assert types == [
            ralphlib.types.RalpherEventType.START,
            ralphlib.types.RalpherEventType.ITERATION_START,
            ralphlib.types.RalpherEventType.ITERATION_END,
            ralphlib.types.RalpherEventType.END,
        ]
        assert state['exit_reason'] == 'complete'
        assert state['iterations_completed'] == 1

    def test_normal_session_runs_every_iteration(self, tmp_path: pathlib.Path) -> None:
        error, types, state = self.run_loop(tmp_path, 'normal', iterations=2)
        assert error is False
        assert types.count(ralphlib.types.RalpherEventType.ITERATION_END) == 2
        assert state['exit_reason'] == 'completed all iterations'
        assert state['iterations_completed'] == 2

    def test_error_result_fires_the_error_hook_and_returns_true(self, tmp_path: pathlib.Path) -> None:
        error, types, state = self.run_loop(tmp_path, 'error', iterations=3)
        assert error is True
        assert types[-2:] == [ralphlib.types.RalpherEventType.ERROR, ralphlib.types.RalpherEventType.END]
        assert state['exit_reason'] == 'error'
        assert state['iterations_completed'] == 1


def make_stop_options(tmp_path: pathlib.Path, tasks_text: str | None) -> ralphlib.options.RalpherOptions:
    task_file = tmp_path / 'tasks.md'
    if tasks_text is not None:
        task_file.write_text(tasks_text)
    options = ralphlib.options.RalpherOptions(
        prompts='p',
        task_file=str(task_file),
        skip_git_check=True,
        state='state.json',
        logdir=str(tmp_path / 'logs'),
        cwd=str(tmp_path),
    )
    options.settings = ralphlib.settings.default_settings()
    return options


class TestRejectUnverifiedStop:
    def test_all_done_allows_the_stop(self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
        options = make_stop_options(tmp_path, TASKS_DONE)
        assert ralphlib.looper.reject_unverified_stop(options, 1, '1') is True
        assert 'rejected' not in capsys.readouterr().out

    def test_missing_task_file_trusts_the_stop(self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
        options = make_stop_options(tmp_path, None)
        assert ralphlib.looper.reject_unverified_stop(options, 1, '1') is True
        assert 'rejected' not in capsys.readouterr().out

    def test_unfinished_tasks_reject_the_stop_and_record_it(self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
        options = make_stop_options(tmp_path, TASKS_UNFINISHED)
        (tmp_path / 'logs').mkdir()
        (tmp_path / 'logs' / 'state.json').write_text('{}')
        assert ralphlib.looper.reject_unverified_stop(options, 2, '2') is False
        out = capsys.readouterr().out
        assert 'Loop complete signal rejected, 2 of 3 tasks not done' in out
        assert '  Task 2: Second thing (todo)' in out
        assert '  Task 3: Third (no status)' in out
        state = json.loads((tmp_path / 'logs' / 'state.json').read_text())
        assert state['iterations']['2']['stop_rejected'] == {'total': 3, 'not_done': [2, 3]}


class TestPrintCleanupCmds:
    def test_worktree_run_prints_the_cleanup_chain(self, capsys: pytest.CaptureFixture[str]) -> None:
        options = ralphlib.options.RalpherOptions(prompts='p', worktree=True, task_file='agents/tasks/tasks-1.md', cwd='/src/probe')
        options.settings = ralphlib.settings.default_settings()
        ralphlib.looper.print_cleanup_cmds(options)
        out = capsys.readouterr().out
        assert 'Probable cleanup commands...' in out
        for cmd in ralphlib.looper.cleanup_cmds(options):
            assert cmd in out
        assert 'cd /src/probe' in out
        assert 'git push' in out

    def test_no_worktree_prints_nothing(self, capsys: pytest.CaptureFixture[str]) -> None:
        options = ralphlib.options.RalpherOptions(prompts='p', task_file='tasks.md')
        options.settings = ralphlib.settings.default_settings()
        ralphlib.looper.print_cleanup_cmds(options)
        assert capsys.readouterr().out == ''


class TestPrintStoppingPrompt:
    def test_prints_the_stored_prompt(self, capsys: pytest.CaptureFixture[str]) -> None:
        options = ralphlib.options.RalpherOptions(prompts='p')
        options.settings = ralphlib.settings.default_settings()
        ralphlib.signals.set_should_exit(True, reason='stop', prompt='do the next thing')
        ralphlib.looper.print_stopping_prompt(options)
        out = capsys.readouterr().out
        assert 'Probable next prompt...' in out
        assert 'do the next thing' in out

    def test_no_prompt_prints_nothing(self, capsys: pytest.CaptureFixture[str]) -> None:
        options = ralphlib.options.RalpherOptions(prompts='p')
        options.settings = ralphlib.settings.default_settings()
        ralphlib.looper.print_stopping_prompt(options)
        assert capsys.readouterr().out == ''


WORKTREE_SETUP_WARNING = "Warning: no worktree_setup setting; the agent's worktree has no project environment."


class TestWarnMissingWorktreeSetup:
    @pytest.mark.parametrize('settings', [{}, {'worktree_setup': []}])
    def test_warns_with_worktree_and_no_commands(self, capsys: pytest.CaptureFixture[str], settings: dict[str, typing.Any]) -> None:
        options = tests.helpers.make_options_with_settings(worktree=True, settings=settings)
        ralphlib.looper.warn_missing_worktree_setup(options)
        assert WORKTREE_SETUP_WARNING in capsys.readouterr().err

    def test_silent_with_the_setting(self, capsys: pytest.CaptureFixture[str]) -> None:
        options = tests.helpers.make_options_with_settings(worktree=True, settings={'worktree_setup': ['make setup']})
        ralphlib.looper.warn_missing_worktree_setup(options)
        assert capsys.readouterr().err == ''

    def test_silent_without_worktree(self, capsys: pytest.CaptureFixture[str]) -> None:
        options = tests.helpers.make_options_with_settings(worktree=False, settings={})
        ralphlib.looper.warn_missing_worktree_setup(options)
        assert capsys.readouterr().err == ''
