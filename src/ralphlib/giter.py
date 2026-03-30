import pathlib
import sys
from typing import TYPE_CHECKING

import git
import rich.console
import rich.prompt
import rich.text

import ralphlib.printer
import ralphlib.types

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions


console_stderr = rich.console.Console(stderr=True, highlight=False)


class YNConfirm(rich.prompt.Confirm):
    def make_prompt(self, default):
        yes, no = ('Y', 'n') if default else ('y', 'N')
        prompt = self.prompt.copy()
        prompt.end = ''
        prompt.append(f' [{yes}/{no}] ')
        return prompt


def lines_to_text(options: RalpherOptions, lines: list[str]) -> rich.text.Text:
    return rich.text.Text(
        '\n'.join(lines),
        style=ralphlib.printer.type_to_style(options, ralphlib.types.MessageType.ALERT),
    )


def check_git(options: RalpherOptions, path: pathlib.Path | str | None = None) -> None:
    if options.skip_git_check:
        return

    repo = discover_repo_path(path=path)
    if repo is None:
        lines = ['Warning: not in a git repository.']
        decision = YNConfirm.ask(lines_to_text(options, lines), default=False)
        if not decision:
            sys.exit('Aborting due to not being in a git repository.')
        return

    check_repo_clean(options, repo)


def discover_repo_path(path: pathlib.Path | str | None = None) -> git.Repo | None:
    """
    Returns the path to the git repository if the given path (or current directory) is inside a git repository.
    """
    if path is None:
        path = pathlib.Path.cwd()
    else:
        path = pathlib.Path(path)

    try:
        return git.Repo(str(path), search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        return None


def is_git_repo(path: pathlib.Path | str | None = None) -> bool:
    return discover_repo_path(path) is not None


def check_repo_clean(options: RalpherOptions, repo: git.Repo) -> None:
    wts = 'Git worktrees will be created from the origin repo.'
    if not is_clean_strict(repo):
        lines = ['Warning: the git working tree is not clean.']
        if options.worktree:
            lines.append(wts)
        lines.append('You probably want to commit and push before continuing. Continue?')
        decision = YNConfirm.ask(lines_to_text(options, lines), default=False)
        if not decision:
            sys.exit('Aborting due to unclean git working tree.')

    if has_unpushed_commits(repo):
        lines = ['Warning: there are unpushed commits.']
        if options.worktree:
            lines.append(wts)
        lines.append('You probably want to push before continuing. Continue?')
        decision = YNConfirm.ask(lines_to_text(options, lines), default=False)
        if not decision:
            sys.exit('Aborting due to unpushed commits.')


def is_clean_strict(repo: git.Repo) -> bool:
    """Clean including untracked files (default git status behavior)"""
    return is_working_tree_clean(repo, include_untracked=True)


def is_clean_no_untracked(repo: git.Repo) -> bool:
    """Clean ignoring untracked files (like git diff --quiet)"""
    return is_working_tree_clean(repo, include_untracked=False)


def is_working_tree_clean(repo: git.Repo, include_untracked: bool = True) -> bool:
    """
    Returns True if the working tree is clean (no changes, no untracked files by default).

    - include_untracked=False → ignores new/untracked files (like git status --untracked-files=no)
    """
    return not repo.is_dirty(untracked_files=include_untracked)


def has_unpushed_commits(repo: git.Repo) -> bool:
    """
    Returns True if the current branch has commits not pushed to its upstream
    (usually origin/<branch>).
    """
    try:
        origin = repo.remotes.origin
    except ValueError:
        console_stderr.print(f"No 'origin' remote found for: {repo.working_dir}")
        return False

    try:
        origin.fetch()
    except Exception as e:
        console_stderr.print(f'Fetch failed for remote "{origin.name}" at "{origin.url}": {e}')
        return False

    upstream = get_upstream_branch(repo)
    if upstream is None:
        return False

    # Count commits ahead of upstream
    ahead = sum(1 for _ in repo.iter_commits(f'{upstream.name}..HEAD'))
    return ahead > 0


def get_upstream_branch(repo: git.Repo) -> git.RemoteReference | None:
    if repo.head.is_detached:
        console_stderr.print('Detached HEAD — no current branch')
        return None

    branch = repo.active_branch
    tracking = branch.tracking_branch()
    if tracking is None:
        console_stderr.print(f'No upstream branch set for the {branch.name} branch')
        return None
    return tracking
