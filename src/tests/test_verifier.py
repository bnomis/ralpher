import pathlib
import threading
import unittest.mock

import git
import hypothesis
import hypothesis.strategies
import pytest

import ralphlib.exceptions
import ralphlib.iteration
import ralphlib.options
import ralphlib.verifier

# auditme: accept[non-alphabetical-literal] status progression; the order is the meaning
STATUSES = ['todo', 'in-progress', 'done']
TASK_FILE = 'agents/tasks/feat/tasks-1.md'
SLUG = 'feat-tasks-1'


def test_headings_with_and_without_status() -> None:
    text = '## Task 1: First\n\n**Status:** todo\n\n## Task 2: Second\n\nno status here\n'
    assert ralphlib.verifier.parse_tasks(text) == [
        ralphlib.verifier.TaskStatus(1, 'First', 'todo'),
        ralphlib.verifier.TaskStatus(2, 'Second', ''),
    ]


def test_status_is_lowercased() -> None:
    tasks = ralphlib.verifier.parse_tasks('## Task 3: T\n**Status:** Done\n')
    assert tasks[0].status == 'done'


def test_first_status_line_wins() -> None:
    tasks = ralphlib.verifier.parse_tasks('## Task 1: T\n**Status:** todo\n**Status:** done\n')
    assert tasks[0].status == 'todo'


def test_status_does_not_leak_to_next_heading() -> None:
    text = '## Task 1: A\n**Status:** done\n## Not a task\n**Status:** todo\n'
    tasks = ralphlib.verifier.parse_tasks(text)
    assert [t.status for t in tasks] == ['done']


def test_fenced_example_is_ignored() -> None:
    text = '```text\n## Task 9: Example\n**Status:** todo\n```\n\n~~~\n## Task 8: Other\n~~~\n\n## Task 1: Real\n**Status:** done\n'
    tasks = ralphlib.verifier.parse_tasks(text)
    assert tasks == [ralphlib.verifier.TaskStatus(1, 'Real', 'done')]


def test_no_headings() -> None:
    assert ralphlib.verifier.parse_tasks('# Title\n\nSome text\n') == []
    assert ralphlib.verifier.parse_tasks('') == []


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    hypothesis.strategies.lists(
        hypothesis.strategies.tuples(
            hypothesis.strategies.integers(min_value=1, max_value=999),
            hypothesis.strategies.from_regex(r'[A-Za-z][A-Za-z0-9 ]{0,20}', fullmatch=True),
            hypothesis.strategies.sampled_from(STATUSES),
        ),
        max_size=10,
    )
)
def test_round_trip(entries: list[tuple[int, str, str]]) -> None:
    text = '# Tasks\n\n' + ''.join(f'## Task {n}: {title}\n\n**Status:** {status}\n**Priority:** high\n\n' for n, title, status in entries)
    tasks = ralphlib.verifier.parse_tasks(text)
    assert [(t.number, t.status) for t in tasks] == [(n, s) for n, _, s in entries]


