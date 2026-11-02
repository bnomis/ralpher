# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

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
