# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## A queue's worktree has no environment, so its audit runs PATH's ruff

Found on 2026-11-21 while `rrq.sh` ran another project's audit task list in
a fresh worktree. That project pins ruff-pre-commit at v0.17.4; the
worktree had no `.venv`, so the audit's `ruff-version-drift` check ran the
ruff on `PATH` (Homebrew 0.17.6) and reported a drift the main checkout did
not have. The queue's log shows its agent working round it by putting the
main checkout's `.venv/bin` first on `PATH` for the checks and tests; that
was improvised in the run, not done by ralpher.

Cause: ralpher only passes `--worktree` to the agent
(`add_worktree_arg()` in `src/ralphlib/iteration.py`), and the agent creates
an empty checkout; nothing creates the project's environment in it. The
audit's fallback to `PATH` is the auditor's specified behaviour (amendment
1.5 of its `agents/specs/project-setup/spec.md`), and the auditor's
`DONE.md` item "A worktree's ruff-version-drift hit is hidden by an accept
marker" (2026-11-21) leaves giving the worktree the pinned ruff to the queue
runner that creates it.

Fix direction: before the first task, run the project's environment setup in
the worktree, so its own pinned tools are the ones the checks find. The
command differs per project (`uv sync` for a uv project), so it is runtime
config, not a built-in default. It adds an option, so it goes through a spec
first.

Spec: agents/specs/worktree-setup/spec.md; tasks: agents/tasks/worktree-setup/tasks-1.md.
