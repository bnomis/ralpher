# ralpher

ralpher runs a coding agent in a loop. Each iteration starts a fresh agent
process with the same prompt, streams its JSON output to your terminal as
readable progress, and records everything to log files. The loop ends when
the agent prints a completion marker, when the iteration budget runs out, or
when something goes wrong.

It is a "ralph loop": instead of one long agent session that fills its
context window, you run many short ones. State lives in the repository (code,
commits, a tasks file), not in the conversation, so every iteration starts
with a clean context and reads where the last one left off.

```shell
bin/ralpher.sh --iterations 5 --prompts 'Fix one failing test, commit, and exit.
If no test fails, print <promise>COMPLETE</promise> on a line of its own.'
```

## What it adds over a shell `for` loop

- **Readable progress.** The agent's `stream-json` output is parsed into
  streamed text, tool calls and task progress lines, coloured by a theme you
  control. See [Terminal output](guide/terminal.md).
- **A stop the agent cannot fake.** With a tasks file, a completion marker
  is accepted only when every task in the file is `done`. See
  [Task files and queues](guide/tasks.md#verified-stop).
- **Isolation.** With `--worktree`, the agent works in a git worktree named
  after the tasks file, and ralpher prints the commands to merge and remove
  it afterwards. See [Worktrees and git](guide/worktrees.md).
- **Hooks.** Run commands (desktop notifications, chat messages) when a run
  starts, an iteration ends, a task changes status, or the run ends. See
  [Hooks](guide/hooks.md).
- **Records.** Raw stdout and stderr, parsed progress, errors and a JSON
  state file, per iteration. See [Logs and state](guide/logs.md).
- **Safe stops.** An agent that asks for an operator, or loops on a blocked
  task, ends the run with a suggested next prompt; Ctrl+C twice stops the
  agent's whole process group. See [Stopping a run](guide/stopping.md).

## Where to start

- [Installation](install.md): clone, `uv sync`, check `claude` is on `PATH`.
- [Getting started](getting-started.md): a first loop, then a task queue in
  a worktree.
- [How ralpher works](concepts.md): the model behind every option.
- [Command line](reference/cli.md): every option and its default.

!!! warning "The default agent arguments skip permission prompts"

    ralpher runs `claude` with `--dangerously-skip-permissions` by default,
    because an unattended loop cannot answer prompts. The agent can run any
    command your user can. Run it in a repository you can restore, on a
    machine or container you are prepared to have changed, or pass your own
    `--args`. See [Limits](limits.md).
