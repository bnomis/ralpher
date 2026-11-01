# Command line

```text
ralpher.sh [OPTIONS]
```

`bin/ralpher.sh --help` prints the same list from the code.

## What to run

| Option | Default | Description |
|--------|---------|-------------|
| `--agent AGENT` | `claude` | The agent command. |
| `--args ARGS` | `--verbose --include-partial-messages --print --dangerously-skip-permissions --output-format stream-json` | The agent's arguments, split as a shell would. Replaces the default entirely. |
| `--prompt FILE` | | Read the prompt from a file. |
| `--prompts TEXT` | | The prompt as text. Ignored when `--prompt` is given. |
| `--iterations N` | `3` | The most iterations to run. |
| `--cwd DIR` | the current directory | The directory the agent runs in, and the git checks run in. Also adds `DIR/.ralpher/settings.json` to the settings files. |
| `--vars KEY=VALUE` | | A prompt template variable. Repeatable. See [Prompts](../guide/prompts.md#-vars). |

## Tasks and stopping

| Option | Default | Description |
|--------|---------|-------------|
| `--task-file FILE` | | The tasks file. Names the worktree, and turns on the [verified stop](../guide/tasks.md#verified-stop). Must exist and not be empty. |
| `--stops MARKER` | `<promise>COMPLETE</promise>` | A completion marker: a line of agent output equal to it ends the loop. Repeatable; giving it replaces the default. |
| `--no-verify-stop` | off | Trust a marker without checking the tasks file. |

## Worktrees and git

| Option | Default | Description |
|--------|---------|-------------|
| `--worktree` | off | Pass `--worktree <name>` to the agent, the name taken from the tasks file. See [Worktrees and git](../guide/worktrees.md). |
| `--worktree-base-ref fresh\|head` | | Pass Claude Code's `worktree.baseRef` setting with `--settings`. |
| `--skip-git-check` | off | Skip the [pre-run checks](../guide/worktrees.md#pre-run-checks). |
| `--cleanup` | off | Print the worktree cleanup commands for `--worktree` and `--task-file`, and exit without running anything. |

## Output and logs

| Option | Default | Description |
|--------|---------|-------------|
| `--logdir DIR` | | Directory for the files below. Created if missing. |
| `--stdout FILE` | | Raw agent stdout, per iteration. |
| `--stderr FILE` | | Raw agent stderr, per iteration. |
| `--progress FILE` | | Everything printed, per iteration, plus a run file. |
| `--errors FILE` | | Unparsed lines and parse errors, per iteration. |
| `--state FILE` | | The run's JSON state file. |
| `--quiet` | off | Print nothing to the terminal. Log files are still written. |

See [Logs and state](../guide/logs.md).

## Settings

| Option | Default | Description |
|--------|---------|-------------|
| `--settings-file FILE` | | A settings file read after the others, so its keys win. |
| `--load-settings-on-loop` | off | Read the settings files again before each iteration. |

See [Settings](settings.md).

## Other

| Option | Description |
|--------|-------------|
| `-h`, `--help` | Show the options and exit. |
| `--completion generate` | Print shell completion source. |

Options take their value either as `--iterations 5` or `--iterations=5`.
