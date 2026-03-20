import pathlib
import sys

import pygit2
import rich.console
import rich.prompt
import rich.text

import ralphlib.printer
import ralphlib.types

console_stderr = rich.console.Console(stderr=True, highlight=False)


class YNConfirm(rich.prompt.Confirm):
    def make_prompt(self, default):
        yes, no = ('Y', 'n') if default else ('y', 'N')
        prompt = self.prompt.copy()
        prompt.end = ''
        prompt.append(f' [{yes}/{no}] ')
        return prompt


def lines_to_text(lines: list[str]) -> rich.text.Text:
    return rich.text.Text(
        '\n'.join(lines),
        style=ralphlib.printer.type_to_style(ralphlib.types.MessageType.ALERT),
    )


def check_git(options, path: pathlib.Path | str | None = None) -> None:
    if options.skip_git_check:
        return

    repo_path = discover_repo_path(path=path)
    if repo_path is None:
        lines = ['Warning: not in a git repository.']
        decision = YNConfirm.ask(lines_to_text(lines), default=False)
        if not decision:
            sys.exit('Aborting due to not being in a git repository.')
        return

    check_repo_clean(options, repo_path)


def discover_repo_path(path: pathlib.Path | str | None = None) -> str | None:
    """
    Returns the path to the git repository if the given path (or current directory) is inside a git repository.
    """
    if path is None:
        path = pathlib.Path.cwd()
    else:
        path = pathlib.Path(path)

    return pygit2.discover_repository(str(path))


def is_git_repo(path: pathlib.Path | str | None = None) -> bool:
    return discover_repo_path(path) is not None


def check_repo_clean(options, repo_path: str) -> None:
    repo = pygit2.Repository(repo_path)
    wts = 'Git worktrees will be created from the origin repo.'
    if not is_clean_strict(repo):
        lines = ['Warning: the git working tree is not clean.']
        if options.worktree:
            lines.append(wts)
        lines.append('You probably want to commit and push before continuing. Continue?')
        decision = YNConfirm.ask(lines_to_text(lines), default=False)
        if not decision:
            sys.exit('Aborting due to unclean git working tree.')

    if has_unpushed_commits(repo):
        lines = ['Warning: there are unpushed commits.']
        if options.worktree:
            lines.append(wts)
        lines.append('You probably want to push before continuing. Continue?')
        decision = YNConfirm.ask(lines_to_text(lines), default=False)
        if not decision:
            sys.exit('Aborting due to unpushed commits.')


def is_clean_strict(repo: pygit2.Repository) -> bool:
    """Clean including untracked files (default git status behavior)"""
    return is_working_tree_clean(repo, include_untracked=True)


def is_clean_no_untracked(repo: pygit2.Repository) -> bool:
    """Clean ignoring untracked files (like git diff --quiet)"""
    return is_working_tree_clean(repo, include_untracked=False)


def is_working_tree_clean(repo: pygit2.Repository, include_untracked: bool = True) -> bool:
    """
    Returns True if the working tree is clean (no changes, no untracked files by default).

    - include_untracked=False → ignores new/untracked files (like git status --untracked-files=no)
    """
    status = repo.status(untracked_files='all' if include_untracked else 'no', ignored=False)

    # Most common & fastest check
    if not status:
        return True  # empty dict == clean

    # More explicit (handles weird edge cases better)
    return all(flags == pygit2.GIT_STATUS_CURRENT for flags in status.values())


def has_unpushed_commits(repo: pygit2.Repository) -> bool:
    """
    Returns True if the current branch has commits not pushed to its upstream
    (usually origin/<branch>).
    """

    callbacks = pygit2.RemoteCallbacks(credentials=pygit2.KeypairFromAgent('git'))

    # Optional but strongly recommended: fetch latest remote state first
    # (otherwise ahead/behind can be outdated)
    try:
        origin = repo.remotes['origin']
        origin.fetch(callbacks=callbacks)
    except KeyError:
        console_stderr.print("No 'origin' remote found")
        return False
    except Exception as e:
        console_stderr.print(f'Fetch failed: {e}')
        return False

    head = repo.head
    short_name = head.shorthand  # e.g. 'main'

    upstream = get_upstream_branch(repo)
    if upstream is None:
        console_stderr.print(f'No upstream branch set for the {short_name} branch')
        return False

    # This is the key call
    ahead, _ = repo.ahead_behind(head.target, upstream.target)

    # ahead > 0 means local commits not present on the remote tracking branch
    return ahead > 0


def get_upstream_branch(repo: pygit2.Repository) -> pygit2.Branch | None:
    if repo.head_is_detached:
        console_stderr.print('Detached HEAD — no current branch')
        return None

    branch_name = repo.head.shorthand
    current_branch = repo.branches.get(branch_name)
    if current_branch is None:
        console_stderr.print(f'Current branch "{branch_name}" not found in repository')
        return None
    return current_branch.upstream
