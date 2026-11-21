import pathlib

import git
import pytest

import ralphlib.exceptions
import ralphlib.order

SETTINGS = """| Setting | Value |
|---|---|
| checkpoint command | `make test-slow` |
| test pass line | `all passed` |
"""

ORDER_HEADER = """| # | Task list | Waits for | Stops for you | Status |
|---|---|---|---|---|
"""

LISTS = ('cache/tasks-1.md', 'lexicon/tasks-1.md', 'parser/tasks-1.md', 'report/tasks-2.md')


@pytest.fixture
def project(tmp_path: pathlib.Path) -> pathlib.Path:
    for name in LISTS:
        target = tmp_path / 'agents' / 'tasks' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('# Tasks\n')
    return tmp_path


def write_order(project: pathlib.Path, text: str) -> pathlib.Path:
    path = project / 'agents' / 'tasks' / 'order-x.md'
    path.write_text(text)
    return path


def test_explicit_checkpoints_and_defaults(project: pathlib.Path) -> None:
    path = write_order(
        project,
        '# Order: x\n\n'
        + SETTINGS
        + '\nfree text between\n\n'
        + ORDER_HEADER
        + '| 1 | `parser/tasks-1.md` | - | - | todo |\n'
        + '| 2 | `lexicon/tasks-1.md` | 1 | the verdicts (Task 3) | merged abc1234 |\n'
        + '| | **Checkpoint** | | | todo |\n'
        + '| 3 | `report/tasks-2.md` | 1, 2 | - | todo |\n'
        + '| | **Final checkpoint** | | | todo |\n'
        + '\ntrailing text\n',
    )
    order = ralphlib.order.read_order(path)
    settings = order.settings
    assert settings.checkpoint_command == 'make test-slow'
    assert settings.checkpoint_every == 3
    assert settings.test_log == 'ralpher-logs/{spec}/tasks-{index}/final-tests.log'
    assert settings.pass_line == 'all passed'  # noqa: S105 a log line, not a password
    assert settings.fail_pattern == 'FAILED'
    assert settings.wait_rules == ()
    assert settings.progress_page is None
    assert order.rows == (
        ralphlib.order.ListRow('1', 'parser/tasks-1.md', (), '-', 'todo'),
        ralphlib.order.ListRow('2', 'lexicon/tasks-1.md', ('1',), 'the verdicts (Task 3)', 'merged abc1234'),
        ralphlib.order.CheckpointRow(label='checkpoint:1', final=False, status='todo'),
        ralphlib.order.ListRow('3', 'report/tasks-2.md', ('1', '2'), '-', 'todo'),
        ralphlib.order.CheckpointRow(label='checkpoint:2', final=True, status='todo'),
    )
    row = order.rows[3]
    assert isinstance(row, ralphlib.order.ListRow)
    assert (row.spec, row.index) == ('report', '2')


def test_no_checkpoint_rows_and_a_suffixed_label(project: pathlib.Path) -> None:
    path = write_order(
        project,
        SETTINGS + ORDER_HEADER + '| 3a | parser/tasks-1.md | - | - | todo |\n',
    )
    order = ralphlib.order.read_order(path)
    assert [row.label for row in order.rows if isinstance(row, ralphlib.order.ListRow)] == ['3a']


def test_every_setting_given(project: pathlib.Path) -> None:
    settings = (
        SETTINGS
        + '| checkpoint every | 5 |\n'
        + '| test log | `logs/{spec}-{index}.log` |\n'
        + '| test fail pattern | `ERROR\\|FAILED` |\n'
        + '| always wait for | `a.md`, `b.md` |\n'
        + '| progress page | https://example.test/p |\n'
    )
    path = write_order(project, settings + ORDER_HEADER + '| 1 | parser/tasks-1.md | - | - | todo |\n')
    result = ralphlib.order.read_order(path).settings
    assert result.checkpoint_every == 5
    assert result.fail_pattern == 'ERROR|FAILED'
    assert result.test_log == 'logs/{spec}-{index}.log'
    assert result.wait_rules == ('a.md', 'b.md')
    assert result.progress_page == 'https://example.test/p'


ROW = '| 1 | parser/tasks-1.md | - | - | todo |\n'


def error_for(project: pathlib.Path, text: str) -> str:
    path = write_order(project, text)
    with pytest.raises(ralphlib.exceptions.OrderFormatError) as info:
        ralphlib.order.read_order(path)
    return str(info.value)


