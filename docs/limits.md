# Limits

## Claude Code's output format

ralpher parses Claude Code's `stream-json` output. Another agent works only
if it writes the same JSON lines; `--agent` changes the command, not the
parser. When Claude Code adds a message type, ralpher logs the new lines to
the errors file and lists them at the end of the iteration, and otherwise
carries on: the stop marker and task blocks are still found as long as
assistant text keeps its shape.

## Permissions

The default `--args` include `--dangerously-skip-permissions`. An unattended
loop has nobody to answer a permission prompt, so without it the agent stalls
on the first tool that needs approval. With it, the agent can run any command
your user can, and a prompt injected through a file, a dependency or a web
page it reads is acted on without asking.

Ways to narrow that:

- run ralpher in a container or a disposable VM;
- replace `--args` with an allow-list:
  `--args '--verbose --include-partial-messages --print --output-format stream-json --allowedTools "Bash(pytest:*)" Edit Read'`;
- keep secrets out of the environment ralpher starts with: the agent
  inherits it.

## Git

- `--worktree` relies on Claude Code's own worktree support, and on its
  branch name, `worktree-<name>`, to find the tasks file for the verified
  stop.
- The pre-run checks prompt on the terminal, so they wait in an unattended
  run. Commit and push first, or pass `--skip-git-check`.
- The pre-run checks do not read a `--settings` you pass in `--args`; they
  take the base ref from `--worktree-base-ref` or Claude Code's settings
  files.
- The cleanup commands are printed for you to run; ralpher never merges,
  deletes or pushes.

## The stop marker

The agent decides when it is finished. Without `--task-file`, nothing checks
it: a premature marker ends the loop, and a forgotten one runs every
iteration. With a tasks file, the verified stop catches the first case,
not the second.

## Concurrency

Two runs with the same tasks file and `--worktree` share a worktree, and
would edit the same files. Run one queue per tasks file at a time.

## Platforms

ralpher is developed on macOS and Linux. Stopping the agent uses process
groups (`os.killpg`), and the bundled scripts are bash.
