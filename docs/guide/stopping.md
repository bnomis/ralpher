# Stopping a run

## From the keyboard

| Action | Effect |
|--------|--------|
| Ctrl+C once | a warning: press again within 3 seconds to exit |
| Ctrl+C twice within 3 seconds | graceful shutdown |
| `SIGTERM` | graceful shutdown |
| any of these during a shutdown | immediate exit, status 1 |

A graceful shutdown sends `SIGTERM` to the agent's process group, so the
agent's own children (test runners, servers) stop too, retrying up to three
times. The current iteration ends, `iteration_end` and `end` hooks run, the
state file is completed, and ralpher exits with status 1 and exit reason
`termination`.

The agent may have been mid-edit. With `--worktree` your checkout is
untouched; inspect the worktree before rerunning.

## Stops the agent asks for

| Cause | Stopping reason | Next prompt printed |
|-------|-----------------|---------------------|
| an `operator` task block | `Operator input required for task <n>` | `unblock task <n> in [worktree ]task file <path>` |
| the same `blocked` task block a third time | `Loop detected for task <n> with status blocked` | the same |

Both stop the agent within a few seconds of the block, and end the run as a
termination. The next prompt is meant for an interactive agent session in
the same repository: it names the task and the tasks file the agent was
editing (the worktree copy with `--worktree`).

## Errors

An agent `result` message flagged `is_error` (out of usage, an API error)
stops the agent and ends the run with exit reason `error`. The `error` hook
runs, then `end`.

An agent that exits with a non-zero status before writing anything to stdout,
as when it refuses its arguments, also ends the run with exit reason `error`
and status 1: every later iteration would pass the same arguments and fail
the same way. ralpher logs `The agent exited with code <n> without any
output; stopping the loop`, and the agent's own message is in the stderr log.
An exit after a termination signal does not count.

An exception inside ralpher during an iteration is logged, and ends the run
as an error with exit reason `exception during iteration <n>` and status 1.
The `error` hook runs, then `end`; `iteration_end` does not run for that
iteration.

## Ending without stopping

A run that uses every iteration without a stop marker exits with status 0
and exit reason `completed all iterations`. Check the tasks file, or the
progress file, to see how far it got; rerun to continue.
