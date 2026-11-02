# Worktrees and git

## Pre-run checks

Before the first iteration, ralpher checks the repository that contains
`--cwd` (or the current directory), and asks before carrying on:

| Check | Prompt default |
|-------|----------------|
| Not in a git repository | continue? no |
| Working tree has changes, including untracked files | continue? no |
| The current branch has commits its upstream lacks (after `git fetch origin`) | continue? no |
| With `--worktree` and a `fresh` base: `origin/HEAD` is not the current branch | exit now? yes |

The unpushed-commits check is skipped when worktrees are created from the
local `HEAD` (below). A failed fetch, a missing `origin` or a branch with no
upstream is reported and not treated as unpushed.

The prompts read from the terminal, so an unattended run that hits one waits.
Commit and push first, or pass `--skip-git-check` to skip every check.

## `--worktree`

With `--worktree`, ralpher adds `--worktree <name>` to the agent's arguments,
and Claude Code runs the agent in a git worktree of that name, on the branch
`worktree-<name>`. Every iteration passes the same name, so every iteration
uses the same worktree. ralpher adds nothing if `--args` already contains
`--worktree` or `-w`.

The name comes from the tasks file: its directory name and its stem, joined
with `-`, lowercased, with every run of characters other than `a-z` and `0-9`
turned into one `-`.

| `--task-file` | Worktree | Branch |
|---------------|----------|--------|
| `agents/tasks/config-loader/tasks-1.md` | `config-loader-tasks-1` | `worktree-config-loader-tasks-1` |
| `TASKS.md` | `tasks` | `worktree-tasks` |

Without `--task-file`, `--worktree` is passed on its own and Claude Code
picks the name.

The prompt must tell the agent to work in the worktree; the bundled one-task
prompt does when `{{ worktree }}` is true. See [Prompts](prompts.md).

## Where the worktree starts

Claude Code's `worktree.baseRef` setting decides what a new worktree is
created from:

- `fresh` (Claude Code's default): `origin`'s default branch. Unpushed
  commits and local changes are not in the worktree.
- `head`: your local `HEAD`, without uncommitted changes.

`--worktree-base-ref fresh|head` passes the setting to the agent as
`--settings '{"worktree": {"baseRef": "..."}}'`, unless `--args` already
contains `--settings`. See the
[Claude Code settings reference](https://code.claude.com/docs/en/settings-reference#worktree-baseref).

The pre-run checks use the same value the agent gets: `--worktree-base-ref`
when ralpher passes it, otherwise `worktree.baseRef` from Claude Code's
settings files (user, project, local and managed). A `--settings` of your
own in `--args` is not read.

## Precedence between `--args` and ralpher's options

A flag in `--args` wins over the ralpher option that would add the same flag:

| `--args` holds | Wins over | Effect |
|----------------|-----------|--------|
| `--worktree` or `-w` | `--worktree` | ralpher adds no worktree name; the agent uses yours |
| `--settings` | `--worktree-base-ref` | ralpher passes no `baseRef` setting |

ralpher logs a warning at start, naming each value that wins. The tasks file
ralpher reads for the stop check and for hook prompts is the worktree copy
only under `--worktree`.

## After the queue

When a run ends complete, with no error or termination, and used
`--worktree` and `--task-file`, ralpher prints the commands to fold the work
back in:

```shell
git merge --no-ff --no-edit worktree-<name> && \
(git worktree unlock <name> 2>/dev/null || true) && \
git worktree remove --force <name> && \
git branch -D worktree-<name> && \
git push && \
(git push origin --delete worktree-<name> 2>/dev/null || true)
```

They are printed, never run. Run them from your checkout of the branch the
worktree started from. `git branch -D` is used rather than `-d` because a
branch pushed for CI, then committed to, is refused by `-d` even once merged,
and the chain would stop before the push.

`--cleanup` prints the same commands without running anything, for a queue
that finished earlier:

```shell
ralpher.sh --cleanup --worktree --task-file agents/tasks/config-loader/tasks-1.md
```

[`rcl.sh <spec> <n>`](../reference/scripts.md#rclsh) is that call for a queue
started with `rrq.sh`.