def run_git(cwd: pathlib.Path, *args: str) -> None:
    git.Git(str(cwd)).execute(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com', *args])


def make_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    repo = (tmp_path / 'repo').resolve()
    (repo / 'agents/tasks/feat').mkdir(parents=True)
    (repo / TASK_FILE).write_text('## Task 1: T\n**Status:** todo\n')
    run_git(repo, 'init', '-b', 'main')
    run_git(repo, 'add', '.')
    run_git(repo, 'commit', '-m', 'init')
    return repo


def make_options(repo: pathlib.Path) -> ralphlib.options.RalpherOptions:
    return ralphlib.options.RalpherOptions(prompt='p', task_file=str(repo / TASK_FILE), worktree=True, cwd=str(repo))


def test_worktree_task_file_found(tmp_path: pathlib.Path) -> None:
    repo = make_repo(tmp_path)
    wt = (tmp_path / 'wt').resolve()
    run_git(repo, 'worktree', 'add', '-b', f'worktree-{SLUG}', str(wt))
    assert ralphlib.verifier.worktree_task_file(make_options(repo)) == wt / TASK_FILE


def test_worktree_task_file_threads_list_worktrees_once(tmp_path: pathlib.Path) -> None:
    repo = make_repo(tmp_path)
    wt = (tmp_path / 'wt').resolve()
    run_git(repo, 'worktree', 'add', '-b', f'worktree-{SLUG}', str(wt))
    options = make_options(repo)
    results: list[pathlib.Path | None] = []
    with unittest.mock.patch.object(ralphlib.verifier, 'parse_worktrees', wraps=ralphlib.verifier.parse_worktrees) as parse:
        threads = [threading.Thread(target=lambda: results.append(ralphlib.verifier.worktree_task_file(options))) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert results == [wt / TASK_FILE, wt / TASK_FILE]
    assert parse.call_count == 1


def test_worktree_task_file_no_match(tmp_path: pathlib.Path) -> None:
    repo = make_repo(tmp_path)
    assert ralphlib.verifier.worktree_task_file(make_options(repo)) is None


def test_worktree_task_file_ignores_unrelated_branch(tmp_path: pathlib.Path) -> None:
    repo = make_repo(tmp_path)
    run_git(repo, 'worktree', 'add', '-b', 'worktree-other', str((tmp_path / 'wt').resolve()))
    assert ralphlib.verifier.worktree_task_file(make_options(repo)) is None


def test_worktree_task_file_no_repository(tmp_path: pathlib.Path) -> None:
    options = ralphlib.options.RalpherOptions(prompt='p', task_file=TASK_FILE, worktree=True, cwd=str(tmp_path))
    assert ralphlib.verifier.worktree_task_file(options) is None


def plain_options(path: pathlib.Path) -> ralphlib.options.RalpherOptions:
    return ralphlib.options.RalpherOptions(prompt='p', task_file=str(path), cwd=str(path.parent))


def test_verify_stop_all_done(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'tasks.md'
    path.write_text('## Task 1: A\n**Status:** done\n## Task 2: B\n**Status:** Done\n')
    check = ralphlib.verifier.verify_stop(plain_options(path))
    assert check.verified
    assert check.all_done
    assert check.not_done == []
    assert check.total == 2


def test_verify_stop_some_not_done(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'tasks.md'
    path.write_text('## Task 1: A\n**Status:** todo\n## Task 2: B\n**Status:** done\n## Task 3: C\n')
    check = ralphlib.verifier.verify_stop(plain_options(path))
    assert check.verified
    assert not check.all_done
    assert check.not_done == [ralphlib.verifier.TaskStatus(1, 'A', 'todo'), ralphlib.verifier.TaskStatus(3, 'C', '')]
    assert check.total == 3


def test_verify_stop_missing_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'missing.md'
    check = ralphlib.verifier.verify_stop(plain_options(path))
    assert not check.verified
    assert str(path) in check.reason


def test_verify_stop_not_utf8(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'tasks.md'
    path.write_bytes(b'\xff\xfe\x00bad')
    check = ralphlib.verifier.verify_stop(plain_options(path))
    assert not check.verified
    assert str(path) in check.reason


def test_verify_stop_empty_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'tasks.md'
    path.write_text('')
    check = ralphlib.verifier.verify_stop(plain_options(path))
    assert not check.verified
    assert check.reason == f'no tasks found in {path}'


def test_verify_stop_worktree_not_found(tmp_path: pathlib.Path) -> None:
    repo = make_repo(tmp_path)
    check = ralphlib.verifier.verify_stop(make_options(repo))
    assert not check.verified
    assert check.reason == f'worktree for {SLUG} not found'


def test_verify_stop_reads_worktree_copy(tmp_path: pathlib.Path) -> None:
    repo = make_repo(tmp_path)
    wt = (tmp_path / 'wt').resolve()
    run_git(repo, 'worktree', 'add', '-b', f'worktree-{SLUG}', str(wt))
    (repo / TASK_FILE).write_text('## Task 1: T\n**Status:** done\n')
    check = ralphlib.verifier.verify_stop(make_options(repo))
    assert check.verified
    assert not check.all_done
    assert [t.number for t in check.not_done] == [1]


def test_verify_stop_worktree_missing_file(tmp_path: pathlib.Path) -> None:
    repo = make_repo(tmp_path)
    wt = (tmp_path / 'wt').resolve()
    run_git(repo, 'worktree', 'add', '-b', f'worktree-{SLUG}', str(wt))
    (wt / TASK_FILE).unlink()
    check = ralphlib.verifier.verify_stop(make_options(repo))
    assert not check.verified


def test_worktree_task_file_cwd_through_symlink(tmp_path: pathlib.Path) -> None:
    repo = make_repo(tmp_path)
    wt = (tmp_path / 'wt').resolve()
    run_git(repo, 'worktree', 'add', '-b', f'worktree-{SLUG}', str(wt))
    link = tmp_path / 'link'
    link.symlink_to(repo)
    options = ralphlib.options.RalpherOptions(prompt='p', task_file=str(repo / TASK_FILE), worktree=True, cwd=str(link))
    assert ralphlib.verifier.worktree_task_file(options) == wt / TASK_FILE


def test_verify_stop_task_file_outside_repository(tmp_path: pathlib.Path) -> None:
    repo = make_repo(tmp_path)
    outside = tmp_path / 'outside.md'
    outside.write_text('## Task 1: T\n**Status:** todo\n')
    options = ralphlib.options.RalpherOptions(prompt='p', task_file=str(outside), worktree=True, cwd=str(repo))
    check = ralphlib.verifier.verify_stop(options)
    assert not check.verified
    assert str(outside) in check.reason


def test_agent_task_file_worktree_not_found_raises_tasks_file_error(tmp_path: pathlib.Path) -> None:
    repo = make_repo(tmp_path)
    with pytest.raises(ralphlib.exceptions.TasksFileError):
        ralphlib.verifier.agent_task_file(make_options(repo))


def test_worktree_task_file_runs_git_worktree_list_once(tmp_path: pathlib.Path) -> None:
    repo = make_repo(tmp_path)
    wt = (tmp_path / 'wt').resolve()
    run_git(repo, 'worktree', 'add', '-b', f'worktree-{SLUG}', str(wt))
    options = make_options(repo)
    with unittest.mock.patch.object(ralphlib.verifier, 'parse_worktrees', wraps=ralphlib.verifier.parse_worktrees) as parse:
        for _ in range(5):
            assert ralphlib.verifier.worktree_task_file(options) == wt / TASK_FILE
    assert parse.call_count == 1


def test_make_context_clears_the_cached_worktree_path() -> None:
    options = ralphlib.options.RalpherOptions(prompt='p', quiet=True)
    options.worktree_task_path = pathlib.Path('/stale')
    ralphlib.iteration.make_context(options, 'prompt', 1)
    assert options.worktree_task_path is None


class TestParseWorktrees:
    def test_entries_with_a_branch(self) -> None:
        porcelain = 'worktree /src/probe\nHEAD abc\nbranch refs/heads/main\n\nworktree /src/probe/wt\nHEAD def\nbranch refs/heads/worktree-a-b\n'
        assert ralphlib.verifier.parse_worktrees(porcelain) == [
            (pathlib.Path('/src/probe'), 'refs/heads/main'),
            (pathlib.Path('/src/probe/wt'), 'refs/heads/worktree-a-b'),
        ]

    def test_detached_entry_is_skipped(self) -> None:
        assert ralphlib.verifier.parse_worktrees('worktree /src/probe\nHEAD abc\ndetached\n') == []

    def test_bare_entry_is_skipped(self) -> None:
        porcelain = 'worktree /src/probe.git\nbare\n\nworktree /src/wt\nHEAD abc\nbranch refs/heads/x\n'
        assert ralphlib.verifier.parse_worktrees(porcelain) == [(pathlib.Path('/src/wt'), 'refs/heads/x')]

    def test_empty_output(self) -> None:
        assert ralphlib.verifier.parse_worktrees('') == []


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    entries=hypothesis.strategies.lists(
        hypothesis.strategies.tuples(
            hypothesis.strategies.from_regex(r'/[a-z0-9]{1,8}(/[a-z0-9]{1,8}){0,2}', fullmatch=True),
            hypothesis.strategies.one_of(
                hypothesis.strategies.none(),
                hypothesis.strategies.from_regex(r'refs/heads/[a-z0-9-]{1,12}', fullmatch=True),
            ),
        ),
        max_size=5,
    )
)
def test_parse_worktrees_returns_exactly_the_entries_with_a_branch(entries: list[tuple[str, str | None]]) -> None:
    blocks = [f'worktree {path}\nHEAD abc\n' + (f'branch {branch}\n' if branch else 'detached\n') for path, branch in entries]
    expected = [(pathlib.Path(path), branch) for path, branch in entries if branch]
    assert ralphlib.verifier.parse_worktrees('\n'.join(blocks)) == expected
