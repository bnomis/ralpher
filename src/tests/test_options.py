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
