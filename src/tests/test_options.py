import pytest

import ralphlib.exceptions
import ralphlib.options


def test_unbalanced_quote_in_args_raises_invalid_args_error() -> None:
    with pytest.raises(ralphlib.exceptions.InvalidArgsError, match="--print 'oops"):
        ralphlib.options.RalpherOptions(args="--print 'oops")


def test_passed_worktree_base_ref_is_stored() -> None:
    assert ralphlib.options.RalpherOptions(worktree_base_ref='head').passed_worktree_base_ref == 'head'


def test_args_settings_wins_over_worktree_base_ref() -> None:
    options = ralphlib.options.RalpherOptions(worktree_base_ref='head', args='--print --settings {}')
    assert options.passed_worktree_base_ref is None
    assert options.args_override_warnings() == ['--args holds --settings: it wins, and --worktree-base-ref is not passed']


def test_args_worktree_warns() -> None:
    options = ralphlib.options.RalpherOptions(worktree=True, args='--print -w')
    assert len(options.args_override_warnings()) == 1


def test_no_warning_without_overlap() -> None:
    assert ralphlib.options.RalpherOptions(worktree=True).args_override_warnings() == []
