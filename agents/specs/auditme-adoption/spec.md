# Auditme adoption

**Version:** 1.0
**Status:** implemented
**Date:** 2026-10-31

Clear every unaccepted hit the shared auditme checker reports on ralpher, then
make the checker a gate: the `auditme-changed` hook on every commit, the
`auditme-all` hook on every push, and a CI workflow that runs the checks and
the tests on every push and pull request. Each hit is either fixed or accepted
with a scoped marker giving the reason.

## Motivation

Found on 2026-10-31 in a TODO review (`TODO.md` item "The auditme checker is
not adopted here, so its hits accumulate unrecorded"). On 2026-10-31 at
`f339eec`, `python3 ~/.claude/skills/auditme/checks/audit.py .` reported 119
unaccepted hits and no accepted ones. One of them, `processed_hooks` at
`src/ralphlib/hooks.py:27`, was surfaced by that day's change to
`mutable-module-level-exported`; the new `raises-section-drift` rule had no
hits. `.pre-commit-config.yaml` ran ruff and shellcheck only, and no workflow
ran the checks or the tests, so nothing failed when a hit appeared.

The operator decided on 2026-10-31:

- `.pre-commit-config.yaml` may be changed for this work (`AGENTS.md` lists it
  as not to be modified without explicit instruction);
- every `from X import Y` is converted to a full import path, not accepted;
- the runtime caches are accepted with markers, not moved into a state object;
- a CI workflow with the audit deploy key is added in this spec.

## Module location

Source changes in `src/ralphlib/` (`giter.py`, `hooks.py`, `iteration.py`,
`logger.py`, `looper.py`, `options.py`, `printer.py`, `settings.py`,
`signals.py`, `state.py`, `templater.py`, `types.py`, `verifier.py`),
`src/tests/`, a new `src/tests/helpers.py`, and `bin/install-claude.py`.
Configuration in `.pre-commit-config.yaml`, a new `.github/workflows/ci.yml`,
and `AGENTS.md`.

## API

Public names that change. Everything else keeps its signature.

```python
# src/ralphlib/settings.py
def default_settings() -> dict[str, typing.Any]:
    """Return a fresh copy of the built-in settings, nested dicts included.

    Replaces the module-level dict `default_settings`, whose shallow `.copy()`
    shared the nested `theme` dict between every caller.
    """


# src/ralphlib/types.py
message_type_to_str: types.MappingProxyType[MessageType, str]
ralpher_event_type_to_str: types.MappingProxyType[RalpherEventType, str]


# src/ralphlib/state.py
def load_state(options: ralphlib.options.RalpherOptions) -> dict[str, typing.Any] | None:
    """Return the saved state, {} if the file does not exist, None if state is off."""


def save_state(options: ralphlib.options.RalpherOptions, state: dict[str, typing.Any]) -> None:
    """Write the state as JSON; do nothing if state is off."""


# src/tests/helpers.py
def make_options(**kwargs: typing.Any) -> ralphlib.options.RalpherOptions:
    """Build options with settings loaded, as most test modules do today."""
```

Removed:

- `ralphlib.iteration.slugify` and `ralphlib.iteration.task_file_slug`:
  callers use `ralphlib.templater.slugify` and
  `ralphlib.templater.task_file_slug`, which have identical bodies.
- `ralphlib.giter.is_clean_strict` and `ralphlib.giter.is_clean_no_untracked`:
  callers use `ralphlib.giter.is_working_tree_clean(repo, include_untracked=...)`.

## Implementation

Work rule by rule, re-running the checker after each and committing per rule.
The fix-or-accept choice for each hit is listed below, as classified on
2026-10-31; a line number is the 2026-10-31 one and moves as edits land.
Accept markers use the scoped form `# auditme: accept[<rule>] <reason>`, on the
hit line or the line above.

| Rule | Fix |
|---|---|
| `from-import` | Rewrite as `import x` with qualified names, in `src/` and `bin/`. `from typing import TYPE_CHECKING` becomes `import typing` and `if typing.TYPE_CHECKING:`; a TYPE_CHECKING-only `from ralphlib.options import RalpherOptions` becomes `import ralphlib.options` inside that block, and annotations name `ralphlib.options.RalpherOptions` (Python 3.14 evaluates annotations lazily). `from unittest.mock import patch` becomes `unittest.mock.patch`; `from hypothesis import given, strategies` becomes `hypothesis.given` and `hypothesis.strategies`. |
| `except-interpolation` | Where the message goes to `loguru.logger.exception`, drop the `{e}`: the traceback carries it (`hooks.py:222`, `iteration.py:168,240,252,620,779`, `looper.py:135`, `state.py:33`). Where the message reaches a person without a traceback - the console, the session error log, a stop-check reason - accept: `giter.py:143`, `iteration.py:621,780`, `state.py:66` (also printed to stderr), `verifier.py:132`, `bin/install-claude.py:115` (the exit message). |
| `mutable-module-level-exported` | Accept `processed_hooks` and `seen_task_ids` (`hooks.py`) and `log_file_cache` (`logger.py`), with the reason "process-lifetime cache, mutated at run time; tests reset it". Wrap `message_type_to_str` and `ralpher_event_type_to_str` in `types.MappingProxyType`; their members are strings. Replace `default_settings` with the function in [API](#api); `load_settings` calls it, and `test_looper.py` and `test_settings.py` call or patch the function. |
| `paired-sibling-helpers` | Delete `slugify` and `task_file_slug` from `iteration.py`, and move their tests from `test_iteration.py` to `test_templater.py`, targeting `ralphlib.templater`. Each group of identical `make_options` bodies in the test modules becomes one function in `src/tests/helpers.py`, imported as `import tests.helpers`; a test module whose body differs keeps its own. |
| `literal-duplication` | Name each repeated tuple once as a module constant in its test file (`('README.md',)` in `test_giter.py`, `('claude', '--verbose')` and `('true',)` in `test_iteration.py`, `('echo hi',)` in `test_settings.py`). |
| `bare-parametric-annotation` | `dict` becomes `dict[str, typing.Any]` (`iteration.py:132`, `options.py:129`, `state.py`, `test_looper.py:98`, `test_process_termination.py:100`). |
| `get-container-default-then-method-call` | `d.get(k, {})` becomes `d.get(k) or {}`, and `[]` likewise (`iteration.py:665,924,931,942`), so an explicit JSON `null` in the agent's stream no longer raises `AttributeError`. |
| `leading-underscore-binding`, `leading-underscore-def-class` | `looper.py:27`: call `ralphlib.signals.GracefulTerminator(options)` without binding it; `signal.signal` holds the bound handler, so the object stays alive. In `test_process_termination.py`, rename the `_options` and `_context` parameters and the `_fast_poll` fixture (and its `usefixtures` uses) without the underscore. |
| `passthrough-shim` | Remove the shims named in [API](#api); `giter.py:91` and `test_giter.py` call `is_working_tree_clean` directly. |
| `silent-broad-except` | `giter.py` `has_unpushed_commits`: catch `(git.GitCommandError, git.GitCommandNotFound, OSError, UnicodeDecodeError)` around the fetch and log it with `loguru.logger.warning` beside the console message. |
| `mutable-store-without-copy` | `test_looper.py` `LoopRun.__init__` stores `list(calls)` and `dict(state)`. |
| `non-alphabetical-literal` | Accept `test_verifier.py:9`: `['todo', 'in-progress', 'done']` is the status progression, and order is its meaning. |
| `stdlib-logging` | Accept `bin/install-claude.py:7`: the installer runs under the system Python, before the project's environment (and `loguru`) exists. |

Then adopt the hooks, as the shared `project-setup` skill's `adopt` mode does.
That mode adds the shared hooks repository to `.pre-commit-config.yaml`,
installs both hook types, writes the CI workflow below, creates the
read-only deploy key and its repository secret, and adds the gate wording to
`AGENTS.md`; the steps below restate each so this spec stands alone:

1. Add to `.pre-commit-config.yaml`, after the existing repos, the
   `git@github.com:bnomis/agents.git` repo pinned at the agents `main` commit
   on the day of the change (`dddaf02` on 2026-10-31; resolve it again with
   `git ls-remote git@github.com:bnomis/agents.git refs/heads/main`), with
   hooks `auditme-changed` and `auditme-all` (`stages: [manual, pre-push]`),
   and the `no-project-names` hook with `--allow=ralpher` and
   `--allow=ralphlib`.
2. Run `pre-commit install --hook-type pre-commit --hook-type pre-push`.
3. Write `.github/workflows/ci.yml` from the `project-setup` template: checkout
   without persisted credentials, Python 3.14, uv, `uv sync`, the project's
   `.venv/bin` on `PATH`, `uv run pytest`, the deploy-key step, `pre-commit
   run --all-files`, `pre-commit run auditme-all --hook-stage manual
   --all-files`, and the key removal (`if: always()`). Pin each third-party
   action to an exact release tag, as the security rule requires; Dependabot
   moves the tags.
4. Create the deploy key and secret with the `project-setup` deploy-key steps:
   a read-only key added to `bnomis/agents`, its private half set as the
   `AGENTS_DEPLOY_KEY` secret on this repository, both files deleted
   afterwards. Each step is confirmed by the operator before it runs, and the
   private key is never printed.
5. In `AGENTS.md`: under "Coding standards", say that `ruff check`,
   `ruff format` and the auditme hooks run on commit, the whole-tree audit
   on push and in CI, and that a hit is fixed or accepted with a scoped marker
   giving its reason; under "Do not modify", leave `.pre-commit-config.yaml`
   listed.

## Error handling

- A gate that fails: the commit or push stops with the checker's hit list.
  Fix the hit or accept it with a reason; never bypass with `--no-verify`.
- `git ls-remote` on the agents repository fails (no SSH access): stop. The
  hooks cannot be pinned without a revision.
- A deploy-key step fails: delete the scratch key files, report which step
  failed, and leave the CI audit step failing rather than removing it.
- Behaviour changes that tests must cover: an explicit `null` for `content`,
  `event`, `content_block` or `delta` in the agent's stream is treated as
  empty (a test per site, written failing first); `load_settings` returns a
  `theme` dict not shared with a second call; a failed fetch logs a warning
  and returns `None`, so the caller asks the user.

## External dependencies

- The shared auditme checker, as the `auditme-changed` and `auditme-all`
  pre-commit hooks from the private `bnomis/agents` repository, pinned by
  commit.
- `pre-commit`, installed as a uv tool on developer machines and in CI.
- GitHub Actions: `actions/checkout`, `actions/setup-python`,
  `astral-sh/setup-uv`, pinned by release tag.

## Out of scope

- Moving the runtime caches into a state object (decided against on
  2026-10-31).
- Changing the checker. The `filesystem-envelope-gap` miss on a named
  exception tuple is raised separately, in the shared repository's auditme
  `requests.md`.
- Correcting the status of the [verified-stop spec](../verified-stop/spec.md),
  which now reads `implemented`.

## Acceptance

- `python3 ~/.claude/skills/auditme/checks/audit.py .` reports no
  unaccepted hits, and every accepted one carries a scoped marker with a reason.
- `pre-commit run --all-files` and
  `pre-commit run auditme-all --hook-stage manual --all-files` pass.
- `uv run pytest` passes.
- The CI workflow passes on the pushed branch.
- The `TODO.md` item moves to `DONE.md` with a `Done:` line naming this spec
  and its task list.
