# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## The auditme checker misses an `OSError` held in a named exception tuple

Found on 2026-11-01 in a TODO review. On 2026-10-31 the checker's
`filesystem-envelope-gap` rule flagged `src/ralphlib/verifier.py:129`,
although the next handler catches `READ_ERRORS`
(`src/ralphlib/verifier.py:17`), a tuple that holds `OSError`. The checker
reads the handler's name, not the tuple's value. The hit is accepted with
`# auditme: accept[filesystem-envelope-gap]` on line 129. The auditme-adoption
spec's "Out of scope" section says the miss "is raised separately, in the
shared repository's auditme `requests.md`", but on 2026-11-01 that file's
"Open" section says "None".

Cause: the rule resolves `except` clauses by name and does not follow a
module-level tuple constant to its members (suspected from the hit; the
checker code is not read here).

Fix direction: file an entry in the agents repository's
`claude/skills/auditme/requests.md`, where the change is made. Once the
checker resolves module-level exception tuples, remove the accept marker at
`src/ralphlib/verifier.py:129` and check that the rule reports no hit there.

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
