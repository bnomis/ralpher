# Getting started

Two runs: a plain loop on a prompt, then a task queue in a worktree, which is
how ralpher is mostly used.

## A plain loop

From the root of a git repository with a clean working tree:

```shell
ralpher.sh --iterations 3 --prompts 'Read TODO.md, do the first item, commit, and exit.
If TODO.md has no items, print <promise>COMPLETE</promise> on a line of its own.'
```

ralpher checks the repository (see [Worktrees and git](guide/worktrees.md#pre-run-checks)),
then runs `claude` up to three times. Each iteration prints the rendered
prompt, then the agent's streamed text and tool calls, then a summary of the
tools it used. When a line of the agent's output is exactly
`<promise>COMPLETE</promise>`, the loop stops after that iteration.

Put a longer prompt in a file and pass `--prompt PROMPT.md` instead of
`--prompts`. The prompt is a [Jinja template](guide/prompts.md), rendered
afresh for each iteration.

Add logs:

```shell
ralpher.sh --iterations 3 --prompt PROMPT.md \
  --logdir ralpher-logs/todo --progress progress.log --stdout stdout.jsonl \
  --stderr stderr.jsonl --errors errors.log --state state.json
```

See [Logs and state](guide/logs.md) for what each file holds.

## A task queue in a worktree

A task queue is a Markdown tasks file worked through by one prompt, one task
per iteration, in a git worktree so your checkout stays untouched.

1. Write a tasks file at `agents/tasks/<spec>/tasks-<n>.md`. Each task is a
   `## Task <n>: <title>` heading followed by a `**Status:** todo` line:

    ```markdown
    # Tasks: config loader

    ## Task 1: Add the Settings dataclass

    **Status:** todo

    Fields and defaults as in the spec...

    ## Task 2: Read settings from TOML

    **Status:** todo
    ```

2. Commit and push it. With `--worktree`, Claude Code creates the worktree
   from `origin`'s default branch unless you have set `worktree.baseRef` to
   `head`, so unpushed work is not in it.

3. From the repository root, run:

    ```shell
    rrq.sh <spec> <n>
    ```

    which is `ralpher.sh` with ralpher's bundled one-task prompt, 20
    iterations, `--worktree`, `--task-file agents/tasks/<spec>/tasks-<n>.md`
    and logs under `ralpher-logs/<spec>/tasks-<n>/`. See
    [Wrapper scripts](reference/scripts.md#rrqsh).

Each iteration, the agent picks the first eligible task, marks it
`in-progress`, does it, runs the project's checks, marks it `done` and
commits. ralpher prints a line as each task starts and finishes:

```text
task 1: Add the Settings dataclass 1/2 start
task 1: Add the Settings dataclass 1/2 done
```

When every task is `done`, the agent prints the completion marker, ralpher
confirms against the tasks file in the worktree, and prints the commands to
merge the branch and remove the worktree:

```text
Probable cleanup commands...
  cd /home/you/src/config-loader && \
  git merge --no-ff --no-edit worktree-config-loader-tasks-1 && \
  (git worktree unlock config-loader-tasks-1 2>/dev/null || true) && \
  git worktree remove --force config-loader-tasks-1 && \
  git branch -D worktree-config-loader-tasks-1 && \
  git push && \
  (git push origin --delete worktree-config-loader-tasks-1 2>/dev/null || true)
```

Review the branch before you run them: they merge, delete the worktree and
push.

If a task needs a decision from you, the agent reports it and ralpher stops
with a suggested prompt for an interactive session, for example
`unblock task 3 in worktree task file <path>`. Answer it there, then rerun
`rrq.sh`; the queue resumes from the tasks file.

## Next

- [How ralpher works](concepts.md)
- [Task files and queues](guide/tasks.md)
- [Hooks](guide/hooks.md), to be notified when a queue finishes
