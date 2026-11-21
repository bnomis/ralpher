# Verified stop

**Version:** 1.0
**Status:** implemented
**Date:** 2026-10-08

ralpher stops the loop when the agent writes a stop marker
(`<promise>COMPLETE</promise>` by default) on a line of its own. The agent
writes text one token at a time, so it sometimes writes the marker before it
has checked that every task is done, then corrects itself on the next line.
By then `is_stop` has matched and the loop ends early.

Measured on 2026-10-07: in another project's `report/tasks-9` run, iteration 3
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
- `claude/commands/rrq.md`: widen the monitor filter to `^=+ Loop .* signal (received|rejected)` and relay a rejection as `■ loop complete rejected, <n> of <m> tasks not done`
- `docs/guide/tasks.md` and `docs/reference/cli.md`: document the behaviour and the flag

## API

No new dependencies: the module uses GitPython (as `giter.py` does) and `re`.

```python
class TasksFileError(RalpherError):
    """Raised, in `ralphlib/exceptions.py`, when the tasks file the agent edits cannot be located."""


@dataclasses.dataclass
class TaskStatus:
    number: int
    title: str
    status: str


@dataclasses.dataclass
class StopCheck:
    verified: bool  # False when the check could not be made
    all_done: bool  # every parsed task is `done`; meaningless when not verified
    not_done: list[TaskStatus]
    total: int
    reason: str  # why the check could not be made


READ_ERRORS = (OSError, UnicodeDecodeError, ValueError, git.GitCommandError, TasksFileError)
"""The expected failures of reading a file the agent controls."""


def parse_tasks(text: str) -> list[TaskStatus]:
    """Return one TaskStatus per `## Task <n>: <title>` heading, in file order.

    The status is the value of the first `**Status:** <value>` line after the
    heading and before the next heading, lowercased. A task with no status
    line gets status `''`, which counts as not done.
    """


def parse_worktrees(porcelain: str) -> list[tuple[pathlib.Path, str]]:
    """Return `(worktree path, branch)` for each worktree-list porcelain entry with a branch."""


def worktree_task_file(options: RalpherOptions) -> pathlib.Path | None:
    """Return the tasks file's path inside the worktree on branch `refs/heads/worktree-<slug>`.

    `<slug>` comes from `templater.task_file_slug(options.task_file)`. Returns
    None if there is no repository or no such worktree. A path found is cached
    on `options.worktree_task_path`, which `iteration.make_context` clears.
    """


def agent_task_file(options: RalpherOptions) -> pathlib.Path:
    """Return the tasks file the agent edits: the worktree copy with `options.worktree`, else `options.task_file`.

    Raises TasksFileError if the worktree does not exist.
    """


def read_tasks(options: RalpherOptions) -> list[TaskStatus]:
    """Parse the tasks file the agent edits. Raises the errors in READ_ERRORS."""


def verify_stop(options: RalpherOptions) -> StopCheck:
    """Check a stop signal against the tasks file the agent edits."""
```

`RalpherOptions.worktree_task_path` (`pathlib.Path | None`, set at run time)
caches the worktree lookup.

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

Verification only applies when `--task-file` is given, and `--no-verify-stop`
skips it, so the loop stops on any stop marker as before this spec.

In `looper.loop`, after `iteration.run` returns and the iteration's end has
been recorded, and before the existing exit test:

```python
if complete and options.task_file and not options.no_verify_stop:
    check = ralphlib.verifier.verify_stop(options)
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

## Error handling

- Tasks file or worktree missing, unreadable, or not valid UTF-8: the check
  is not `verified`, the reason names the tasks file option
  (`options.task_file`, not the worktree path that was read) and the error
  (for a missing worktree, the `TasksFileError` text
  `worktree for <slug> not found`),
  and the loop stops as it does today. `verifier.READ_ERRORS` (`OSError`,
  `UnicodeDecodeError`, `ValueError`, `git.GitCommandError` and
  `TasksFileError`) are caught in `verify_stop` and where `iteration.py`
  reads the tasks file for progress. They are the expected failures of
  reading a file the agent controls.
- `git worktree list` failing (`git.GitCommandError`): not `verified`, same
  handling.
- With `--worktree`, a tasks file outside the repository (`ValueError` from
  `relative_to`): not `verified`, same handling. The repository root is
  resolved before the comparison, so a `--cwd` reached through a symlink
  still matches the resolved tasks file path.
- Any other exception propagates, as AGENTS.md requires.

## Tests

`src/tests/test_verifier.py`: `parse_tasks` (headings with and without
status lines, mixed case, a fenced example ignored, no headings; a hypothesis
render-then-parse round trip), `verify_stop` without a worktree (all done,
some not done, missing file, empty file), and `worktree_task_file` against a
temporary repository with and without a matching worktree.

`src/tests/test_looper.py`, with `iteration.run` patched to return
`(True, False)`: an unfinished task runs the next iteration and prints the
rejection line; every task done, `--no-verify-stop` and an unreadable tasks
file each stop after the first iteration (the last also logs a warning).

## External dependencies

- GitPython (`git`), already used by `giter.py`, for `git worktree list`.
- `re`, from the standard library, for the task heading and status patterns.

## Out of scope

- A new hook event for a rejected stop. The `iteration_end` and `end`
  events are unchanged.
- Telling the agent in the next prompt that its signal was rejected. The
  next iteration re-reads the tasks file and selects a task as usual.
- Changing `one-task.md`.
