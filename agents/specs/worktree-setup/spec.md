# Worktree setup

**Version:** 1.0
**Status:** implemented
**Date:** 2026-11-21

A queue runs its agent in a fresh git worktree, which has the project's
tracked files and nothing else: no virtual environment, no installed tools.
A check that runs the project's pinned tools from its environment then falls
back to whatever is on `PATH`, and reports differences the main checkout does
not have. This spec adds a per-project list of setup commands, kept in
ralpher's settings, which the prompt tells the agent to run in the worktree
before it does anything else.

Found on 2026-11-21 while `rrq.sh` ran another project's audit task list in a
fresh worktree. That project pins `ruff-pre-commit` at `v0.17.4`. The
worktree had no `.venv`, so the audit's `ruff-version-drift` check, which runs
the project's own `.venv/bin/ruff` when it is an executable file and the ruff
on `PATH` otherwise, ran Homebrew's ruff 0.17.6 and reported a drift the main
checkout did not have. The queue's agent worked round it by putting the main
checkout's `.venv/bin` first on `PATH`, which nothing in ralpher asked it to
do.

ralpher only adds `--worktree <name>` to the agent's arguments
(`add_worktree_arg` in `src/ralphlib/iteration.py`). Claude Code creates the
worktree at `<repo>/.claude/worktrees/<name>` on branch `worktree-<name>`, and
nothing creates the project's environment in it. Claude Code has no
setup-command setting (its worktrees page, read 2026-11-21, says to run setup
in the worktree yourself).

The command differs per project (`uv sync` for a uv project, `npm ci` for a
Node one), so it is runtime config with no built-in default.

## Decisions

Answered by the operator on 2026-11-21:

- **The agent runs the commands, told by the prompt.** ralpher neither
  creates the worktree nor runs the commands itself. Rejected: ralpher
  creating the worktree with `git worktree add` before iteration 1, and a
  `WorktreeCreate` hook passed through `--settings`.
- **The commands run at the start of every run**, not only when the worktree
  is created, so a resumed queue picks up a lock that moved on `main`.
  Commands must be safe to repeat (`uv sync` is). Carried into the prompt
  when this spec was written: each iteration starts a new agent session that
  cannot tell whether an earlier one ran them, so the prompt asks every
  iteration's agent to run them. Rendering the block only for iteration 1
  would undo this choice, if wanted.
- **A settings key only.** No command-line option.

Out of scope:

- ralpher creating the worktree or running the commands itself (decided
  against on 2026-11-21).
- Copying gitignored files into the worktree; Claude Code's own
  `.worktreeinclude` already does that for worktrees it creates.

## Module location

- `src/ralphlib/settings.py` - validate the new key
- `src/ralphlib/templater.py` - expose it to prompts
- `src/ralphlib/looper.py` - warn when `--worktree` runs without it
- `agents/prompts/one-task.md` - tell the agent to run the commands
- `docs/reference/settings.md`, `docs/reference/variables.md`,
  `docs/guide/worktrees.md`, `docs/guide/prompts.md` - user docs
- `src/tests/test_settings.py`, `src/tests/test_templater.py`,
  `src/tests/test_looper.py` - tests

## API

```python
# src/ralphlib/settings.py
def validate_settings(file_settings: dict[str, typing.Any], path: pathlib.Path) -> None:
    """Raise SettingsError when `hooks`, `hook_templates`, `theme` or
    `worktree_setup` has the wrong shape.

    `worktree_setup`, when present, must be a list of strings.
    """


# src/ralphlib/templater.py
def render(options: ralphlib.options.RalpherOptions, prompt: str, iteration: int) -> str:
    """Render the prompt template.

    Adds `worktree_setup` to the context: the list of command strings from
    `options.settings['worktree_setup']` when `--worktree` is given, else an
    empty list. A `--vars` key named `worktree_setup` is rejected, as for
    every built-in: `BUILTIN_VARS` gains `worktree_setup`.
    """


# src/ralphlib/looper.py
def warn_missing_worktree_setup(options: ralphlib.options.RalpherOptions) -> None:
    """With --worktree and no `worktree_setup` setting, log a warning and
    print `Warning: no worktree_setup setting; the agent's worktree has no
    project environment.` to stderr. Prints nothing otherwise."""
```

