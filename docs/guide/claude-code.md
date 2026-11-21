# Driving ralpher from Claude Code

A queue takes from minutes to hours. You can start it from an interactive
Claude Code session and have that session relay progress, then deal with the
result: review the branch, run the cleanup commands, answer an `operator`
stop.

## The `/rrq` command

[`bin/install-claude.sh`](../install.md#optional-the-rrq-command-for-claude-code)
installs `/rrq` into `~/.claude/commands/`. In a session at a project's root:

```text
/rrq config-loader 1
```

The session:

1. runs `$RALPHER_PATH/bin/rrq.sh config-loader 1` in the background, from
   the main checkout even if the session is in a worktree;
2. watches the output for task progress and loop-end lines, and relays each
   as one short line: `▶` start, `✓` done, `✗` blocked, `?` operator,
   `■` loop end;
3. when the queue exits, shows the last 100 lines of its output, which hold
   the exit reason and either the cleanup commands or the next prompt.

`/rrq --decide <spec> <n>` lets the session settle an `operator` stop
itself, rather than stopping for you.

`/rro <order file>` runs several task lists in a set order, merging each and
checking in between; see [Running an order of task lists](../run-order.md).

The command file is `claude/commands/rrq.md` in ralpher's checkout. Read it
before you rely on it; edit it to change what the session relays.

## Without the command

Any program can follow a queue: run `rrq.sh` with its output going to a file,
and filter that file as shown in
[Terminal output](terminal.md#lines-worth-watching-for). The
[state file](logs.md#the-state-file) gives the outcome as JSON once the run
ends.
