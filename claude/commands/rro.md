Run a whole order of task lists from one order file: each list is merged
before the next starts, a slower whole-project check runs at checkpoints, and
the stops you decided are reviewed by the operator in batches.

Invoke as `/rro <order file>`. The order file is the only state: everything
a script can decide is decided by `bin/rro.sh`, so never read or edit a
table by hand. Every call prints one line of JSON; on an error it prints
`{"error": "<class>", "message": "..."}` and exits 2. Quote the message to
the operator and stop. Run the script as `"$RALPHER_PATH/bin/rro.sh"`.

Report each event to the operator in the relay format of `rrq.md` (`▶`
start, `✓` done, `✗` blocked, `?` needs the operator), one short line each.
A claim about the state of a repository, a process or the order carries the
time of the check it comes from (run `date -u +%H:%M:%S` with the check).

## Start

1. Check, from the main checkout (not a worktree): it is on the default
   branch, the tree is clean, and it is level with its remote
   (`git status -sb`). If not, stop and say which.
2. Run `bin/rro.sh next <order>`. An `OrderFormatError` or a
   `WaitsForUnmetError` stops the order before anything runs: quote it and
   name the row it concerns. Never skip over a row, since the table order is
   the operator's.
3. Publish the progress page (see Progress page) if the `progress page`
   setting is empty.

Then act on the step `next` returned: `RunList` (A list), `RunCheckpoint`
(A checkpoint), `Resume` (Resume) or `Finished` (Finish). After each list or
checkpoint, run `next` again and act on the new step.

## A list

1. `bin/rro.sh set-status <order> <label> running`, commit the order file
   and push it.
2. Run the list exactly as `/rrq --decide <spec> <index>` does: follow the
   steps in `rrq.md` (background run, monitor, relayed lines, deciding
   operator stops, and the `Queue-decision:` trailer on every decided stop)
   rather than any copy here.
3. A stop named in the row's `Stops for you` cell, or in a rule file listed
   in the `always wait for` setting, is never decided: run
   `bin/rro.sh set-status <order> <label> "waiting: <the stop>"`, commit the
   order file, ask the operator, and wait. Anything else `rrq.md` says to
   wait for waits as well.
4. Update the progress page at the list's start and at every stop.

## Merge

When the queue reports every task done, check in this order, stopping at the
first that fails:

1. Every task in the list's tasks file has status `done`.
2. `bin/rro.sh check-log <order> <label>` returns `"passed": true`.
   On a failure (a missing log, no pass line, or a fail-pattern match), do
   not merge. If the log names failing test directories, rerun those
   serially from the list's worktree; merge only if they pass, and record
   that in the status (`merged <hash>, after serial rerun`). Otherwise run
   `bin/rro.sh set-status <order> <label> "waiting: test gate"`, commit the
   order file, report the `fail_lines`, and stop for the operator.
3. `git merge --no-ff` the list's branch into the default branch.
4. `pre-commit run --all-files --hook-stage pre-push`.
5. Push the default branch.
6. Remove the list's worktree and branch.
7. `bin/rro.sh set-status <order> <label> "merged <short hash>"`, commit
   the order file and push it.

A merge conflict, a rejected push or a failing pre-push hook stops the order:
report it. Never force-push, never use `--no-verify`.

Update the progress page, then take the next step.

## A checkpoint

1. Run only one test run on the machine at a time, as the project's own
   rules say: wait for any other to finish first.
2. Run the `checkpoint command` setting in the background from the main
   checkout, on the default branch, and wait for it to exit.
3. On a pass, `bin/rro.sh set-status <order> <label> "passed <counts>"`,
   where `<label>` is the `label` of the `RunCheckpoint` step that `next`
   returned, passed unchanged: never build one.
   On a failure, set `failed <counts>` with the same label, list the lists merged since the last
   passing checkpoint, newest first, as the suspects, report them and stop.
   Commit and push the order file either way.
4. After a pass, run `bin/rro.sh decisions <order> --since <the previous
   checkpoint's commit>` (the order's first commit for the first checkpoint).
   If it lists any, write the batch review document
   `agents/reviews/queue-decisions-<n>.md` with one item per decision, each
   with a recommendation and its one-line reason. Publish its page as the
   shared reviews rule requires: approve or flag each item, an accept-all
   button, and answers saved to the artifact database as they are clicked.
   Put the page's URL in the document's header, commit it, and give the URL
   to the operator.
5. Go on to the next list without waiting for the answers. When the operator
   says the page is answered, copy the answers into the document's Answers
   section, dated, and commit it.

If the Artifact tool is not available, write the document, say that no page
was published, and go on.

## Progress page

Publish one page per order at the start, built from
`$RALPHER_PATH/claude/templates/order-progress.html`: copy it once into the
scratchpad, set its `<title>`, and on every update rewrite only the block
between its `DATA START` and `DATA END` markers, so the layout stays the
template's. Build the data from the order file (`bin/rro.sh next` and the
table's rows), never from memory:

- `SEQ`, `STATUS` and `CKSTATUS`: each row's label, list, task count,
  waits-for, stops for the operator and status, and each checkpoint's result;
  each entry is `[code, text]`, and the page colours only the codes its
  template styles: `done` (green) or `fail` (red) for a list or checkpoint,
  `run` while one is going; any other code, such as `passed`, shows uncoloured;
- `RUN`, for the list now running (else `null`): every task's title and
  status from its tasks file in the list's worktree, and the time each
  finished from that task's commit (`git log --format='%cI %s' <default
  branch>..<list branch>`); a stop shows as `stop`;
- `ORDER.pace`: each merged list's task count and wall-clock minutes from its
  start to its merge, which the page averages for its list and order ETAs;
  `ORDER.checkpointMinutes`, the last checkpoint's run time;
- `ORDER.updated` and the `meta` line: the time of the check the data comes
  from.

Republish it at every list start, task start and finish, stop, merge and
checkpoint. A task line from the queue's monitor is two actions in the same
turn: relay the line, then rebuild `RUN` and `STATUS` from the tasks file and
the list's commits and republish. Relaying the line alone leaves the page
showing the first task running while the queue is several tasks on. On the first publish, write its URL with
`bin/rro.sh set-setting <order> "progress page" <url>`, then commit and push. The file stays the record; the
page never disagrees with it.

## Resume

The order file is the state. A new session given the same file continues
from `bin/rro.sh next`:

- `Resume` of a `running` list: check whether its queue is still running
  (`ps -o comm=`, by name, never `pkill -f`). If not, run `/rrq --decide` on
  it again as `rrq.md` does.
- `Resume` of a `waiting: ...` row: ask the operator about the stop it
  names, then continue.
- `Resume` of a `failed` checkpoint: tell the operator and wait.
- `Resume` of a checkpoint row that is `running`: run the checkpoint again,
  and set its status with the `label` the `Resume` step carries, unchanged.

## Finish

When `next` returns `Finished`, report the merged lists, the checkpoints and
their counts, and the decisions still awaiting review, with the batch review
pages' URLs. State what was last checked and when.
