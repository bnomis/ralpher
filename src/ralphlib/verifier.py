import dataclasses
import pathlib
import re
from typing import TYPE_CHECKING

import ralphlib.giter
import ralphlib.templater

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions

HEADING = re.compile(r'^## Task (\d+):\s*(.*)$')
STATUS = re.compile(r'^\*\*Status:\*\*\s*(\S+)')
FENCES = ('```', '~~~')


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


def worktree_task_file(options: RalpherOptions) -> pathlib.Path | None:
    """Return the path of the tasks file inside the agent's worktree.

    The worktree is the entry whose branch is `refs/heads/worktree-<slug>`.
    Returns None if there is no repository or no such worktree.
    `git.GitCommandError` propagates.
    """
    repo = ralphlib.giter.discover_repo_path(options.cwd)
    if repo is None or repo.working_tree_dir is None or not options.task_file:
        return None

    branch = f'refs/heads/worktree-{ralphlib.templater.task_file_slug(options.task_file)}'
    task_file = pathlib.Path(options.task_file)
    if task_file.is_absolute():
        task_file = task_file.relative_to(repo.working_tree_dir)
    for path, entry_branch in parse_worktrees(repo.git.worktree('list', '--porcelain')):
        if entry_branch == branch:
            return path / task_file
    return None
