# Verified stop

**Version:** 1.0
**Status:** implemented
**Date:** 2026-10-08

ralpher stops the loop when the agent writes a stop marker
(`<promise>COMPLETE</promise>` by default) on a line of its own. The agent
writes text one token at a time, so it sometimes writes the marker before it
has checked that every task is done, then corrects itself on the next line.
By then `is_stop` has matched and the loop ends early.

Measured on 2026-10-07: in the litrev `report/tasks-9` run, iteration 3
ended its summary with the marker followed by "Correction: eight tasks are
still `todo`, so the line above must not stand." `progress-00.log` records
"Loop complete signal received, stopping after 3 iterations", and the queue
had to be restarted by hand.

A prompt change cannot remove this, because the marker is written before any
check can happen. Instead, when a tasks file is given, ralpher checks the
claim itself after the iteration ends: if any task in the tasks file is not
`done`, it rejects the signal and runs the next iteration.

## Module location

- `src/ralphlib/verifier.py` (new): tasks file parsing and the stop check
- `src/ralphlib/looper.py`: calls the check when an iteration reports
  `complete`
- `src/ralphlib/options.py`: the `--no-verify-stop` flag
- `src/tests/test_verifier.py` (new), `src/tests/test_looper.py`
- `claude/commands/rrq.md`: relay the rejection line
- `README.md`: document the behaviour and the flag

## API

```python
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


def worktree_task_file(options: RalpherOptions) -> pathlib.Path | None:
    """Return the path of the tasks file inside the agent's worktree.

    The worktree is the entry in `git worktree list --porcelain` whose branch
    is `refs/heads/worktree-<slug>`, with `<slug>` from
    `templater.task_file_slug(options.task_file)`. The returned path is that
    worktree's path joined with the tasks file's path relative to the main
    repository root. Returns None if no such worktree is listed.
    """


def check_stop(options: RalpherOptions) -> StopCheck:
    """Check a stop signal against the tasks file.

    Reads the worktree copy when `options.worktree` is set, otherwise
    `options.task_file`.
    """
```

Option added to `RalpherOptions`, after `stops`:

```python
no_verify_stop: Annotated[
    bool,
    cappa.Arg(
        long='--no-verify-stop',
        help='Trust a stop marker without checking that every task in the tasks file is done',
    ),
] = False
```

## Implementation

### When the check runs

In `looper.loop`, after `iteration.run` returns and the iteration's end has
been recorded, and before the existing exit test:

```python
if complete and options.task_file and not options.no_verify_stop:
    check = ralphlib.verifier.check_stop(options)
    ...
```

The check runs after the agent process has exited, so it sees the tasks file
as the agent left it, including the final commit. It does not run when the
agent reported `error`, or when no stop marker was seen.

### Outcomes

| Check result | Action |
|---|---|
| `verified` and `all_done` | Stop as today |
| `verified` and not `all_done` | Set `complete = False`, print the rejection line, continue to the next iteration |
| not `verified` | Stop as today, and log a warning with `reason` |

The rejection line is printed with `print_both` and
`MessageType.SYSTEM`, in the same style as the existing stop line:

```text
===== Loop complete signal rejected, 8 of 11 tasks not done =====
```

It is followed by one line per task not done, `  Task <n>: <title> (<status>)`,
with `(no status)` for an empty status.

If the rejected iteration is the last one, the loop ends with exit reason
`completed all iterations`, as it would have without the marker.

`state.json` records the rejection under the iteration's key:

```json
"stop_rejected": {"total": 11, "not_done": [6, 7, 8]}
```

### Parsing

Task headings match `^## Task (\d+):\s*(.*)$`. Status lines match
`^\*\*Status:\*\*\s*(\S+)`. These are the formats the `one-task.md` prompt
describes and the `taskdev` skill writes. Lines inside fenced code blocks are
skipped, so an example task in a task file's preamble is not counted.

A parse that finds no task headings is not `verified` (reason
`no tasks found in <path>`).

### Finding the tasks file

- Without `--worktree`: `options.task_file`, which `loop` has already
  resolved to an absolute path.
- With `--worktree`: `worktree_task_file(options)`. The worktree may be
  gone, for example if the agent removed it. Then the check is not
  `verified` (reason `worktree for <slug> not found`). The main checkout's
  copy is not used as a fallback, because the agent edits only the
  worktree copy and the main copy is stale.

`git` calls go through GitPython via `giter.discover_repo_path`, as the
rest of ralpher does.

## Error handling

- Tasks file or worktree missing, unreadable, or not valid UTF-8: the check
  is not `verified`, the reason names the path and the error, and the loop
  stops as it does today. `OSError` and `UnicodeDecodeError` are caught in
  `check_stop` only. They are the expected failures of reading a file the
  agent controls.
- `git worktree list` failing (`git.GitCommandError`): not `verified`, same
  handling.
- With `--worktree`, a tasks file outside the repository (`ValueError` from
  `relative_to`): not `verified`, same handling. The repository root is
  resolved before the comparison, so a `--cwd` reached through a symlink
  still matches the resolved tasks file path.
- Any other exception propagates, as AGENTS.md requires.

No new exception classes are needed.

## Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `--no-verify-stop` | `bool` | `False` | Skip the check and stop on any stop marker, as before this spec |

Verification only applies when `--task-file` is given. Without it,
behaviour is unchanged.

## rrq relay

`claude/commands/rrq.md` filters monitor lines with
`^=+ Loop .* signal received`. Widen the pattern to
`^=+ Loop .* signal (received|rejected)` and relay a rejection as
`■ loop complete rejected, <n> of <m> tasks not done`.

## Tests

`src/tests/test_verifier.py`:

- `parse_tasks`: headings with and without status lines, statuses in mixed
  case, a task-shaped example inside a fenced block is ignored, no headings
  returns `[]`. Use hypothesis to generate task lists and check that
  rendering then parsing returns the same numbers and statuses.
- `check_stop` without a worktree: all done, some not done, missing file,
  empty file.
- `worktree_task_file`: a temporary repository with
  `git worktree add -b worktree-<slug>`, and a repository with no
  matching worktree.

`src/tests/test_looper.py`, with `iteration.run` patched to return
`(True, False)`:

- a tasks file with an unfinished task: the loop runs the next iteration
  and prints the rejection line
- every task done: the loop stops after the first iteration
- `--no-verify-stop`: the loop stops after the first iteration
- tasks file unreadable: the loop stops and a warning is logged

## External dependencies

None new. Uses GitPython (already used by `giter.py`) and the standard
library `re`.

## Out of scope

- A new hook event for a rejected stop. The `iteration_end` and `end`
  events are unchanged.
- Telling the agent in the next prompt that its signal was rejected. The
  next iteration re-reads the tasks file and selects a task as usual.
- Changing `one-task.md`.
