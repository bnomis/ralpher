# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## The `agent_process_end` hook event is never fired

Found 2026-11-01 while writing the user guide, at `631f6b1`:
`RalpherEventType.AGENT_PROCESS_END` and its name `agent_process_end` are
defined in `src/ralphlib/types.py:45` and `:58`, but only
`AGENT_PROCESS_START` is sent (`src/ralphlib/iteration.py:452`). A hook set
on `agent_process_end` is accepted and never runs. `docs/guide/hooks.md`
and `docs/reference/variables.md` leave the event out.

Cause: the event was declared alongside `agent_process_start` and its call
was never added.

Fix direction: fire it when the agent process exits, with
`agent_process_id` and the exit status in the context, test it in
`src/tests/test_hooks.py` or `test_iteration.py`, and add it to both docs
pages.

Note 2026-11-01: since the `--worktree-base-ref` fix, `AGENT_PROCESS_START` is
sent at `src/ralphlib/iteration.py:450`.
