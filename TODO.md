# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## The printed cleanup commands stop before the push when the branch was pushed

Found on 2026-11-01 after the `agents/tasks/auditme-adoption/tasks-1.md`
queue completed. The operator ran the "Probable cleanup commands" it printed.
The merge and the worktree removal succeeded, then `git branch -d
worktree-auditme-adoption-tasks-1` failed with "not deleting branch ... that
is not yet merged to 'refs/remotes/origin/worktree-auditme-adoption-tasks-1',
even though it is merged to HEAD", and the `&&` chain stopped before
`git push`. The branch had been pushed with `-u` for a CI run (Task 12), and
two more commits landed on it after that push, so its upstream was behind it.
`git branch -d` checks a branch with an upstream against that upstream, not
only against `HEAD`. The remote branch was also left on GitHub, which nothing
in the printed commands removes.

Cause: `cleanup_cmds` in `src/ralphlib/looper.py` builds the chain with
`git branch -d {branch}`, which refuses whenever the branch tracks a remote
copy that lacks its last commits. No test covers `cleanup_cmds`.

Fix direction: print `git branch -D {branch}`, which is safe because it runs
only after the merge in the same `&&` chain has succeeded. Decide whether to
also print `git push origin --delete {branch}` when the branch has a remote
copy, or a note saying so. Add tests on `cleanup_cmds`'s output.

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