def test_no_settings_table(project: pathlib.Path) -> None:
    assert 'no settings table' in error_for(project, ORDER_HEADER + ROW)


def test_missing_required_setting(project: pathlib.Path) -> None:
    text = '| Setting | Value |\n|---|---|\n| checkpoint command | `x` |\n' + ORDER_HEADER + ROW
    message = error_for(project, text)
    assert 'test pass line' in message
    assert ':1:' in message


def test_unknown_setting(project: pathlib.Path) -> None:
    message = error_for(project, SETTINGS + '| colour | red |\n' + ORDER_HEADER + ROW)
    assert 'unknown setting `colour`' in message
    assert ':5:' in message


@pytest.mark.parametrize('value', ['0', '-2', 'three', '1.5'])
def test_bad_checkpoint_every(project: pathlib.Path, value: str) -> None:
    message = error_for(project, SETTINGS + f'| checkpoint every | {value} |\n' + ORDER_HEADER + ROW)
    assert 'positive integer' in message
    assert ':5:' in message


def test_duplicate_label(project: pathlib.Path) -> None:
    message = error_for(project, SETTINGS + ORDER_HEADER + ROW + ROW)
    assert 'duplicate label `1`' in message
    assert ':8:' in message


def test_label_with_spaces(project: pathlib.Path) -> None:
    message = error_for(project, SETTINGS + ORDER_HEADER + '| a b | parser/tasks-1.md | - | - | todo |\n')
    assert 'spaces' in message
    assert ':7:' in message


def test_task_list_wrong_form(project: pathlib.Path) -> None:
    message = error_for(project, SETTINGS + ORDER_HEADER + '| 1 | parser/one.md | - | - | todo |\n')
    assert '<spec>/tasks-<index>.md' in message
    assert ':7:' in message


def test_task_list_missing(project: pathlib.Path) -> None:
    message = error_for(project, SETTINGS + ORDER_HEADER + '| 1 | nothing/tasks-1.md | - | - | todo |\n')
    assert 'does not exist' in message
    assert ':7:' in message


def test_waits_for_unknown_label(project: pathlib.Path) -> None:
    message = error_for(project, SETTINGS + ORDER_HEADER + '| 1 | parser/tasks-1.md | 9 | - | todo |\n')
    assert '`9`' in message
    assert ':7:' in message


