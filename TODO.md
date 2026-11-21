# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## CI's `check` job fails on every Dependabot pull request

Found on 2026-11-21 by a survey: `check` fails on all five open Dependabot
pull requests (#21, #22, #24, #25, #26) with `Load key
"/home/runner/.ssh/agents_deploy_key": error in libcrypto` and `Permission
denied (publickey)` when pre-commit fetches the audit hooks (runs of
2026-11-15, e.g. run 43683071813).

Cause: a workflow run that Dependabot triggers reads Dependabot secrets, not
Actions secrets. `gh secret list --app dependabot` lists none, while the
deploy key is set only as the Actions secret `AUDITOR_DEPLOY_KEY`, which
`.github/workflows/ci.yml:48` writes to `~/.ssh/auditor_deploy_key`. The
failed runs predate the move to the auditor repository, but a rebased pull
request meets the same empty secret.

Fix direction: the operator adds the auditor deploy key as a Dependabot
secret named `AUDITOR_DEPLOY_KEY` (repository settings, Secrets and
variables, Dependabot); only the operator holds the key. Then ask Dependabot
to rebase each open pull request (`@dependabot rebase`) and check that
`check` passes. Small; no spec.

## `claude-review` fails on every Dependabot pull request

Found on 2026-11-21 by a survey: the `claude-review` job of
`.github/workflows/claude-code-review.yml` fails on all five open Dependabot
pull requests with `Workflow initiated by non-human actor: dependabot (type:
Bot). Add bot to allowed_bots list or use '*' to allow all bots.` (run
43683071806, 2026-11-15).

Cause: the job's `if:` condition is commented out
(`.github/workflows/claude-code-review.yml:16`), so the review starts for bot
pull requests, which the action refuses.

Fix direction: skip the job for Dependabot (`if: github.actor !=
'dependabot[bot]'`) rather than allowing bots, so a dependency bump spends no
review. Small; no spec.

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

## A merged feature branch is still on the remote

Found on 2026-11-21 by a survey: `origin/feat/no-short-tail-checkpoint`
(last commit `2de0cde`, 2026-11-07) is an ancestor of `main`, so everything
on it is merged. No local branch tracks it.

Cause: the branch was merged without deleting it on the remote; `/cleanup`
never changes the remote.

Fix direction: the operator deletes it with
`git push origin --delete feat/no-short-tail-checkpoint`. Small; no spec.
