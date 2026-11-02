# Installation

ralpher is run from a checkout; it is not published as a package.

## Prerequisites

| Tool | Why |
|------|-----|
| Python 3.14.5 or later | ralpher's own code (`requires-python` in `pyproject.toml`) |
| [uv](https://docs.astral.sh/uv/) | creates ralpher's virtual environment from the lock file |
| git | the pre-run checks and worktrees |
| [Claude Code](https://code.claude.com/docs/en/overview) (`claude`), signed in | the default agent |

## Install

```shell
git clone git@github.com:bnomis/ralpher.git
cd ralpher
uv sync
```

`uv sync` creates `.venv` with the locked runtime dependencies and the `dev`
group. ralpher never installs into, or runs from, your project's environment.

## Check it

```shell
bin/ralpher.sh --help
```

prints every option with its default. Then check that the agent starts:

```shell
claude --version
```

## Make it easy to call

The wrapper scripts find ralpher through `RALPHER_PATH`. Set it, and put
`bin` on your `PATH`, in your shell profile:

```shell
export RALPHER_PATH="$HOME/src/ralpher"
export PATH="$RALPHER_PATH/bin:$PATH"
```

`bin/ralpher.sh` activates ralpher's `.venv` and puts its `src` on
`PYTHONPATH` before starting `bin/ralpher.py`, so it works from any directory.
The agent itself does not inherit that environment; see
[How ralpher works](concepts.md#the-agents-environment).

## Optional: the `/rrq` command for Claude Code

```shell
python3 bin/install-claude.py
```

symlinks everything under ralpher's `claude/` directory into `~/.claude/`,
which installs the `/rrq` command. An existing symlink at a destination is
replaced; an existing regular file is renamed with a `.orig` suffix, never
overwritten. See
[Driving ralpher from Claude Code](guide/claude-code.md).

## Update

```shell
git -C "$RALPHER_PATH" pull
uv --directory "$RALPHER_PATH" sync
```