`loop` calls `warn_missing_worktree_setup(options)` once, after settings are
loaded and before the first iteration, beside the pre-run git checks.

## Implementation

**Settings.** `worktree_setup` is a top-level key like `hooks`: each settings
file's value replaces the earlier one whole. `validate_settings` checks it in
the same pass as the other keys. Its strings are not rendered as templates and
not run by ralpher.

**Prompt context.** `render` sets `context['worktree_setup']` to a new list
copied from the setting (so a template cannot change the settings), or `[]`.
`--load-settings-on-loop` picks up a change on the next iteration, as for
every setting.

**Prompt text.** In `agents/prompts/one-task.md`, inside the existing
`{% if worktree %}` block, after the line telling the agent to change to the
worktree:

```jinja
{% if worktree_setup %}
- After changing to the worktree and before anything else, run these
  commands in the worktree, in order, so its checks and tests use the
  project's own pinned tools:
{% for command in worktree_setup %}
  - `{{ command }}`
{% endfor %}
  If one fails, write a `<task>` block with `<status>blocked</status>`
  naming the command and its error, and exit. Do not work round it by
  using another checkout's environment.
{% endif %}
```

The block is not shown when the list is empty, so a project without the
setting gets the prompt it gets today.

**Warning.** `warn_missing_worktree_setup` checks `options.worktree` and
`options.settings.get('worktree_setup')`; an empty list counts as missing. It
uses `loguru.logger.warning` and `ralphlib.printer.console_stderr.print`, as
the other pre-run warnings do, and does not stop the run.

## Error handling

- `SettingsError` (existing) when `worktree_setup` is not a list of strings:
  `Settings file <path>: worktree_setup must be a list of strings`. The run
  stops before the first iteration with the usual `Error:` line and exit
  status 1.
- `InvalidVarFormatError` (existing) for `--vars worktree_setup=...`, as for
  every built-in name.
- A setup command that fails is the agent's to report: the prompt tells it to
  write a `blocked` task block and exit, which the queue already treats as a
  stopped task. ralpher does not run the commands, so it raises nothing for
  them.

## Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `worktree_setup` | list of strings | none | Commands the agent runs in its worktree before anything else, every iteration. Must be safe to repeat. Normally set in the project's `.ralpher/settings.json`, e.g. `["uv sync"]`. |

## Tests and documentation

Tests:

- `test_settings.py`: a list of strings passes; a string, a list holding a
  number, and an object each raise `SettingsError` naming `worktree_setup`;
  a later file's `worktree_setup` replaces an earlier one.
- `test_templater.py`: with `--worktree` and the setting, the context lists
  the commands; without `--worktree`, or without the setting, it is `[]`;
  `--vars worktree_setup=x` is rejected; rendering
  `agents/prompts/one-task.md` shows each command, in order, only when the
  list is not empty.
- `test_looper.py`: `warn_missing_worktree_setup` prints the warning with
  `--worktree` and no setting, and with an empty list; prints nothing with the
  setting, or without `--worktree`.

User docs, in the same change:

- `docs/reference/settings.md`: a row for `worktree_setup` in the Keys table.
- `docs/reference/variables.md`: a `worktree_setup` row under Prompts.
- `docs/guide/worktrees.md`: a section on giving the worktree an environment,
  with the `uv sync` example, why it matters (a check that falls back to
  `PATH`), the warning, and that the commands must be safe to repeat.
- `docs/guide/prompts.md`: that `one-task.md` shows the commands, and that a
  custom prompt can use `worktree_setup`.

## External dependencies

None new. Jinja2 (already used by `templater.render`) renders the list.
