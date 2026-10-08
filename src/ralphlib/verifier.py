import dataclasses
import re

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
