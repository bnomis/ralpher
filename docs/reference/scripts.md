# Wrapper scripts

All live in ralpher's `bin/`. Each shell wrapper activates ralpher's `.venv` first (`install-claude.py`
is run with `python3` and does not). `ralpherun.sh`, `rrq.sh` and `rcl.sh` need
`RALPHER_PATH` set to ralpher's checkout.

## `ralpher.sh`

```text
ralpher.sh [OPTIONS]
```

ralpher itself; every [option](cli.md) is passed through.

## `rrq.sh`

```text
rrq.sh SPEC INDEX
```

Runs a task queue. From your project's root:

| Passed to ralpher | Value |
|-------------------|-------|
| `--cwd` | the current directory |
| `--task-file` | `agents/tasks/SPEC/tasks-INDEX.md` |
| `--prompt` | ralpher's `agents/prompts/one-task.md` |
| `--iterations` | `20` |
| `--worktree` | on |
| `--logdir` | `ralpher-logs/SPEC/tasks-INDEX` |
| `--stdout`, `--stderr`, `--progress`, `--errors`, `--state` | `stdout.jsonl`, `stderr.jsonl`, `progress.log`, `errors.log`, `state.json` |

`SPEC` and `INDEX` must not contain `/` or `..`; `rrq.sh` and `rcl.sh` print
a usage message and exit otherwise.

Add `ralpher-logs/` to your project's `.gitignore`.

## `rcl.sh`

```text
rcl.sh SPEC INDEX
```

Prints the [cleanup commands](../guide/worktrees.md#after-the-queue) for the
queue `rrq.sh SPEC INDEX` ran, and exits. Runs nothing.

## `ralpherun.sh`

```text
ralpherun.sh ITERATIONS PROMPT LOGDIR [TASKS]
```

Runs ralpher with `--worktree`, the five log files in `LOGDIR`, and
`--task-file TASKS` when given. Its `--cwd` is the directory above the
script's `bin/`, which is ralpher's own checkout, so it is for running loops
on ralpher itself. For another project, use `rrq.sh` or `ralpher.sh --cwd`.

## `install-claude.py`

```text
python3 bin/install-claude.py
```

Symlinks the files under ralpher's `claude/` into `~/.claude/`. See
[Driving ralpher from Claude Code](../guide/claude-code.md).
