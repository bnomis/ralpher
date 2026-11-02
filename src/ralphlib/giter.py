import contextlib
import json
import pathlib
import re
import sys
import typing

import git
import loguru
import rich.prompt
import rich.text

import ralphlib.exceptions
import ralphlib.printer
import ralphlib.types

if typing.TYPE_CHECKING:
    import ralphlib.options


class YNConfirm(rich.prompt.Confirm):
    def make_prompt(self, default: bool) -> rich.text.Text:  # type: ignore
        yes, no = ('Y', 'n') if default else ('y', 'N')
        prompt = self.prompt.copy()
        prompt.end = ''
        prompt.append(f' [{yes}/{no}] ')
        return prompt


def lines_to_text(options: ralphlib.options.RalpherOptions, lines: list[str]) -> rich.text.Text:
    return rich.text.Text(
        '\n'.join(lines),
        style=ralphlib.printer.type_to_style(options, ralphlib.types.MessageType.ALERT),
    )


def last_commit_summary(path: pathlib.Path | str | None = None) -> str:
    repo = discover_repo_path(path=path)
    if repo is None:
        return ''

    try:
        return str(repo.head.commit.summary)
    except git.GitCommandError, git.GitCommandNotFound, ValueError:
        loguru.logger.opt(exception=True).warning('Cannot read the last commit')
        return ''


def confirm_git_state(options: ralphlib.options.RalpherOptions, path: pathlib.Path | str | None = None) -> None:
    if options.skip_git_check:
        return

    repo = discover_repo_path(path=path)
    if repo is None:
        lines = ['Warning: not in a git repository.']
        decision = YNConfirm.ask(lines_to_text(options, lines), default=False)
        if not decision:
            sys.exit('Aborting due to not being in a git repository.')
        return

    confirm_repo_clean(options, repo)
    if options.worktree:
        confirm_divergence(options, repo)


