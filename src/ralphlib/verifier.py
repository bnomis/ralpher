import dataclasses
import pathlib
import re
import typing

import git

import ralphlib.exceptions
import ralphlib.giter
import ralphlib.templater

if typing.TYPE_CHECKING:
    import ralphlib.options

HEADING = re.compile(r'^## Task (\d+):\s*(.*)$')
STATUS = re.compile(r'^\*\*Status:\*\*\s*(\S+)')
FENCES = ('```', '~~~')
READ_ERRORS = (ralphlib.exceptions.TasksFileError, OSError, UnicodeDecodeError, ValueError, git.GitCommandError)


@dataclasses.dataclass
class TaskStatus:
    number: int
    title: str
    status: str


@dataclasses.dataclass
class StopCheck:
    verified: bool
    """True when the tasks file was read and parsed; False when the check could not be made."""
    all_done: bool
    """True when every parsed task has status `done`. Meaningless when `verified` is False."""
    not_done: list[TaskStatus]
    total: int
    reason: str
    """Why the check could not be made, empty when `verified` is True."""


def parse_tasks(text: str) -> list[TaskStatus]:
    """Return one TaskStatus per `## Task <n>: <title>` heading, in file order.

    The status is the value of the first `**Status:** <value>` line after the
    heading and before the next heading, lowercased and stripped. A task
    with no status line gets status `''`, which counts as not done.
    """
    tasks: list[TaskStatus] = []
    fence = ''
    current: TaskStatus | None = None
    for line in text.splitlines():
        marker = next((f for f in FENCES if line.startswith(f)), '')
        if fence:
            if marker == fence:
                fence = ''
            continue
        if marker:
            fence = marker
            continue
        if line.startswith('## '):
            match = HEADING.match(line)
            current = TaskStatus(int(match.group(1)), match.group(2).strip(), '') if match else None
            if current:
                tasks.append(current)
            continue
        if current and not current.status:
            match = STATUS.match(line)
            if match:
                current.status = match.group(1).strip().lower()
    return tasks


def parse_worktrees(porcelain: str) -> list[tuple[pathlib.Path, str]]:
    """Return `(worktree path, branch)` for each `worktree list --porcelain` entry that has a branch."""
    worktrees: list[tuple[pathlib.Path, str]] = []
    path: pathlib.Path | None = None
    for line in porcelain.splitlines():
        if line.startswith('worktree '):
            path = pathlib.Path(line.removeprefix('worktree '))
        elif line.startswith('branch ') and path is not None:
            worktrees.append((path, line.removeprefix('branch ')))
    return worktrees


def worktree_task_file(options: ralphlib.options.RalpherOptions) -> pathlib.Path | None:
    """Return the path of the tasks file inside the agent's worktree.

    The worktree is the entry whose branch is `refs/heads/worktree-<slug>`.
    Returns None if there is no repository or no such worktree. A path found
    is cached on `options.worktree_task_path`; `iteration.make_context` clears it.
    `git.GitCommandError` propagates, and `ValueError` when the tasks file
    is outside the repository.
    """
    if options.worktree_task_path is not None:
        return options.worktree_task_path
    repo = ralphlib.giter.discover_repo_path(options.cwd)
    if repo is None or repo.working_tree_dir is None or not options.task_file:
        return None

    branch = f'refs/heads/worktree-{ralphlib.templater.task_file_slug(options.task_file)}'
    task_file = pathlib.Path(options.task_file)
    if task_file.is_absolute():
        task_file = task_file.relative_to(pathlib.Path(repo.working_tree_dir).resolve())
    for path, entry_branch in parse_worktrees(repo.git.worktree('list', '--porcelain')):
        if entry_branch == branch:
            options.worktree_task_path = path / task_file
            return options.worktree_task_path
    return None


def agent_task_file(options: ralphlib.options.RalpherOptions) -> pathlib.Path:
    """Return the tasks file the agent edits: the worktree copy when `options.worktree` is set, otherwise `options.task_file`.

    Raises:
        TasksFileError: the worktree does not exist.
        git.GitCommandError, ValueError: as `worktree_task_file` does.
    """
    if not options.worktree:
        return pathlib.Path(options.task_file)
    path = worktree_task_file(options)
    if path is None:
        raise ralphlib.exceptions.TasksFileError(f'worktree for {ralphlib.templater.task_file_slug(options.task_file)} not found')
    return path


def read_tasks(options: ralphlib.options.RalpherOptions) -> list[TaskStatus]:
    """Parse the tasks file the agent edits. Raises the errors in `READ_ERRORS`."""
    return parse_tasks(agent_task_file(options).read_text())


def check_stop(options: ralphlib.options.RalpherOptions) -> StopCheck:
    """Check a stop signal against the tasks file the agent edits."""
    try:
        path = agent_task_file(options)
        tasks = parse_tasks(path.read_text())
    except ralphlib.exceptions.TasksFileError as e:
        return unverified(str(e))
    except READ_ERRORS as e:
        # auditme: accept[except-interpolation] the text is the stop-check reason, which shows no traceback
        return unverified(f'cannot read {options.task_file}: {e!r}')

    if not tasks:
        return unverified(f'no tasks found in {path}')
    not_done = [t for t in tasks if t.status != 'done']
    return StopCheck(verified=True, all_done=not not_done, not_done=not_done, total=len(tasks), reason='')


def unverified(reason: str) -> StopCheck:
    return StopCheck(verified=False, all_done=False, not_done=[], total=0, reason=reason)
