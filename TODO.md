# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## A merged feature branch is still on the remote

Found on 2026-11-21 by a survey: `origin/feat/no-short-tail-checkpoint`
(last commit `2de0cde`, 2026-11-07) is an ancestor of `main`, so everything
on it is merged. No local branch tracks it.

Cause: the branch was merged without deleting it on the remote; `/cleanup`
never changes the remote.

Fix direction: the operator deletes it with
`git push origin --delete feat/no-short-tail-checkpoint`. Small; no spec.
