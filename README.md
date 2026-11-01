# ralpher

A ralph loop: run a coding agent with the same prompt, a fresh process each
iteration, until it prints a completion marker. ralpher shows the agent's
streamed JSON as readable progress, checks a completion claim against a
tasks file, runs task queues in git worktrees, fires hooks, and records logs.

Documentation: <https://bnomis.github.io/ralpher/>

## Quick start

```shell
git clone git@github.com:bnomis/ralpher.git
cd ralpher
uv sync
export RALPHER_PATH="$PWD"

# from the root of the project the agent should work on
"$RALPHER_PATH/bin/ralpher.sh" --iterations 3 --prompts 'Do the first item in TODO.md, commit, and exit.
If TODO.md is empty, print <promise>COMPLETE</promise> on a line of its own.'
```

ralpher runs `claude` with `--dangerously-skip-permissions` by default; see
[Limits](docs/limits.md).

## Documentation source

The site is built from `docs/` with MkDocs:

```shell
uv run --group docs mkdocs serve
```
