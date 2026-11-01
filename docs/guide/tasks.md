# Task files and queues

`--task-file PATH` tells ralpher which Markdown file holds the queue's tasks.
ralpher reads it to name the worktree, to show which task has started, and to
check a stop marker. The agent is the only thing that edits it.

## Format

ralpher parses two kinds of line:

```markdown
## Task 3: Read settings from TOML

**Status:** in-progress
```

- a task heading, `## Task <number>: <title>`;
- the first `**Status:** <value>` line after it, before the next `## `
  heading. The value is lowercased; a task with no status line counts as not
  done.

Everything else is ignored, including headings and status lines inside
fenced code blocks (`` ``` `` or `~~~`), so a tasks file can show an example
task without it being counted. Statuses the bundled prompt uses are `todo`,
`in-progress` and `done`; ralpher only distinguishes `done`, and
`in-progress` for start lines.

The file must exist and not be empty when the run starts.

## Task blocks

The agent reports progress by printing a `<task>` block in its text output:

```xml
<task>
<id>3</id>
<title>Read settings from TOML</title>
<index>3</index>
<count>7</count>
<status>done</status>
</task>
```

`status` is one of `start`, `done`, `blocked` or `operator`. ralpher prints a
progress line for each block and fires an `llm_task_progress` hook:

```text
task 3: Read settings from TOML 3/7 done
```

ralpher also polls the tasks file every few seconds while the agent runs, and
prints a `start` line for any task newly marked `in-progress`, because agents
often skip the start block. Each task gets one start line per iteration.

Two statuses end the run:

| Status | What happens |
|--------|--------------|
| `operator` | The task needs a person. The agent is stopped and the run ends as a termination, printing `Probable next prompt...` and `unblock task <n> in [worktree ]task file <path>`. |
| `blocked`, the identical block a third time in one run | Looks like a loop. The run ends as a termination with the same next prompt. |

## Verified stop

With `--task-file`, a stop marker is checked against the tasks file before
the loop stops:

- The check passes when every task's status is `done`.
- With `--worktree`, ralpher reads the copy of the tasks file inside the
  agent's worktree (the worktree whose branch is `worktree-<name>`), never the
  copy in your checkout.
- On rejection ralpher prints
  `===== Loop complete signal rejected, <n> of <m> tasks not done =====`,
  lists the unfinished tasks, records `stop_rejected` for the iteration in
  the state file, and runs the next iteration. A rejection on the last
  iteration ends the run with `completed all iterations`.
- If the check cannot be made (file missing or unreadable, no tasks found,
  worktree not found), ralpher logs a warning, trusts the marker and stops.

`--no-verify-stop` skips the check and stops on any marker. Use it when the
tasks file does not follow the format above. The cost is that one premature
marker ends the whole queue.

Without `--task-file` the check never runs.

## Running a queue

[`rrq.sh <spec> <n>`](../reference/scripts.md#rrqsh) runs
`agents/tasks/<spec>/tasks-<n>.md` with the bundled one-task prompt in a
worktree. The equivalent call:

```shell
ralpher.sh --cwd "$PWD" --worktree \
  --task-file agents/tasks/<spec>/tasks-<n>.md \
  --prompt "$RALPHER_PATH/agents/prompts/one-task.md" \
  --iterations 20 \
  --logdir ralpher-logs/<spec>/tasks-<n> \
  --stdout stdout.jsonl --stderr stderr.jsonl --progress progress.log \
  --errors errors.log --state state.json
```

Rerunning the same command after a stop resumes the queue: the worktree is
reused, and the agent reads the tasks file to find where it is. Each run
writes new log files beside the old ones; see
[Logs and state](logs.md#file-names).

Set `--iterations` above the number of tasks. Some iterations do no task
work: one that only repairs the tasks file, one that finds a task blocked.
