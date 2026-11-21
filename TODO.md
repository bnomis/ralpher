# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## Merging the ruff 0.17.3 bump would fail the push hook

Found on 2026-11-21 by a survey: Dependabot pull request #24 moves ruff from
0.17.2 to 0.17.3 in `pyproject.toml` and `uv.lock` only, while
`.pre-commit-config.yaml:4` pins the `ruff-pre-commit` hook at `rev:
v0.17.2`.

Cause: the audit's `ruff-version-drift` check compares the ruff in `.venv`
with that `rev` and reports any difference, so once the lock holds 0.17.3
the `auditme-all` push hook and CI fail until the `rev` matches.
`.pre-commit-config.yaml` is under "Do not modify" in `AGENTS.md`.

Fix direction: with the operator's go-ahead to edit `.pre-commit-config.yaml`,
raise the `rev` to `v0.17.3` in the same change that merges #24 (push a
commit to the Dependabot branch, or take the bump on `main` by hand and close
the pull request). Waits on the `check` item above for #24's own CI. Small;
no spec.

Note 2026-11-21: the `check` item is done (see `DONE.md`). #24, rebased at
15:49 UTC, now fails only here: run 44921408958 reports `ruff-version-drift`
at `.pre-commit-config.yaml:4`.

## A merged feature branch is still on the remote

Found on 2026-11-21 by a survey: `origin/feat/no-short-tail-checkpoint`
(last commit `2de0cde`, 2026-11-07) is an ancestor of `main`, so everything
on it is merged. No local branch tracks it.

Cause: the branch was merged without deleting it on the remote; `/cleanup`
never changes the remote.

Fix direction: the operator deletes it with
`git push origin --delete feat/no-short-tail-checkpoint`. Small; no spec.
