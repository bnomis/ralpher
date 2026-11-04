Run a whole order of task lists from one order file: each list is merged
before the next starts, a slower whole-project check runs at checkpoints, and
the stops you decided are reviewed by the operator in batches.

Invoke as `/rro <order file>`. The order file is the only state: everything
a script can decide is decided by `bin/rro.py`, so never read or edit a
table by hand. Every call prints one line of JSON; on an error it prints
`{"error": "<class>", "message": "..."}` and exits 2. Quote the message to
the operator and stop. Run the script as `"$RALPHER_PATH/bin/rro.py"`.

Report each event to the operator in the relay format of `rrq.md` (`▶`
start, `✓` done, `✗` blocked, `?` needs the operator), one short line each.
A claim about the state of a repository, a process or the order carries the
time of the check it comes from (run `date -u +%H:%M:%S` with the check).

## Start

1. Check, from the main checkout (not a worktree): it is on the default
   branch, the tree is clean, and it is level with its remote
   (`git status -sb`). If not, stop and say which.
2. Run `bin/rro.py next <order>`. An `OrderFormatError` or a
   `WaitsForUnmetError` stops the order before anything runs: quote it and
   name the row it concerns. Never skip over a row, since the table order is
   the operator's.
3. Publish the progress page (see Progress page) if the `progress page`
   setting is empty.

Then act on the step `next` returned: `RunList` (A list), `RunCheckpoint`
(A checkpoint), `Resume` (Resume) or `Finished` (Finish). After each list or
checkpoint, run `next` again and act on the new step.

## A list

1. `bin/rro.py set-status <order> <label> running`, commit the order file
   and push it.
2. Run the list exactly as `/rrq --decide <spec> <index>` does: follow the
   steps in `rrq.md` (background run, monitor, relayed lines, deciding
   operator stops, and the `Queue-decision:` trailer on every decided stop)
   rather than any copy here.
3. A stop named in the row's `Stops for you` cell, or in a rule file listed
   in the `always wait for` setting, is never decided: run
   `bin/rro.py set-status <order> <label> "waiting: <the stop>"`, commit the
   order file, ask the operator, and wait. Anything else `rrq.md` says to
   wait for waits as well.
4. Update the progress page at the list's start and at every stop.

## Merge

When the queue reports every task done, check in this order, stopping at the
first that fails:

1. Every task in the list's tasks file has status `done`.
2. `bin/rro.py check-log <order> <label>` returns `"passed": true`.
   On a failure (a missing log, no pass line, or a fail-pattern match), do
   not merge. If the log names failing test directories, rerun those
   serially from the list's worktree; merge only if they pass, and record
   that in the status (`merged <hash>, after serial rerun`). Otherwise run
   `bin/rro.py set-status <order> <label> "waiting: test gate"`, commit the
   order file, report the `fail_lines`, and stop for the operator.
3. `git merge --no-ff` the list's branch into the default branch.
4. `pre-commit run --all-files --hook-stage pre-push`.
5. Push the default branch.
6. Remove the list's worktree and branch.
7. `bin/rro.py set-status <order> <label> "merged <short hash>"`, commit
   the order file and push it.

A merge conflict, a rejected push or a failing pre-push hook stops the order:
report it. Never force-push, never use `--no-verify`.

Update the progress page, then take the next step.

## A checkpoint

1. Run only one test run on the machine at a time, as the project's own
   rules say: wait for any other to finish first.
2. Run the `checkpoint command` setting in the background from the main
   checkout, on the default branch, and wait for it to exit.
3. On a pass, `bin/rro.py set-status <order> <label> "passed <counts>"`.
   On a failure, set `failed <counts>`, list the lists merged since the last
   passing checkpoint, newest first, as the suspects, report them and stop.
   Commit and push the order file either way.
4. After a pass, run `bin/rro.py decisions <order> --since <the previous
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

Publish one page per order at the start. Build its data from the order file
(`bin/rro.py next` and the table's rows), never from memory: each row's
label, list, status and the time of the last change. Republish it at every
list start, stop, merge and checkpoint. On the first publish, write its URL
to the order file's `progress page` setting, commit and push. The file stays
the record; the page never disagrees with it.

## Resume

The order file is the state. A new session given the same file continues
from `bin/rro.py next`:

- `Resume` of a `running` list: check whether its queue is still running
  (`ps -o comm=`, by name, never `pkill -f`). If not, run `/rrq --decide` on
  it again as `rrq.md` does.
- `Resume` of a `waiting: ...` row: ask the operator about the stop it
  names, then continue.
- `Resume` of a `failed` checkpoint: tell the operator and wait.

## Finish

When `next` returns `Finished`, report the merged lists, the checkpoints and
their counts, and the decisions still awaiting review, with the batch review
pages' URLs. State what was last checked and when.
