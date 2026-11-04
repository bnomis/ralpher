# Running an order of task lists

A large piece of work is often several task lists that must run in a set
order. An order file names those lists, says which must be merged before
another may start, and holds the settings for a slower whole-project check
(a checkpoint) that runs every few lists. `/rro` runs the whole order from
that file: each list is merged before the next starts, and the stops the
session decided along the way are gathered into a batch review for you.

The order file is the only state. A new session given the same file carries on
where the last one stopped.

## An example order

Save this as `agents/tasks/order-example.md`. Text outside the two tables is
kept as written.

```markdown
# Order: example

| Setting | Value |
|---|---|
| checkpoint command | `make test-slow` |
| checkpoint every | 3 |
| test log | `ralpher-logs/{spec}/tasks-{index}/final-tests.log` |
| test pass line | `all selected test directories passed` |
| test fail pattern | `FAILED` |
| always wait for | `claude/rules/queue-stops.md` |
| progress page | |

| # | Task list | Waits for | Stops for you | Status |
|---|---|---|---|---|
| 1 | `parser/tasks-1.md` | - | - | todo |
| 2 | `lexicon/tasks-1.md` | - | the verdicts on the new entries (Task 3) | todo |
| | **Checkpoint** | | | todo |
| 3 | `report/tasks-2.md` | 1 | - | todo |
| | **Final checkpoint** | | | todo |
```

Run it from the main checkout, on the default branch, with a clean tree that
is level with its remote:

```text
/rro agents/tasks/order-example.md
```

The same file is `agents/tasks/run-order/example-order.md` in ralpher's
checkout, which the tests read.

## The order table

| Column | Meaning |
|---|---|
| `#` | A label without spaces (`3a` is allowed). Labels are unique. |
| `Task list` | A path under `agents/tasks/`, as `<spec>/tasks-<index>.md`. It must exist. |
| `Waits for` | `-`, or labels separated by commas. Each must be merged before the row may start. |
| `Stops for you` | Free text naming the stops that always wait for you in that list. `-` means none beyond the `always wait for` rule files. |
| `Status` | Written by `/rro` only: `todo`, `running`, `waiting: <what>`, `merged <short hash>`, and for a checkpoint `passed <counts>` or `failed <counts>`. |

A `**Checkpoint**` row may be written by hand. Where the table has none,
`/rro` runs one after every `checkpoint every` merged lists and after the last.
A `**Final checkpoint**` row ends the order.

Rows run in table order. A row that waits for an unmerged row is an error, not
something to skip: the table order is yours.

## Settings

An order file with no settings table, or without a required setting, is an
error before anything runs.

| Setting | Default | Trade-off |
|---|---|---|
| `checkpoint command` | required | Run from the main checkout on the default branch, in the background. Use your slowest whole-project test command; the per-list gate covers the rest. |
| `checkpoint every` | `3` | Lists merged between checkpoints when the table has no checkpoint rows. A smaller number finds a regression sooner and names fewer suspect lists, at the cost of more slow runs. |
| `test log` | `ralpher-logs/{spec}/tasks-{index}/final-tests.log` | Path, relative to the main checkout, where a list's last task saves its final test output. `{spec}` and `{index}` are filled per list. |
| `test pass line` | required | A line the log must contain for the run to count as passed. Choose one only a complete, successful run prints. |
| `test fail pattern` | `FAILED` | Regular expression; any match in the log fails the gate. |
| `always wait for` | empty | Comma-separated rule files whose listed stops are never decided, in addition to `/rrq`'s own exceptions. |
| `progress page` | empty | Artifact URL of the progress page. `/rro` fills it in when it first publishes one. |

## What `/rro` does

1. **Start.** Checks it is in the main checkout on the default branch, clean
   and level with its remote, then asks `bin/rro.py next` for the next step.
   A malformed order file or an unmet `Waits for` stops here, before anything
   runs.
2. **A list.** Sets the row to `running`, commits the order file, and runs the
   list as `/rrq --decide <spec> <index>` does. The stops `/rrq --decide`
   settles carry a `Queue-decision:` trailer in their commit.
3. **Merge.** When every task is `done`, checks the saved test log, then
   merges with `--no-ff`, runs the pre-push hooks, pushes, removes the list's
   worktree and branch, and sets `merged <hash>`. It never forces and never
   skips hooks.
4. **A checkpoint.** Runs the `checkpoint command` in the background, one test
   run on the machine at a time. On a pass it sets `passed <counts>`, writes
   the batch review `agents/reviews/queue-decisions-<n>.md` from the decisions
   since the previous checkpoint, publishes its page, and goes on to the next
   list without waiting for your answers.
5. **Progress page.** One page per order, rebuilt from the order file at every
   list start, stop, merge and checkpoint.
6. **Finish.** After the final checkpoint, reports the merged lists, the
   checkpoints and the decisions awaiting review.

Without the Artifact tool, `/rro` writes the review document, says no page was
published, and carries on.

## What stops for you

- A stop named in a row's `Stops for you` cell or in an `always wait for` rule
  file. The row becomes `waiting: <the stop>`.
- A failed test gate: a missing log, no pass line, or a fail-pattern match. If
  the log names failing directories, `/rro` reruns them serially and merges
  only if they pass; otherwise the row becomes `waiting: test gate`.
- A merge conflict, a rejected push or a failing pre-push hook.
- A failed checkpoint. The row becomes `failed <counts>`, and the lists merged
  since the last passing checkpoint are reported, newest first, as the
  suspects.

## The last task saves the test log

The merge gate reads the log at the `test log` path; it does not rerun the
tests. So the last task of every list in an order must save its final test
output there. The shared task-list skill is meant to do this; until it does,
write the path into the last task of each list by hand.

## Resuming

The order file is the state. After a lost session, run `/rro` with the same
file:

- a `running` list: the session checks whether its queue is still running and,
  if not, runs it again;
- a `waiting: ...` row: it asks you about the stop the row names;
- a `failed` checkpoint: it tells you and waits.

## The script

`/rro` calls `bin/rro.py`, which prints one line of JSON per call:

```shell
bin/rro.py next agents/tasks/order-example.md
bin/rro.py check-log agents/tasks/order-example.md 1
bin/rro.py set-status agents/tasks/order-example.md 1 running
bin/rro.py decisions agents/tasks/order-example.md --since <ref>
```

An expected error prints `{"error": "<class>", "message": "..."}` and exits 2.
The command is installed by `bin/install-claude.py` beside `/rrq`.