def test_no_agents_tasks_directory(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'order.md'
    path.write_text(SETTINGS + ORDER_HEADER + ROW)
    with pytest.raises(ralphlib.exceptions.OrderFormatError, match='agents/tasks'):
        ralphlib.order.read_order(path)


def order_with(project: pathlib.Path, rows: list[str], tail: str = '', every: int | None = None) -> ralphlib.order.Order:
    settings = SETTINGS + (f'| checkpoint every | {every} |\n' if every else '')
    return ralphlib.order.read_order(write_order(project, settings + ORDER_HEADER + ''.join(rows) + tail))


L1 = '| 1 | parser/tasks-1.md | - | - | {} |\n'
L2 = '| 2 | lexicon/tasks-1.md | 1 | - | {} |\n'
L3 = '| 3 | report/tasks-2.md | - | - | {} |\n'
L4 = '| 4 | cache/tasks-1.md | - | - | {} |\n'
CP = '| | **Checkpoint** | | | {} |\n'
FINAL = '| | **Final checkpoint** | | | {} |\n'


def test_first_todo_list_runs(project: pathlib.Path) -> None:
    order = order_with(project, [L1.format('merged abc1234'), L2.format('todo'), L3.format('todo')])
    step = ralphlib.order.next_step(order)
    assert isinstance(step, ralphlib.order.RunList)
    assert step.row.label == '2'


@pytest.mark.parametrize('status', ['running', 'waiting: test gate'])
def test_resume_a_running_or_waiting_list(project: pathlib.Path, status: str) -> None:
    order = order_with(project, [L1.format('merged abc1234'), L2.format(status)])
    step = ralphlib.order.next_step(order)
    assert isinstance(step, ralphlib.order.Resume)
    assert step.row.status == status


def test_waits_for_unmet_raises(project: pathlib.Path) -> None:
    order = order_with(project, [L1.format('todo'), L2.format('todo')])
    assert isinstance(ralphlib.order.next_step(order), ralphlib.order.RunList)
    order = order_with(project, [L3.format('merged abc1234'), L2.format('todo'), L1.format('todo')])
    with pytest.raises(ralphlib.exceptions.WaitsForUnmetError, match='list 2 waits for list 1'):
        ralphlib.order.next_step(order)


def test_explicit_checkpoint_due_and_resume(project: pathlib.Path) -> None:
    rows = [L1.format('merged abc1234'), L2.format('merged def5678'), CP.format('{}'), L3.format('todo')]
    step = ralphlib.order.next_step(order_with(project, [r.replace('{}', 'todo') for r in rows]))
    assert step == ralphlib.order.RunCheckpoint(label='checkpoint:1', position=2, final=False, after='2')
    step = ralphlib.order.next_step(order_with(project, [r.replace('{}', 'failed 3 tests') for r in rows]))
    assert isinstance(step, ralphlib.order.Resume)
    assert step.row.status == 'failed 3 tests'
    step = ralphlib.order.next_step(order_with(project, [r.replace('{}', 'passed 90') for r in rows]))
    assert isinstance(step, ralphlib.order.RunList)


def test_final_checkpoint_then_finished(project: pathlib.Path) -> None:
    merged = [L1.format('merged abc1234'), L2.format('merged def5678')]
    step = ralphlib.order.next_step(order_with(project, [*merged, FINAL.format('todo')]))
    assert step == ralphlib.order.RunCheckpoint(label='checkpoint:1', position=2, final=True, after='2')
    assert ralphlib.order.next_step(order_with(project, [*merged, FINAL.format('passed 90')])) == ralphlib.order.Finished()


def test_implicit_checkpoint_after_the_third_merge(project: pathlib.Path) -> None:
    rows = [L1.format('merged a1'), L2.format('merged b2'), L3.format('merged c3')]
    step = ralphlib.order.next_step(order_with(project, rows))
    assert step == ralphlib.order.RunCheckpoint(label='Checkpoint after 3', position=2, final=True, after='3')
    two = [L1.format('merged a1'), L2.format('merged b2'), L3.format('todo'), L4.format('todo')]
    assert isinstance(ralphlib.order.next_step(order_with(project, two)), ralphlib.order.RunList)
    step = ralphlib.order.next_step(order_with(project, two, every=2))
    assert step == ralphlib.order.RunCheckpoint(label='Checkpoint after 2', position=1, final=False, after='2')


@pytest.mark.parametrize('every', [2, 3])
def test_no_implicit_checkpoint_leaves_a_short_tail(project: pathlib.Path, every: int) -> None:
    three = [L1.format('merged a1'), L2.format('merged b2'), L3.format('merged c3'), L4.format('todo')]
    rows = three if every == 3 else [L1.format('merged a1'), L2.format('merged b2'), L3.format('todo')]
    step = ralphlib.order.next_step(order_with(project, rows, every=every))
    assert isinstance(step, ralphlib.order.RunList)
    assert step.row.label == rows[-1].split('|')[1].strip()
    merged = [row.replace('todo', 'merged d4') for row in rows]
    step = ralphlib.order.next_step(order_with(project, merged, every=every))
    last = merged[-1].split('|')[1].strip()
    assert step == ralphlib.order.RunCheckpoint(label=f'Checkpoint after {last}', position=len(merged) - 1, final=True, after=last)


def test_implicit_checkpoint_status_is_read_back(project: pathlib.Path) -> None:
    rows = [L1.format('merged a1'), L2.format('merged b2'), L3.format('merged c3')]
    order = order_with(project, rows, tail='\nCheckpoint after 3: passed 90\n')
    assert order.implicit == (('3', 'passed 90'),)
    assert ralphlib.order.next_step(order) == ralphlib.order.Finished()
    order = order_with(project, rows, tail='\nCheckpoint after 3: failed 2\n')
    step = ralphlib.order.next_step(order)
    assert isinstance(step, ralphlib.order.Resume)
    assert step.row.status == 'failed 2'
    order = order_with(project, rows, tail='\nCheckpoint after 3: running\n')
    assert isinstance(ralphlib.order.next_step(order), ralphlib.order.Resume)


def test_implicit_counter_restarts_after_a_passed_checkpoint(project: pathlib.Path) -> None:
    rows = [L1.format('merged a1'), L2.format('merged b2'), L3.format('todo'), L4.format('todo')]
    order = order_with(project, rows, tail='\nCheckpoint after 2: passed 90\n', every=2)
    step = ralphlib.order.next_step(order)
    assert isinstance(step, ralphlib.order.RunList)
    assert step.row.label == '3'


def test_all_merged_with_explicit_checkpoints_passed_is_finished(project: pathlib.Path) -> None:
    rows = [L1.format('merged a1'), CP.format('passed 1'), L2.format('merged b2'), FINAL.format('passed 2')]
    assert ralphlib.order.next_step(order_with(project, rows)) == ralphlib.order.Finished()


def git_commit(repo: git.Repo, name: str, message: str) -> str:
    target = pathlib.Path(repo.working_dir) / name
    target.write_text(message)
    repo.git.add(name)
    repo.git.commit('-m', message)
    return repo.head.commit.hexsha


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> git.Repo:
    repo = git.Repo.init(tmp_path / 'repo', initial_branch='main')
    repo.git.config('user.name', 'Probe')
    repo.git.config('user.email', 'probe@example.com')
    return repo


def test_decisions_since_filters_and_orders(repo: git.Repo) -> None:
    base = git_commit(repo, 'a', 'base\n\nQueue-decision: old')
    plain = git_commit(repo, 'b', 'plain change\n\nno trailer here')
    first = git_commit(repo, 'c', 'first stop\n\nWhy it was chosen.\n\nQueue-decision: parser 3')
    git_commit(repo, 'd', 'another plain')
    second = git_commit(repo, 'e', 'second stop\n\nQueue-decision: report 1')
    decisions = ralphlib.order.decisions_since(pathlib.Path(repo.working_dir), base)
    assert [d.commit for d in decisions] == [first, second]
    assert plain not in [d.commit for d in decisions]
    assert [d.task for d in decisions] == ['parser 3', 'report 1']
    assert decisions[0].subject == 'first stop'
    assert 'Why it was chosen.' in decisions[0].body


def test_decisions_since_reads_a_line_outside_the_last_paragraph(repo: git.Repo) -> None:
    base = git_commit(repo, 'a', 'base')
    stop = git_commit(repo, 'b', 'task stop\n\nWhy.\n\nQueue-decision: sites S1, S3 and S4 change\n\nCo-Authored-By: Probe <p@example.com>')
    decisions = ralphlib.order.decisions_since(pathlib.Path(repo.working_dir), base)
    assert [d.commit for d in decisions] == [stop]
    assert [d.task for d in decisions] == ['sites S1, S3 and S4 change']


def test_decisions_since_includes_merged_branch(repo: git.Repo) -> None:
    base = git_commit(repo, 'a', 'base')
    repo.git.checkout('-b', 'feature')
    stop = git_commit(repo, 'b', 'on branch\n\nQueue-decision: lexicon 2')
    repo.git.checkout('main')
    git_commit(repo, 'c', 'on main')
    repo.git.merge('--no-ff', 'feature', '-m', 'merge feature')
    decisions = ralphlib.order.decisions_since(pathlib.Path(repo.working_dir), base)
    assert [d.commit for d in decisions] == [stop]


def test_decisions_since_unknown_ref(repo: git.Repo) -> None:
    git_commit(repo, 'a', 'base')
    with pytest.raises(ralphlib.exceptions.GitError):
        ralphlib.order.decisions_since(pathlib.Path(repo.working_dir), 'no-such-ref')


def log_verdict(project: pathlib.Path, text: str | None, **settings: str) -> ralphlib.order.LogVerdict:
    extra = ''.join(f'| {name} | {value} |\n' for name, value in settings.items())
    path = write_order(project, SETTINGS + extra + ORDER_HEADER + L1.format('todo'))
    order = ralphlib.order.read_order(path)
    row = order.rows[0]
    assert isinstance(row, ralphlib.order.ListRow)
    if text is not None:
        log = project / 'ralpher-logs' / 'parser' / 'tasks-1' / 'final-tests.log'
        log.parent.mkdir(parents=True)
        log.write_text(text)
    return ralphlib.order.check_test_log(order, row, project)


def test_log_passes_with_pass_line_and_no_fail(project: pathlib.Path) -> None:
    verdict = log_verdict(project, 'a\nall passed\n')
    assert verdict.passed
    assert verdict.has_pass_line
    assert verdict.fail_lines == ()
    assert verdict.path == project / 'ralpher-logs' / 'parser' / 'tasks-1' / 'final-tests.log'


def test_log_missing(project: pathlib.Path) -> None:
    verdict = log_verdict(project, None)
    assert not verdict.passed
    assert verdict.fail_lines == ()
    assert not verdict.has_pass_line


def test_log_without_pass_line(project: pathlib.Path) -> None:
    verdict = log_verdict(project, 'nothing here\n')
    assert not verdict.passed
    assert not verdict.has_pass_line


def test_log_with_fail_match(project: pathlib.Path) -> None:
    verdict = log_verdict(project, 'FAILED a\nall passed\nFAILED b\n')
    assert not verdict.passed
    assert verdict.has_pass_line
    assert verdict.fail_lines == ('FAILED a', 'FAILED b')


def test_log_with_colour_codes(project: pathlib.Path) -> None:
    verdict = log_verdict(project, '\x1b[32mall passed\x1b[0m\n\x1b[31mFAILED x\x1b[0m\n')
    assert verdict.has_pass_line
    assert verdict.fail_lines == ('FAILED x',)


def test_log_path_uses_the_test_log_setting(project: pathlib.Path) -> None:
    verdict = log_verdict(project, None, **{'test log': 'out/{spec}-{index}.log'})
    assert verdict.path == project / 'out' / 'parser-1.log'


def test_set_status_changes_one_cell(project: pathlib.Path) -> None:
    rows = [L1.format('todo'), L2.format('todo'), CP.format('todo')]
    path = write_order(project, '# x\r\n' + SETTINGS + ORDER_HEADER + ''.join(rows).replace('\n', '\r\n') + 'tail\n')
    before = path.read_bytes()
    ralphlib.order.set_status(path, '2', 'merged abc1234')
    after = path.read_bytes()
    assert after.replace(b'merged abc1234', b'todo', 1) == before
    assert b'| 2 | lexicon/tasks-1.md | 1 | - | merged abc1234 |\r\n' in after
    ralphlib.order.set_status(path, 'checkpoint:1', 'passed 90')
    assert b'| | **Checkpoint** | | | passed 90 |\r\n' in path.read_bytes()
    assert ralphlib.order.read_order(path).rows[2].status == 'passed 90'


def test_set_status_unknown_label(project: pathlib.Path) -> None:
    path = write_order(project, SETTINGS + ORDER_HEADER + L1.format('todo'))
    with pytest.raises(ralphlib.exceptions.OrderFormatError):
        ralphlib.order.set_status(path, '9', 'running')


@pytest.mark.parametrize('status', ['a\nb', 'a\rb', 'x\nCheckpoint after 1: passed 9', 'x\r\n', 'a\x0bb', 'a\x0cb', 'a\x1cb', 'a\x85b', 'a b', 'a b'])
def test_set_status_refuses_a_line_break(project: pathlib.Path, status: str) -> None:
    path = write_order(project, SETTINGS + ORDER_HEADER + L1.format('todo'))
    before = path.read_bytes()
    with pytest.raises(ralphlib.exceptions.OrderFormatError, match='line break'):
        ralphlib.order.set_status(path, '1', status)
    assert path.read_bytes() == before


def test_set_status_restores_a_file_the_write_left_unparseable(project: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_order(project, SETTINGS + ORDER_HEADER + L1.format('todo'))
    before = path.read_bytes()

    def refuse(order_path: pathlib.Path) -> None:
        raise ralphlib.exceptions.OrderFormatError('refused')

    monkeypatch.setattr(ralphlib.order, 'read_order', refuse)
    with pytest.raises(ralphlib.exceptions.OrderFormatError, match='refused'):
        ralphlib.order.set_status(path, '1', 'running')
    assert path.read_bytes() == before


def test_set_status_implicit_checkpoint_line(project: pathlib.Path) -> None:
    path = write_order(project, SETTINGS + ORDER_HEADER + L1.format('merged a1') + '\nafter\n')
    ralphlib.order.set_status(path, 'Checkpoint after 1', 'running')
    assert ralphlib.order.read_order(path).implicit == (('1', 'running'),)
    ralphlib.order.set_status(path, 'Checkpoint after 1', 'passed 5')
    order = ralphlib.order.read_order(path)
    assert order.implicit == (('1', 'passed 5'),)
    assert path.read_text().endswith('after\n')


def checkpoint_label(step: ralphlib.order.Step) -> str:
    if isinstance(step, ralphlib.order.RunCheckpoint):
        return step.label
    assert isinstance(step, ralphlib.order.Resume)
    return step.row.label


def test_one_list_order_final_checkpoint_label(project: pathlib.Path) -> None:
    step = ralphlib.order.next_step(order_with(project, [L1.format('merged a1')]))
    assert step == ralphlib.order.RunCheckpoint(label='Checkpoint after 1', position=0, final=True, after='1')


@pytest.mark.parametrize(
    ('rows', 'every', 'tail'),
    [
        ([L1.format('merged a1'), CP.format('todo'), L2.format('todo')], None, ''),
        ([L1.format('merged a1'), FINAL.format('todo')], None, ''),
        ([L1.format('merged a1'), L2.format('merged b2'), L3.format('merged c3')], None, ''),
        ([L1.format('merged a1')], None, ''),
        ([L1.format('merged a1'), CP.format('running'), L2.format('todo')], None, ''),
        ([L1.format('merged a1'), L2.format('merged b2')], 2, '\nCheckpoint after 2: failed 2\n'),
    ],
)
def test_checkpoint_label_round_trip(project: pathlib.Path, rows: list[str], every: int | None, tail: str) -> None:
    settings = SETTINGS + (f'| checkpoint every | {every} |\n' if every else '')
    path = write_order(project, settings + ORDER_HEADER + ''.join(rows) + tail)
    step = ralphlib.order.next_step(ralphlib.order.read_order(path))
    assert isinstance(step, ralphlib.order.RunCheckpoint | ralphlib.order.Resume)
    ralphlib.order.set_status(path, checkpoint_label(step), 'passed 9')
    after = ralphlib.order.next_step(ralphlib.order.read_order(path))
    assert after != step
    if isinstance(after, ralphlib.order.RunCheckpoint | ralphlib.order.Resume):
        assert checkpoint_label(after) != checkpoint_label(step)


SETTINGS_WITH_PAGE = SETTINGS + '| progress page | |\n'
ONE_LIST = ORDER_HEADER + '| 1 | `parser/tasks-1.md` | - | - | todo |\n'


def test_set_setting_changes_only_the_empty_cell(project: pathlib.Path) -> None:
    path = write_order(project, '# Order\n\n' + SETTINGS_WITH_PAGE + '\n' + ONE_LIST)
    before = path.read_bytes()
    ralphlib.order.set_setting(path, 'progress page', 'https://example.test/p')
    after = path.read_bytes()
    assert after == before.replace(b'| progress page | |', b'| progress page | https://example.test/p |')
    assert ralphlib.order.read_order(path).settings.progress_page == 'https://example.test/p'


def test_set_setting_adds_a_missing_row_last(project: pathlib.Path) -> None:
    path = write_order(project, SETTINGS + '\n' + ONE_LIST)
    ralphlib.order.set_setting(path, 'progress page', 'https://example.test/p')
    lines = path.read_text().splitlines()
    assert lines[lines.index('| test pass line | `all passed` |') + 1] == '| progress page | https://example.test/p |'
    assert ralphlib.order.read_order(path).settings.progress_page == 'https://example.test/p'


def test_set_setting_adds_a_row_with_crlf_endings(project: pathlib.Path) -> None:
    path = write_order(project, '')
    path.write_bytes((SETTINGS + '\n' + ONE_LIST).replace('\n', '\r\n').encode())
    ralphlib.order.set_setting(path, 'test log', 'logs/x.log')
    assert b'| test log | logs/x.log |\r\n' in path.read_bytes()
    assert b'\n' not in path.read_bytes().replace(b'\r\n', b'')


def test_set_setting_unknown_name(project: pathlib.Path) -> None:
    path = write_order(project, SETTINGS + '\n' + ONE_LIST)
    before = path.read_bytes()
    with pytest.raises(ralphlib.exceptions.OrderFormatError):
        ralphlib.order.set_setting(path, 'colour', 'red')
    assert path.read_bytes() == before


def test_set_setting_invalid_value_restores_the_file(project: pathlib.Path) -> None:
    path = write_order(project, SETTINGS + '| checkpoint every | 2 |\n\n' + ONE_LIST)
    before = path.read_bytes()
    with pytest.raises(ralphlib.exceptions.OrderFormatError):
        ralphlib.order.set_setting(path, 'checkpoint every', 'x')
    assert path.read_bytes() == before


def test_set_setting_value_with_a_bar_round_trips(project: pathlib.Path) -> None:
    path = write_order(project, SETTINGS_WITH_PAGE + '\n' + ONE_LIST)
    ralphlib.order.set_setting(path, 'progress page', 'https://example.test/a|b')
    assert ralphlib.order.read_order(path).settings.progress_page == 'https://example.test/a|b'


def raise_os_error(*args: object, **kwargs: object) -> bytes:
    raise PermissionError('denied')


SET_STATUS_AND_SETTING = [
    lambda path: ralphlib.order.set_status(path, '1', 'done'),
    lambda path: ralphlib.order.set_setting(path, 'test log', 'x.log'),
]


def test_read_order_names_the_path_on_an_os_error(project: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_order(project, SETTINGS + ORDER_HEADER + L1.format('todo'))
    monkeypatch.setattr(pathlib.Path, 'read_bytes', raise_os_error)
    with pytest.raises(ralphlib.exceptions.OrderFormatError, match=str(path)):
        ralphlib.order.read_order(path)


@pytest.mark.parametrize('call', [lambda path: ralphlib.order.read_order(path), *SET_STATUS_AND_SETTING])
def test_an_undecodable_order_file_is_an_order_format_error(project: pathlib.Path, call: object) -> None:
    path = write_order(project, '')
    path.write_bytes(b'\xff\xfe\xfa')
    with pytest.raises(ralphlib.exceptions.OrderFormatError, match=str(path)):
        call(path)  # type: ignore[operator]


@pytest.mark.parametrize('call', SET_STATUS_AND_SETTING)
def test_an_unreadable_order_file_is_an_order_format_error(project: pathlib.Path, monkeypatch: pytest.MonkeyPatch, call: object) -> None:
    path = write_order(project, SETTINGS + ORDER_HEADER + L1.format('todo'))
    monkeypatch.setattr(pathlib.Path, 'read_bytes', raise_os_error)
    with pytest.raises(ralphlib.exceptions.OrderFormatError, match=str(path)):
        call(path)  # type: ignore[operator]


@pytest.mark.parametrize('call', SET_STATUS_AND_SETTING)
def test_a_failed_write_is_an_order_format_error(project: pathlib.Path, monkeypatch: pytest.MonkeyPatch, call: object) -> None:
    path = write_order(project, SETTINGS + ORDER_HEADER + L1.format('todo'))
    monkeypatch.setattr(pathlib.Path, 'write_bytes', raise_os_error)
    with pytest.raises(ralphlib.exceptions.OrderFormatError, match='cannot write'):
        call(path)  # type: ignore[operator]


def test_set_setting_names_both_failures_when_the_restore_fails(project: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_order(project, SETTINGS + '| checkpoint every | 2 |\n\n' + ONE_LIST)
    real = pathlib.Path.write_bytes
    calls: list[bytes] = []

    def fail_second(self: pathlib.Path, data: bytes) -> int:
        calls.append(data)
        if len(calls) > 1:
            raise PermissionError('denied')
        return real(self, data)

    monkeypatch.setattr(pathlib.Path, 'write_bytes', fail_second)
    with pytest.raises(ralphlib.exceptions.OrderFormatError, match='restoring the original also failed') as info:
        ralphlib.order.set_setting(path, 'checkpoint every', 'x')
    assert 'positive integer' in str(info.value)
    assert isinstance(info.value.__cause__, ralphlib.exceptions.OrderFormatError)


def test_check_test_log_os_error_is_an_order_format_error(project: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_order(project, SETTINGS + ORDER_HEADER + L1.format('todo'))
    order = ralphlib.order.read_order(path)
    row = order.rows[0]
    assert isinstance(row, ralphlib.order.ListRow)
    log = project / 'ralpher-logs' / 'parser' / 'tasks-1' / 'final-tests.log'
    log.parent.mkdir(parents=True)
    log.write_text('all passed\n')
    monkeypatch.setattr(pathlib.Path, 'read_bytes', raise_os_error)
    with pytest.raises(ralphlib.exceptions.OrderFormatError, match='final-tests.log'):
        ralphlib.order.check_test_log(order, row, project)
