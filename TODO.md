# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## The pre-run git checks ignore `--worktree-base-ref`

Found 2026-11-01 while writing the user guide, at `631f6b1`:
`check_repo_clean` (`src/ralphlib/giter.py:87`) and `check_divergence`
(`src/ralphlib/giter.py:163`) take the worktree base ref from
`claude_worktree_base_ref`, which reads only Claude Code's settings files.
`--worktree-base-ref` reaches the agent through `add_settings`
(`src/ralphlib/iteration.py:183`) but never the checks. With
`--worktree-base-ref fresh` and `"baseRef": "head"` in the settings, the
divergence check is skipped and the worktree starts from an `origin` that
lacks the local commits; with the opposite pair, the checks warn about a
divergence that does not matter. `docs/limits.md` records it as a limit.
`add_settings` also builds the `--settings` JSON with `%` formatting,
against the project's f-string rule.

Cause: no single place holds the effective base ref (option first, then
settings); each consumer reads one source.

Fix direction: add one function that returns the effective base ref from
the options and the settings, use it in both checks, build the
`--settings` JSON with `json.dumps`, test both combinations, and drop the
line from `docs/limits.md`.

## CI's actions are pinned by tag, not commit

Found 2026-11-01 at `631f6b1`: `.github/workflows/ci.yml:16`, `:22` and
`:25` use `actions/checkout`, `actions/setup-python` and
`astral-sh/setup-uv` by tag. `.github/workflows/docs.yml` pins the same
kind of actions to full commit SHAs, after that day's security review
flagged tags there: a moved tag runs new code in the job without a change
here.

Cause: `ci.yml` predates the pinning in `docs.yml`.

Fix direction: pin each action in `ci.yml` to its commit SHA with the tag
in a trailing comment, as `docs.yml` does.

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
