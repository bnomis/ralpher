# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## The locked ruff is older than the pre-commit ruff hook

Found on 2026-11-01 while getting CI to pass (`agents/tasks/auditme-adoption/tasks-1.md`
Task 12): the CI audit runs `ruff` from the project's `.venv`, so ruff was
added to the dev group. The pre-commit ruff hook is at `v0.17.3`, but the
`exclude-newer = "14 days"` cooldown in `pyproject.toml` only allowed
`ruff==0.17.1`, which was locked. Both versions passed the tree on
2026-11-01, but a later difference between them would make the commit hook
and the CI audit disagree.

Fix direction: once 0.17.3 clears the cooldown (published 2026-10-27, so
from 2026-11-10), run `uv add --dev ruff==0.17.3` so the locked ruff
matches the hook's `rev`, and keep the two equal whenever either moves.

Note 2026-11-01: agents `e7901e6` adds the `ruff-version-drift` rule, which
fails while the hook's `rev` and the locked ruff differ. To pass it, the
ruff-pre-commit hook was pinned back to `v0.17.1`, the locked version, so the
two match now. Remaining work: from 2026-11-10, raise both together - the
hook's `rev` to `v0.17.3` and `uv add --dev ruff==0.17.3` - in one commit.
