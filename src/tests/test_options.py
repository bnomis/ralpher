import pathlib

import hypothesis
import hypothesis.strategies
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


ARG_TOKENS = hypothesis.strategies.sampled_from(['--model=x', '--print', '--settings', '--settings={}', '--verbose', '--worktree', '--worktree=x', '-w', 'x'])


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    iterations=hypothesis.strategies.integers(min_value=-3, max_value=5),
    tokens=hypothesis.strategies.lists(ARG_TOKENS, max_size=4),
    unbalanced=hypothesis.strategies.booleans(),
)
def test_post_init_refuses_exactly_the_bad_iterations_and_args(iterations: int, tokens: list[str], unbalanced: bool) -> None:
    args = ' '.join(tokens) + (" '" if unbalanced else '')
    refused = any(token.split('=', 1)[0] in ralphlib.options.REFUSED_ARGS for token in tokens)
    if iterations < 1:
        expected: type[Exception] | None = ralphlib.exceptions.InvalidIterationsError
    elif unbalanced or refused:
        expected = ralphlib.exceptions.InvalidArgsError
    else:
        expected = None
    if expected is None:
        assert ralphlib.options.RalpherOptions(iterations=iterations, args=args).args == args
    else:
        with pytest.raises(expected):
            ralphlib.options.RalpherOptions(iterations=iterations, args=args)
