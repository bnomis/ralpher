import pathlib

import pytest

import ralphlib.exceptions
import ralphlib.options


def test_unbalanced_quote_in_args_raises_invalid_args_error() -> None:
    with pytest.raises(ralphlib.exceptions.InvalidArgsError, match="--print 'oops"):
        ralphlib.options.RalpherOptions(args="--print 'oops")


@pytest.mark.parametrize(
    ('args', 'flag', 'instead'),
    [
        ('--print --worktree x', '--worktree', 'ralpher --worktree'),
        ('--print --worktree=x', '--worktree', 'ralpher --worktree'),
        ('--print -w', '-w', 'ralpher --worktree'),
        ('--print --settings {}', '--settings', '--worktree-base-ref'),
        ('--print --settings={}', '--settings', '--worktree-base-ref'),
    ],
)
def test_worktree_flags_in_args_are_refused(args: str, flag: str, instead: str) -> None:
    with pytest.raises(ralphlib.exceptions.InvalidArgsError, match=f'{flag}.*{instead}'):
        ralphlib.options.RalpherOptions(args=args)


def test_worktree_base_ref_is_stored() -> None:
    assert ralphlib.options.RalpherOptions(worktree_base_ref='head').worktree_base_ref == 'head'


def test_args_without_worktree_flags_are_accepted() -> None:
    ralphlib.options.RalpherOptions(worktree=True, args='--print --verbose')


@pytest.mark.parametrize('iterations', [0, -1])
def test_iterations_below_one_are_refused(iterations: int) -> None:
    with pytest.raises(ralphlib.exceptions.InvalidIterationsError, match='at least 1'):
        ralphlib.options.RalpherOptions(iterations=iterations)


def test_resolve_paths_makes_cwd_and_task_file_absolute(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    options = ralphlib.options.resolve_paths(ralphlib.options.RalpherOptions(cwd='.', task_file='TASKS.md'))
    assert options.cwd == str(tmp_path.resolve())
    assert options.task_file == str(tmp_path.resolve() / 'TASKS.md')


def test_resolve_paths_leaves_unset_paths_unset() -> None:
    options = ralphlib.options.resolve_paths(ralphlib.options.RalpherOptions())
    assert options.cwd is None
    assert options.task_file is None
