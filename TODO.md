# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## The `--vars` validation from audit review 2 has no tests

Found on 2026-11-02, reviewing `TODO.md` against the queue log for
`agents/tasks/audit-reviews/tasks-2.md` Task 5 ("Validate `--vars` before the
loop starts"). The agent reported adding tests for a bad format, each reserved
key and good vars in `src/tests/test_templater.py`, and looper tests for
`noequals` and `iteration=3`. Its commit, `a72ca80`, changes no test file, and
on 2026-11-02 nothing under `src/tests/` names `parse_vars`, a reserved key or
the loop refusing bad `--vars`. The tests were most likely written in the
queue's worktree and never staged. The task's subtask to confirm the looper
test fails against the old code was ticked without being run.

`templater.parse_vars` (`src/ralphlib/templater.py`) raises `InvalidVarFormat`
for a value without `=` and for a key `render` sets itself; `looper.loop`
(`src/ralphlib/looper.py`) calls it before the `start` hook.

Fix direction: add the tests the task describes - bad format, each reserved
key and good vars for `parse_vars`, and a `loop` test asserting no `start`
hook, no iteration and a `True` (error) return on bad `--vars` - and confirm
each fails against `a72ca80^`.

## The audit summary still lists the findings tasks-2 fixed as unresolved

Found on 2026-11-02, after `agents/tasks/audit-reviews/tasks-2.md` shipped in
merge `8d320ce`. The auditme skill's step 8b says that once a review's task
list ships, `agents/audit-reviews/summary.md` moves the resolved findings from
Unresolved to Recently resolved, and the list's Task 14 Notes repeat it. The
Task 14 agent left it for the merge, and nothing did it.

Fix direction: re-check each Unresolved finding in `summary.md` against the
code (the review-2 locations), move the fixed ones to Recently resolved with
review-2 as the review that raised them, and keep the rest, including the
property-test gaps in the next item.

## Seven functions from audit review 2's property-test gaps have no property test

Found on 2026-11-02 in the queue log for
`agents/tasks/audit-reviews/tasks-2.md` Task 14. Review-2's T2 question
(Finding 18) lists functions with well-defined input domains and only example
tests. Task 14 added hypothesis tests for eight of them, and its agent
reported that it skipped the rest without recording why none fits, though it
ticked the acceptance criterion:

- `iteration.process_line`, `iteration.process_stream_event`,
  `iteration.input_field_to_content` and `iteration.agent_environment`
  (`src/ralphlib/iteration.py`)
- `templater.render` (`src/ralphlib/templater.py`)
- `logger.log_file` (`src/ralphlib/logger.py`)
- `state.add_to_state` (`src/ralphlib/state.py`, the `key1`/`key2` merge)

Fix direction: add a hypothesis test for each
(`@hypothesis.settings(max_examples=20, deadline=10000)`), with strategies
for the stream-JSON payload shapes shared between `process_line` and
`process_stream_event`; where a property test does not fit, say why in the
test module and add an example test instead.