def discover_repo_path(path: pathlib.Path | str | None = None) -> git.Repo | None:
    """
    Returns the path to the git repository if the given path (or current directory) is inside a git repository.

    Raises:
        GitError: the path cannot be opened.
    """
    try:
        path = pathlib.Path.cwd() if path is None else pathlib.Path(path)
        return git.Repo(str(path), search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        return None
    except OSError as e:
        raise ralphlib.exceptions.GitError(f'Cannot open the git repository at {path or "the current directory"}') from e


def opens_as_repo(path: pathlib.Path | str | None = None) -> bool:
    return discover_repo_path(path) is not None


def confirm_repo_clean(options: ralphlib.options.RalpherOptions, repo: git.Repo) -> None:
    from_head = options.worktree and worktree_base_ref(options, repo) == 'head'
    if from_head:
        wts = 'Git worktrees will be created from the local HEAD, without uncommitted changes.'
    else:
        wts = 'Git worktrees will be created from the origin repo.'
    if not working_tree_is_clean(repo, include_untracked=True):
        lines = ['Warning: the git working tree is not clean.']
        if options.worktree:
            lines.append(wts)
        lines.append('You probably want to commit and push before continuing. Continue?')
        decision = YNConfirm.ask(lines_to_text(options, lines), default=False)
        if not decision:
            sys.exit('Aborting due to unclean git working tree.')

    unpushed = None if from_head else fetch_unpushed_state(repo)
    if not from_head and unpushed is not False:
        if unpushed is None:
            lines = ['Warning: cannot tell whether there are unpushed commits.']
            advice = 'You probably want to check and push before continuing. Continue?'
            abort = 'Aborting: cannot tell whether there are unpushed commits.'
        else:
            lines = ['Warning: there are unpushed commits.']
            advice = 'You probably want to push before continuing. Continue?'
            abort = 'Aborting due to unpushed commits.'
        if options.worktree:
            lines.append(wts)
        lines.append(advice)
        decision = YNConfirm.ask(lines_to_text(options, lines), default=False)
        if not decision:
            sys.exit(abort)


def working_tree_is_clean(repo: git.Repo, include_untracked: bool = True) -> bool:
    """
    Returns True if the working tree is clean (no changes, no untracked files by default).

    - include_untracked=False → ignores new/untracked files (like git status --untracked-files=no)

    Raises:
        GitError: the status cannot be read.
    """
    try:
        return not repo.is_dirty(untracked_files=include_untracked)
    except (git.GitCommandError, git.GitCommandNotFound, OSError) as e:
        raise ralphlib.exceptions.GitError(f'Cannot read the git status of {repo.working_dir}') from e


def redact_url(text: str) -> str:
    """Return text with the user-info (credentials) removed from every scheme://user:pw@host URL in it."""
    return re.sub(r'([a-zA-Z][a-zA-Z0-9+.-]*://)[^/@\s]*@', r'\1', text)


def fetch_unpushed_state(repo: git.Repo) -> bool | None:
    """
    Returns True if the current branch has commits not pushed to its upstream
    (usually origin/<branch>), False if it has none, and None if that cannot be
    told: no origin remote, a failed fetch, a detached HEAD or no upstream.

    Raises:
        GitError: the upstream branch or its commits cannot be read.
    """
    try:
        origin = repo.remotes.origin
    except AttributeError, ValueError, OSError:
        ralphlib.printer.console_stderr.print(f"No 'origin' remote found for: {repo.working_dir}")
        return None

    try:
        origin.fetch()
    except (git.GitCommandError, git.GitCommandNotFound, OSError, UnicodeDecodeError) as e:
        # auditme: accept[except-interpolation] the message goes to the console, which shows no traceback
        message = redact_url(f'Fetch failed for remote "{origin.name}" at "{origin.url}": {e}')
        ralphlib.printer.console_stderr.print(message)
        loguru.logger.warning(message)
        return None

    upstream = read_upstream_branch(repo)
    if upstream is None:
        return None

    # Count commits ahead of upstream
    try:
        ahead = sum(1 for _ in repo.iter_commits(f'{upstream.name}..HEAD'))
    except (git.GitCommandError, git.GitCommandNotFound, OSError) as e:
        raise ralphlib.exceptions.GitError(f'Cannot list the commits ahead of {upstream.name}') from e
    return ahead > 0


def read_upstream_branch(repo: git.Repo) -> git.RemoteReference | None:
    try:
        if repo.head.is_detached:
            ralphlib.printer.console_stderr.print('Detached HEAD — no current branch')
            return None

        branch = repo.active_branch
        tracking = branch.tracking_branch()
    except (git.GitCommandError, OSError) as e:
        raise ralphlib.exceptions.GitError(f'Cannot read the upstream branch of {repo.working_dir}') from e
    if tracking is None:
        ralphlib.printer.console_stderr.print(f'No upstream branch set for the {branch.name} branch')
        return None
    return tracking


def confirm_divergence(options: ralphlib.options.RalpherOptions, repo: git.Repo) -> None:
    if worktree_base_ref(options, repo) != 'fresh':
        return

    base, base_short = read_origin(repo)
    if not base:
        ralphlib.printer.console_stderr.print('Warning: origin/HEAD is not set locally. Cannot check for divergence.')
        return

    current = read_current_branch(repo)
    if not current:
        ralphlib.printer.console_stderr.print('Warning: HEAD is detached. Cannot check for divergence.')
        return

    if base_short != current:
        lines = ['Warning: the git worktree will diverge from the current branch.']
        lines.append(f'You probably want to: "git remote set-head origin {current}" before continuing. Exit now?')
        decision = YNConfirm.ask(lines_to_text(options, lines), default=True)
        if decision:
            sys.exit('Aborting due to divergence.')


def read_origin(repo: git.Repo) -> tuple[str | None, str | None]:
    # Where origin/HEAD points — the base Claude Code will branch new worktrees from
    try:
        origin_head = repo.remotes.origin.refs.HEAD.reference  # e.g. origin/master
        base = origin_head.name  # "origin/master"
        base_short = base.split('/', 1)[1]  # "master"
    except AttributeError, TypeError, OSError:
        # origin/HEAD not set locally
        base = base_short = None
    return base, base_short


def read_current_branch(repo: git.Repo) -> str | None:
    try:
        if repo.head.is_detached:
            return None
        return repo.active_branch.name
    except (git.GitCommandError, OSError) as e:
        raise ralphlib.exceptions.GitError(f'Cannot read the current branch of {repo.working_dir}') from e


def worktree_base_ref(options: ralphlib.options.RalpherOptions, repo: git.Repo) -> str:
    """The ref the agent's worktrees branch from: `--worktree-base-ref` if passed, else Claude Code's settings."""
    return options.worktree_base_ref or claude_worktree_base_ref(repo)


def claude_worktree_base_ref(repo: git.Repo) -> str:
    """
    The ref Claude Code branches new worktrees from: the `worktree.baseRef` setting, or its default "fresh".
    "fresh" branches from origin/<default-branch>, "head" from the local HEAD.
    """
    base_ref = 'fresh'
    for path in claude_settings_paths(repo):
        with contextlib.suppress(OSError, ValueError):
            settings = json.loads(path.read_text())
            worktree = settings.get('worktree') if isinstance(settings, dict) else None
            if isinstance(worktree, dict) and 'baseRef' in worktree:
                base_ref = worktree['baseRef']
    return base_ref


def claude_settings_paths(repo: git.Repo) -> list[pathlib.Path]:
    """Claude Code settings files, lowest precedence first."""
    paths = [pathlib.Path.home() / '.claude' / 'settings.json']
    if repo.working_tree_dir is not None:
        project = pathlib.Path(repo.working_tree_dir) / '.claude'
        paths += [project / 'settings.json', project / 'settings.local.json']

    managed_dir = {
        'darwin': pathlib.Path('/Library/Application Support/ClaudeCode'),
        'win32': pathlib.Path('C:/Program Files/ClaudeCode'),
    }.get(sys.platform, pathlib.Path('/etc/claude-code'))
    paths.append(managed_dir / 'managed-settings.json')
    paths += sorted((managed_dir / 'managed-settings.d').glob('[!.]*.json'))
    return paths
