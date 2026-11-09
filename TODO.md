# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## `rro decisions` drops a `Queue-decision:` line that git does not parse as a trailer

Found on 2026-11-09, at the final checkpoint of an order in another project:
`bin/rro.sh decisions <order> --since <ref>` printed `[]`, while
`git log --grep '^Queue-decision:' <ref>..main` listed the one decided stop.
Three of the six `Queue-decision:` commits on that project's default branch
had the same shape.

Cause: `decisions_since` (`src/ralphlib/order.py`) selects commits with
`--grep=^Queue-decision:` but reads the value with
`%(trailers:key=Queue-decision,valueonly)`, and git parses trailers only in a
message's last paragraph. The missed commits put a blank line between the
`Queue-decision:` line and `Co-Authored-By:`, so the grep matched, the trailer
parser returned nothing, and the `if task.strip()` check dropped the commit
without a word. Removing the blank line makes `git interpret-trailers --parse`
find it. The missed commit was a task's own commit made by the queue agent,
with a free-text value ("sites S1, S3 and S4 change; ..."), not the
`<task list path> Task <N>` that `claude/commands/rrq.md` step 4 asks the
session for.

Fix direction: in `decisions_since`, take the value from the body's
`^Queue-decision:` line when the trailer parser returns nothing, or raise an
error naming each commit the grep matched and the parser did not, so a batch
review is never published empty by mistake. Add a test with the blank-line
shape beside `test_decisions_since_filters_and_orders`
(`src/tests/test_order.py`). Consider saying in `rrq.md` that the line goes in
the message's last paragraph, beside the other trailers. Small; no spec.
