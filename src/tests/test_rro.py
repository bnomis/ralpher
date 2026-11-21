import importlib.util
import os
import pathlib
import subprocess
import types

import git
import orjson
import pytest

BIN = pathlib.Path(__file__).resolve().parents[2] / 'bin'
SCRIPT = BIN / 'rro.py'

ORDER = """| Setting | Value |
|---|---|
| checkpoint command | `make test-slow` |
| test pass line | `all passed` |

| # | Task list | Waits for | Stops for you | Status |
|---|---|---|---|---|
| a | `parser/tasks-1.md` | - | - | todo |
| b | `report/tasks-2.md` | a | - | todo |
"""


@pytest.fixture
def rro() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location('rro_script', SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def order(tmp_path: pathlib.Path) -> pathlib.Path:
    for name in ('parser/tasks-1.md', 'report/tasks-2.md'):
        target = tmp_path / 'agents' / 'tasks' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('# Tasks\n')
    path = tmp_path / 'agents' / 'tasks' / 'order-x.md'
    path.write_text(ORDER)
    return path


def call(rro: types.ModuleType, capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[object, int]:
    code = 0
    try:
        rro.main(list(argv))
    except SystemExit as e:
        code = int(e.code)
    out = capsys.readouterr().out
    assert out.endswith('\n')
    assert out.count('\n') == 1
    return orjson.loads(out), code


def test_next_prints_the_step_and_row(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    result, code = call(rro, capsys, 'next', str(order))
    assert code == 0
    assert result == {
        'kind': 'run-list',
        'row': {'type': 'list', 'label': 'a', 'task_list': 'parser/tasks-1.md', 'waits_for': [], 'stops_for_you': '-', 'status': 'todo'},
    }


def test_next_reports_a_checkpoint_when_all_lists_merged(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    order.write_text(ORDER.replace('| todo |', '| merged abc |'))
    result, _ = call(rro, capsys, 'next', str(order))
    assert result['kind'] == 'run-checkpoint'
    assert result['after'] == 'b'


def test_set_status_then_next_resumes(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    result, code = call(rro, capsys, 'set-status', str(order), 'a', 'running')
    assert (result, code) == ({'ok': True}, 0)
    result, _ = call(rro, capsys, 'next', str(order))
    assert result['kind'] == 'resume'
    assert result['row']['status'] == 'running'


def test_check_log_prints_the_verdict(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = order.parents[2] / 'ralpher-logs' / 'parser' / 'tasks-1' / 'final-tests.log'
    log.parent.mkdir(parents=True)
    log.write_text('x\nall passed\n')
    result, code = call(rro, capsys, 'check-log', str(order), 'a')
    assert code == 0
    assert result == {'passed': True, 'path': str(log), 'fail_lines': [], 'has_pass_line': True}


def test_check_log_unknown_label(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    result, code = call(rro, capsys, 'check-log', str(order), 'zzz')
    assert code == 2
    assert result['error'] == 'OrderFormatError'


def test_decisions_prints_a_list(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = git.Repo.init(order.parents[2], initial_branch='main')
    repo.git.config('user.name', 'Probe')
    repo.git.config('user.email', 'probe@example.com')
    repo.git.add('-A')
    repo.git.commit('-m', 'base')
    base = repo.head.commit.hexsha
    (order.parents[2] / 'x').write_text('x')
    repo.git.add('x')
    repo.git.commit('-m', 'a stop\n\nQueue-decision: parser 3')
    result, code = call(rro, capsys, 'decisions', str(order), '--since', base)
    assert code == 0
    assert isinstance(result, list)
    assert [d['task'] for d in result] == ['parser 3']
    assert result[0]['subject'] == 'a stop'


def test_decisions_bad_ref_is_an_error_line(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    result, code = call(rro, capsys, 'decisions', str(order), '--since', 'nope')
    assert code == 2
    assert result['error'] == 'GitError'


def test_malformed_order_is_an_error_line(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    order.write_text(ORDER.replace('| a | `parser/tasks-1.md`', '| a b | `parser/tasks-1.md`'))
    result, code = call(rro, capsys, 'next', str(order))
    assert code == 2
    assert result['error'] == 'OrderFormatError'
    assert 'label' in result['message']


def test_undecodable_order_is_an_error_line(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    order.write_bytes(b'\xff\xfe\xfa')
    result, code = call(rro, capsys, 'next', str(order))
    assert code == 2
    assert result['error'] == 'OrderFormatError'
    assert str(order) in result['message']


def test_next_checkpoint_carries_its_label(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    order.write_text(ORDER.replace('| todo |', '| merged abc |'))
    result, code = call(rro, capsys, 'next', str(order))
    assert code == 0
    assert result == {'kind': 'run-checkpoint', 'label': 'Checkpoint after b', 'position': 1, 'final': True, 'after': 'b'}


def test_next_resume_of_a_checkpoint_carries_its_label(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    order.write_text(ORDER.replace('| todo |', '| merged abc |'))
    step, _ = call(rro, capsys, 'next', str(order))
    assert isinstance(step, dict)
    result, code = call(rro, capsys, 'set-status', str(order), str(step['label']), 'running')
    assert (result, code) == ({'ok': True}, 0)
    result, _ = call(rro, capsys, 'next', str(order))
    assert isinstance(result, dict)
    assert result['kind'] == 'resume'
    assert result['row']['type'] == 'checkpoint'
    assert result['row']['label'] == step['label']


def test_set_setting_writes_the_value(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    result, code = call(rro, capsys, 'set-setting', str(order), 'progress page', 'https://example.com/p')
    assert (result, code) == ({'ok': True}, 0)
    assert '| progress page | https://example.com/p |' in order.read_text()


def test_set_setting_unknown_name_is_an_error_line(rro: types.ModuleType, order: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = order.read_bytes()
    result, code = call(rro, capsys, 'set-setting', str(order), 'no such setting', 'x')
    assert code == 2
    assert isinstance(result, dict)
    assert result['error'] == 'OrderFormatError'
    assert order.read_bytes() == before


def test_wrapper_runs_outside_the_repo_past_a_stub_python(order: pathlib.Path, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stubs = tmp_path / 'stubs'
    stubs.mkdir()
    stub = stubs / 'python'
    stub.write_text('#!/bin/sh\nexit 1\n')
    stub.chmod(0o755)
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    monkeypatch.setenv('PATH', f'{stubs}:{os.environ["PATH"]}')
    done = subprocess.run(  # noqa: S603
        [str(BIN / 'rro.sh'), 'next', str(order)],
        cwd=elsewhere,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert orjson.loads(done.stdout)['kind'] == 'run-list'
