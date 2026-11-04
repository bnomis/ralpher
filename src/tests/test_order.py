import pathlib

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

LISTS = ('lexicon/tasks-1.md', 'parser/tasks-1.md', 'report/tasks-2.md')


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
        ralphlib.order.CheckpointRow(final=False, status='todo'),
        ralphlib.order.ListRow('3', 'report/tasks-2.md', ('1', '2'), '-', 'todo'),
        ralphlib.order.CheckpointRow(final=True, status='todo'),
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
    assert step == ralphlib.order.RunCheckpoint(position=2, final=False, after='2')
    step = ralphlib.order.next_step(order_with(project, [r.replace('{}', 'failed 3 tests') for r in rows]))
    assert isinstance(step, ralphlib.order.Resume)
    assert step.row.status == 'failed 3 tests'
    step = ralphlib.order.next_step(order_with(project, [r.replace('{}', 'passed 90') for r in rows]))
    assert isinstance(step, ralphlib.order.RunList)


def test_final_checkpoint_then_finished(project: pathlib.Path) -> None:
    merged = [L1.format('merged abc1234'), L2.format('merged def5678')]
    step = ralphlib.order.next_step(order_with(project, [*merged, FINAL.format('todo')]))
    assert step == ralphlib.order.RunCheckpoint(position=2, final=True, after='2')
    assert ralphlib.order.next_step(order_with(project, [*merged, FINAL.format('passed 90')])) == ralphlib.order.Finished()


def test_implicit_checkpoint_after_the_third_merge(project: pathlib.Path) -> None:
    rows = [L1.format('merged a1'), L2.format('merged b2'), L3.format('merged c3')]
    step = ralphlib.order.next_step(order_with(project, rows))
    assert step == ralphlib.order.RunCheckpoint(position=2, final=True, after='3')
    two = [L1.format('merged a1'), L2.format('merged b2'), L3.format('todo')]
    assert isinstance(ralphlib.order.next_step(order_with(project, two)), ralphlib.order.RunList)
    step = ralphlib.order.next_step(order_with(project, two, every=2))
    assert step == ralphlib.order.RunCheckpoint(position=1, final=False, after='2')


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
    rows = [L1.format('merged a1'), L2.format('merged b2'), L3.format('todo')]
    order = order_with(project, rows, tail='\nCheckpoint after 2: passed 90\n', every=2)
    step = ralphlib.order.next_step(order)
    assert isinstance(step, ralphlib.order.RunList)
    assert step.row.label == '3'


def test_all_merged_with_explicit_checkpoints_passed_is_finished(project: pathlib.Path) -> None:
    rows = [L1.format('merged a1'), CP.format('passed 1'), L2.format('merged b2'), FINAL.format('passed 2')]
    assert ralphlib.order.next_step(order_with(project, rows)) == ralphlib.order.Finished()
