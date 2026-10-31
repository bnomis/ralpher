# Tasks: Auditme adoption

**Spec:** `agents/specs/auditme-adoption/spec.md`
**Review:** `agents/specs/auditme-adoption/review-1.md` (every item approved on 2026-10-31)
**Created:** 2026-10-31
**Version:** 1

Code tasks first, behaviour changes before refactors, so a refactor never hides
a behaviour change. The hooks are added only once the checker reports no
unaccepted hit. New code in every task uses full import paths (`import x`,
never `from x import y`), so the from-import conversion does not have to be
redone.

The per-rule audit check in each task's Definition of Done counts the
unaccepted hits left for the rules that task covers:

```shell
python3 ~/.claude/skills/auditme/checks/audit.py . | grep '"accepted": false' | grep -c -E '"rule": "(<rule>|<rule>)"'
```

It must print `0`. (`grep -c` exits 1 when it prints `0`; judge it by the
number it prints.)

---

## Task 1: Treat an explicit null in the agent stream as empty

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** Implementation (`get-container-default-then-method-call`); Error handling (behaviour changes)

**Technical Goal:** Stop a JSON `null` for `content`, `event`, `content_block` or `delta` in the agent's stream from raising `AttributeError` in `process_line`.

**Subtasks:**

- [x] In `src/tests/test_iteration.py`, add one test per site: a stream line whose `message.content`, `event`, `event.content_block` or `event.delta` is `null` is processed without raising, and handled as the empty case is today. Run them and see each fail
- [x] In `src/ralphlib/iteration.py`, change each `x = d.get(k, {})` / `d.get(k, [])` flagged by the rule to `d.get(k) or {}` / `d.get(k) or []`
- [x] Run the new tests and see them pass

**Acceptance Criteria:**

- [x] Each new test fails before the change and passes after it
- [x] Existing `process_line` tests still pass

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_iteration.py` passes
- [x] The per-rule audit check for `get-container-default-then-method-call` prints `0`

**Notes:**

- Key files: `src/ralphlib/iteration.py` (sites near lines 665, 924, 931, 942 on 2026-10-31), `src/tests/test_iteration.py`

---

## Task 2: Narrow the broad excepts

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** Implementation (`silent-broad-except`); Error handling (behaviour changes)

**Technical Goal:** Catch only the errors each handler expects, so anything else propagates as `AGENTS.md` asks, and log the fetch failure.

**Subtasks:**

- [x] In `src/tests/test_giter.py`, add tests: a fetch raising `git.GitCommandError` prints the console message, logs a `loguru` warning and returns `False`; a fetch raising `RuntimeError` propagates. Run them and see the new ones fail
- [x] In `src/ralphlib/giter.py`, change `except Exception as e:` around `origin.fetch()` to `except git.GitCommandError as e:` and add `loguru.logger.warning(...)` beside the console print
- [x] In `src/tests/test_hooks.py`, add a test that a task-file name whose last `-` part is not a number gives task file number `0`
- [x] In `src/ralphlib/hooks.py`, change the bare `except:` around `int(name_parts[-1])` to `except ValueError:`
- [x] Run the new tests and see them pass

**Acceptance Criteria:**

- [x] A `git.GitCommandError` from fetch still returns `False`, and now also logs a warning
- [x] Any other exception from fetch propagates
- [x] A non-numeric task-file suffix still gives `0`

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_giter.py src/tests/test_hooks.py` passes
- [x] The per-rule audit check for `silent-broad-except` prints `0`

**Notes:**

- Key files: `src/ralphlib/giter.py` (near line 142 on 2026-10-31), `src/ralphlib/hooks.py` (near line 126)
- The fetch message stays interpolated for now; Task 6 decides its marker under `except-interpolation`

---

## Task 3: Freeze the read-only module maps and accept the runtime caches

**Status:** done
**Priority:** medium
**Complexity:** medium
**Spec Reference:** API (`default_settings()`, type maps); Implementation (`mutable-module-level-exported`); Error handling (`load_settings` theme not shared)

**Technical Goal:** Remove exported mutable module state that is meant to be constant, and record why the runtime caches stay mutable.

**Subtasks:**

- [x] In `src/tests/test_settings.py`, add a test that two `load_settings` calls return `theme` dicts that are not the same object, and that changing one leaves the other unchanged. Run it and see it fail
- [x] In `src/ralphlib/settings.py`, replace the `default_settings` dict with `def default_settings() -> dict[str, typing.Any]` returning a fresh dict each call (nested `theme` included), with the docstring in the spec's API section; `load_settings` calls it
- [x] Update `src/tests/test_settings.py` (patch the function, for example with `return_value`) and `src/tests/test_looper.py` (`ralphlib.settings.default_settings()`)
- [x] In `src/ralphlib/types.py`, wrap `message_type_to_str` and `ralpher_event_type_to_str` in `types.MappingProxyType`
- [x] Add `# auditme: accept[mutable-module-level-exported] process-lifetime cache, mutated at run time; tests reset it` on `processed_hooks` and `seen_task_ids` in `src/ralphlib/hooks.py` and `log_file_cache` in `src/ralphlib/logger.py`

**Acceptance Criteria:**

- [x] The new theme test passes
- [x] Printer and hook tests that read the type maps pass unchanged
- [x] The three caches show `accepted: true` in the checker output, with the marker's reason

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_settings.py src/tests/test_looper.py src/tests/test_printer.py src/tests/test_hooks.py src/tests/test_logger.py` passes
- [x] The per-rule audit check for `mutable-module-level-exported` prints `0`

**Notes:**

- Key files: `src/ralphlib/settings.py`, `src/ralphlib/types.py`, `src/ralphlib/hooks.py`, `src/ralphlib/logger.py`
- `MappingProxyType` cannot be deep-copied; that is why `default_settings` becomes a function (review-1 item 1)

---

## Task 4: Remove the duplicate slug helpers and the clean-check shims

**Status:** done
**Priority:** medium
**Complexity:** small
**Spec Reference:** API (Removed); Implementation (`paired-sibling-helpers` source part, `passthrough-shim`)

**Technical Goal:** Give each helper one owner, and call `is_working_tree_clean` directly.

**Subtasks:**

- [x] Delete `slugify` and `task_file_slug` from `src/ralphlib/iteration.py`; its callers use `ralphlib.templater.task_file_slug`
- [x] Move the `slugify` and `task_file_slug` tests from `src/tests/test_iteration.py` to `src/tests/test_templater.py`, targeting `ralphlib.templater`
- [x] Delete `is_clean_strict` and `is_clean_no_untracked` from `src/ralphlib/giter.py`; `giter.py` calls `is_working_tree_clean(repo, include_untracked=True)`
- [x] Change `src/tests/test_giter.py` to call `is_working_tree_clean` with `include_untracked=True` and `False` where it called the shims

**Acceptance Criteria:**

- [x] `grep -rn -E 'iteration\.(slugify|task_file_slug)|is_clean_strict|is_clean_no_untracked' src` prints nothing
- [x] The moved tests pass against `ralphlib.templater`

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_iteration.py src/tests/test_templater.py src/tests/test_giter.py` passes
- [x] The per-rule audit check for `passthrough-shim` prints `0`, and the checker reports no `paired-sibling-helpers` hit in `src/ralphlib/`

**Notes:**

- Key files: `src/ralphlib/iteration.py`, `src/ralphlib/templater.py`, `src/ralphlib/giter.py`
- The `make_options` `paired-sibling-helpers` hits are Task 5's

---

## Task 5: Tidy the test modules

**Status:** done
**Priority:** medium
**Complexity:** medium
**Spec Reference:** API (`tests.helpers.make_options`); Implementation (`paired-sibling-helpers` test part, `literal-duplication`, `mutable-store-without-copy`, `leading-underscore-binding`, `leading-underscore-def-class`)

**Technical Goal:** Share the identical test helpers, name repeated literals once, and drop the underscore names.

**Subtasks:**

- [x] Create `src/tests/helpers.py` with one function per group of identical `make_options` bodies (as of 2026-10-31): `make_options(**kwargs)` loading settings (`test_giter.py`, `test_printer.py`, `test_process_termination.py`, `test_signals.py`); `make_plain_options(**kwargs)` without settings (`test_iteration.py`, `test_logger.py`, `test_state.py`); `make_options_with_settings(**kwargs)` popping `settings` (`test_hooks.py`, `test_settings.py`). Each fully annotated
- [x] Replace each module's copy with `import tests.helpers` and calls to the shared function; `test_verifier.py` keeps its own, different `make_options`
- [x] Name each repeated tuple once as a module constant: `('README.md',)` in `test_giter.py`, `('claude', '--verbose')` and `('true',)` in `test_iteration.py`, `('echo hi',)` in `test_settings.py`
- [x] In `src/tests/test_looper.py`, `LoopRun.__init__` stores `list(calls)` and `dict(state)`
- [x] In `src/tests/test_process_termination.py`, rename `_fast_poll` to `fast_poll` (and its `usefixtures` uses) and the `_options` / `_context` parameters to `options` / `context`
- [x] In `src/ralphlib/looper.py`, call `ralphlib.signals.GracefulTerminator(options)` without binding it

**Acceptance Criteria:**

- [x] `grep -rn 'def make_options' src/tests` lists only `helpers.py` and `test_verifier.py`
- [x] The signal tests still show Ctrl-C handled during a loop

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_giter.py src/tests/test_printer.py src/tests/test_process_termination.py src/tests/test_signals.py src/tests/test_iteration.py src/tests/test_logger.py src/tests/test_state.py src/tests/test_hooks.py src/tests/test_settings.py src/tests/test_looper.py` passes
- [x] The per-rule audit check for `paired-sibling-helpers|literal-duplication|mutable-store-without-copy|leading-underscore-binding|leading-underscore-def-class` prints `0`

**Notes:**

- Depends on Task 4 (it moves tests out of `test_iteration.py`)
- Check that pytest collects `src/tests/helpers.py` as no tests (it has no `test_` functions) and that `import tests.helpers` resolves under the project's pytest config

---

## Task 6: Exception messages and bare dict annotations

**Status:** done
**Priority:** medium
**Complexity:** small
**Spec Reference:** Implementation (`except-interpolation`, `bare-parametric-annotation`)

**Technical Goal:** Stop duplicating exception text where a traceback already carries it, record why the person-facing messages keep it, and give every `dict` annotation its element types.

**Subtasks:**

- [x] Drop the `{e}` from each message passed to `loguru.logger.exception`: `hooks.py`, `iteration.py` (`run`, `make_context`, `flush_and_close_fd`, `process_line`, `process_task_progress`), `looper.py`, `state.py` (`load_state`)
- [x] Add `# auditme: accept[except-interpolation] <reason>` where the message reaches a person with no traceback, with the reason naming where it goes: `giter.py` fetch message (console), `iteration.py` `log_error` calls (session error log), `state.py` `add_to_state` (also printed to stderr), `verifier.py` `check_stop` (stop-check reason), `bin/install-claude.py` (exit message)
- [x] Change bare `dict` to `dict[str, typing.Any]` in `iteration.py` (`add_unknown_tool`), `options.py` (`settings`), `state.py` (`load_state`, `save_state`, `add_to_state`, `add_to_state_work`), `test_looper.py` (`LoopRun`) and `test_process_termination.py` (`holder`)

**Acceptance Criteria:**

- [x] No `loguru.logger.exception` message interpolates the caught exception
- [x] Every accepted site's marker names where the message goes

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_hooks.py src/tests/test_iteration.py src/tests/test_looper.py src/tests/test_state.py src/tests/test_verifier.py src/tests/test_giter.py src/tests/test_process_termination.py` passes
- [x] The per-rule audit check for `except-interpolation|bare-parametric-annotation` prints `0`

**Notes:**

- If a site does not fit either case (logger with traceback, or a person with none), stop the task as `blocked` and name the site; the spec decided only the cases it lists

---

## Task 7: Accept the remaining by-design hits

**Status:** done
**Priority:** low
**Complexity:** small
**Spec Reference:** Implementation (`non-alphabetical-literal`, `filesystem-envelope-gap`, `stdlib-logging`)

**Technical Goal:** Record, beside the code, why three hits are not defects.

**Subtasks:**

- [x] `src/tests/test_verifier.py` status list: `# auditme: accept[non-alphabetical-literal] status progression; the order is the meaning`
- [x] `src/ralphlib/verifier.py` `except LookupError` in `check_stop`: `# auditme: accept[filesystem-envelope-gap] the next handler catches READ_ERRORS, which holds OSError`
- [x] `bin/install-claude.py` `import logging`: `# auditme: accept[stdlib-logging] runs under the system Python before the project environment, and loguru, exist`

**Acceptance Criteria:**

- [x] Each of the three hits shows `accepted: true` with its reason

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_verifier.py` passes
- [x] The per-rule audit check for `non-alphabetical-literal|filesystem-envelope-gap|stdlib-logging` prints `0`

**Notes:**

- The checker miss behind the `filesystem-envelope-gap` hit is reported in the shared agents repository's auditme `requests.md`, outside this list (spec: Out of scope)

---

## Task 8: Convert from-imports in the library and scripts

**Status:** done
**Priority:** medium
**Complexity:** medium
**Spec Reference:** Implementation (`from-import`)

**Technical Goal:** Use full import paths in `src/ralphlib/` and `bin/`, as the shared import rule asks.

**Subtasks:**

- [x] For each `from X import Y` in `src/ralphlib/*.py` and `bin/*.py`: `from typing import TYPE_CHECKING` becomes `import typing` and `if typing.TYPE_CHECKING:`; `from typing import Any, Annotated, Literal, NoReturn` become `typing.Any` and so on; `from collections.abc import Callable` becomes `collections.abc.Callable`; `from jinja2.sandbox import SandboxedEnvironment` becomes `import jinja2.sandbox` and `jinja2.sandbox.SandboxedEnvironment`
- [x] Each TYPE_CHECKING-only `from ralphlib.options import RalpherOptions` (and `from ralphlib.types import RalpherEventType`) becomes `import ralphlib.options` inside the `typing.TYPE_CHECKING` block, and annotations name `ralphlib.options.RalpherOptions`
- [x] Check that every changed module imports (`uv run python -c "import ralphlib.<module>"` for each)

**Acceptance Criteria:**

- [x] `grep -rn -E '^\s*from \S+ import' src/ralphlib bin --include='*.py' | grep -v __init__.py` prints nothing
- [x] `bin/ralpher.sh --help` still prints the help

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_giter.py src/tests/test_hooks.py src/tests/test_iteration.py src/tests/test_logger.py src/tests/test_looper.py src/tests/test_printer.py src/tests/test_settings.py src/tests/test_signals.py src/tests/test_state.py src/tests/test_templater.py src/tests/test_verifier.py` passes
- [x] The checker reports no unaccepted `from-import` hit in `src/ralphlib/` or `bin/`

**Notes:**

- Python 3.14 evaluates annotations lazily, so a name imported only under `typing.TYPE_CHECKING` is safe in annotations; it is not safe in a runtime expression (`isinstance`, a default value), so check each use
- A runtime import that makes a cycle under the new form: stop as `blocked` and name the cycle

---

## Task 9: Convert from-imports in the tests

**Status:** done
**Priority:** medium
**Complexity:** medium
**Spec Reference:** Implementation (`from-import`)

**Technical Goal:** Use full import paths in `src/tests/`.

**Subtasks:**

- [x] `from unittest.mock import MagicMock, patch` becomes `import unittest.mock` and `unittest.mock.MagicMock` / `unittest.mock.patch`
- [x] `from hypothesis import given, settings, strategies` becomes `import hypothesis` and `hypothesis.given`, `hypothesis.settings`, `hypothesis.strategies`
- [x] `from typing import Any` and `from collections.abc import Iterator` become `typing.Any` and `collections.abc.Iterator`
- [x] `from ralphlib.x import y` becomes `import ralphlib.x` and `ralphlib.x.y` (`test_looper.py`, `test_process_termination.py`, `test_signals.py`)

**Acceptance Criteria:**

- [x] `grep -rn -E '^\s*from \S+ import' src/tests --include='*.py' | grep -v __init__.py` prints nothing

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_hooks.py src/tests/test_iteration.py src/tests/test_logger.py src/tests/test_looper.py src/tests/test_process_termination.py src/tests/test_settings.py src/tests/test_signals.py src/tests/test_state.py src/tests/test_verifier.py` passes
- [x] The per-rule audit check for `from-import` prints `0`

**Notes:**

- Depends on Task 5 (it rewrites the same test files)
- `hypothesis.settings` and the project's `ralphlib.settings` differ; keep each qualified so neither shadows the other

---

## Task 10: Adopt the auditme hooks

**Status:** todo
**Priority:** high
**Complexity:** small
**Spec Reference:** Implementation (hook adoption steps 1-2)

**Technical Goal:** Make every commit run `auditme-changed` and every push run `auditme-all`, now that nothing is unaccepted.

**Subtasks:**

- [ ] Run `python3 ~/.claude/skills/auditme/checks/audit.py . | grep -c '"accepted": false'`. If it does not print `0`, set this task `blocked`, list the hits, and stop: the gate is never enabled over a backlog
- [ ] Resolve the agents revision: `git ls-remote git@github.com:bnomis/agents.git refs/heads/main`, first field. If it fails, set `blocked` and stop
- [ ] Add after the existing repos in `.pre-commit-config.yaml`, with the template's upgrade comment: repo `git@github.com:bnomis/agents.git`, `rev:` that commit, hooks `auditme-changed` and `auditme-all` with `stages: [manual, pre-push]` (the operator allowed this file to change on 2026-10-31)
- [ ] Run `pre-commit install --hook-type pre-commit --hook-type pre-push`
- [ ] Look for a project-local hook, script or `.claude/settings.json` Stop hook that already runs an audit on changed files; if one exists, set `blocked` naming it, for the operator to decide whether to remove it

**Acceptance Criteria:**

- [ ] `pre-commit run auditme-all --hook-stage manual --all-files` passes
- [ ] `.git/hooks/pre-push` exists and calls pre-commit

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks, now including `auditme-changed` (never `--no-verify`)
- [ ] `pre-commit run auditme-all --hook-stage manual --all-files` passes

**Notes:**

- Depends on Tasks 1-9
- `pre-commit install` changes only `.git/hooks`, not tracked files

---

## Task 11: Add the CI workflow

**Status:** todo
**Priority:** medium
**Complexity:** small
**Spec Reference:** Implementation (hook adoption step 3); External dependencies

**Technical Goal:** Run the tests, the commit-time hooks and the whole-tree audit on every push and pull request.

**Subtasks:**

- [ ] Write `.github/workflows/ci.yml` from `~/.claude/skills/project-setup/templates/ci.yml`, with `{{TEST_COMMAND}}` as `uv run pytest`
- [ ] Pin `actions/checkout`, `actions/setup-python` and `astral-sh/setup-uv` to the full commit SHA of the template's tag (`gh api repos/<owner>/<action>/git/ref/tags/<tag>`, dereferencing an annotated tag), with the tag in a trailing comment
- [ ] Check no placeholder remains: `grep -nE '\{\{[A-Z_]+\}\}' .github/workflows/ci.yml` prints nothing

**Acceptance Criteria:**

- [ ] Every `uses:` line names a 40-character SHA
- [ ] The workflow parses: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"` (or `uv run --with pyyaml ...`) exits 0

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] The YAML parse check above exits 0

**Notes:**

- Depends on Task 10
- Do not create the deploy key or secret here; Task 12 is the operator's

---

## Task 12: Operator: deploy key, secret and a passing CI run

**Status:** todo
**Priority:** medium
**Complexity:** small
**Spec Reference:** Implementation (hook adoption step 4); Acceptance (CI passes)

**Technical Goal:** Give CI read-only access to the agents repository and see the workflow pass. This changes GitHub, so an operator session does it, not an unattended run.

**Subtasks:**

- [ ] Run `gh secret list` and look for `AGENTS_DEPLOY_KEY`. If it is missing, set this task `blocked` with the note "operator: run the project-setup deploy-key steps, then push the branch", and stop
- [ ] Operator session (not the unattended run): run the `project-setup` skill's deploy-key steps, each confirmed before it runs - generate the key in a `mktemp -d` scratch directory, `gh repo deploy-key add ... --repo bnomis/agents --title ralpher`, `gh secret set AGENTS_DEPLOY_KEY --repo <owner>/ralpher < <key>`, then delete both key files and the directory. The private key is never printed
- [ ] Operator: push the branch, then set this task back to `todo` and restart the list
- [ ] Run `gh run list --workflow ci.yml --limit 1 --json conclusion,headSha`. If the run for the pushed head is not `success`, set `blocked` naming the failing step and stop

**Acceptance Criteria:**

- [ ] `gh secret list` shows `AGENTS_DEPLOY_KEY`
- [ ] The latest `ci.yml` run on the pushed head concluded `success`

**Definition of Done:**

- [ ] `gh run list --workflow ci.yml --limit 1 --json conclusion` shows `success`

**Notes:**

- Depends on Task 11
- The deploy key and secret commands come from the shared `project-setup` skill; they need the operator's GitHub credentials

---

## Task 13: Document the gates and close the spec

**Status:** todo
**Priority:** medium
**Complexity:** small
**Spec Reference:** Implementation (hook adoption step 5); Acceptance

**Technical Goal:** Say in `AGENTS.md` what the gates are, and record the work as finished.

**Subtasks:**

- [ ] In `AGENTS.md` under "Coding standards", add that `ruff check`, `ruff format` and the auditme hooks run on every commit, the whole-tree audit on every push and in CI, and that a hit is fixed or accepted with `# auditme: accept[<rule>] <reason>`; leave `.pre-commit-config.yaml` under "Do not modify"
- [ ] Add `src/tests/helpers.py` to the project structure tree in `AGENTS.md`
- [ ] Set the spec's `**Status:**` to `implemented`
- [ ] Create `DONE.md` with a `# Done` title and one line saying it holds finished `TODO.md` items, oldest first. Move the `TODO.md` item "The auditme checker is not adopted here, so its hits accumulate unrecorded" to the end of `DONE.md`: append its heading and body unchanged, then `Done: <YYYY-MM-DD> - agents/specs/auditme-adoption/spec.md, agents/tasks/auditme-adoption/tasks-1.md.` Remove it from `TODO.md`
- [ ] Take the baseline `TODO.md` from the commit that added this task list: `git show $(git log --diff-filter=A --format=%H -- agents/tasks/auditme-adoption/tasks-1.md):TODO.md > <scratch>/todo-before.md`

**Acceptance Criteria:**

- [ ] `python3 ~/.claude/skills/auditme/checks/audit.py . | grep -c '"accepted": false'` prints `0`
- [ ] `TODO.md` holds no item for this work, and `DONE.md` ends with it and its `Done:` line

**Definition of Done:**

- [ ] `pre-commit run --all-files` passes
- [ ] `pre-commit run auditme-all --hook-stage manual --all-files` passes
- [ ] `uv run pytest` passes (the spec's Acceptance names the full suite, and this list touches every library module)
- [ ] `python3 ~/.claude/skills/todo-review/verify_bodies.py <scratch>/todo-before.md TODO.md DONE.md` exits 0

**Notes:**

- Depends on Task 12 and Task 14

---

## Task 14: Fix three failing tests that predate this task list

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** Acceptance (the full suite passes)

**Technical Goal:** Also make the five `src/tests/test_looper.py` tests that raise the same `ValueError` pass (`test_loop_stops_when_all_tasks_done`, `test_loop_rejects_stop_while_tasks_unfinished`, `test_loop_no_verify_stop_trusts_the_marker`, `test_loop_rejected_stop_on_last_iteration_completes_all_iterations`, `test_loop_stops_and_warns_when_tasks_file_unreadable`; found on 2026-10-31 failing on `6fa5bbe`). Make `test_process_task_progress_suppresses_start_already_announced`, `test_announce_started_tasks_skips_task_the_agent_announced` and `test_announce_started_tasks_prints_start_when_task_goes_in_progress` in `src/tests/test_iteration.py` pass.

**Background:** Found while doing Task 1 on 2026-10-31. All three fail on an unmodified checkout of `8849c60`. Each passes an absolute `tmp_path` task file to `announce_started_tasks` or `process_task_progress`; `ralphlib.verifier.worktree_task_file` then calls `relative_to` against the repository root and raises `ValueError` because the file is outside the repository. The behaviour came in with `fix(iteration): announce task start from tasks file` (`ffa497c`) and `fix(verifier): resolve repo root before relative_to` (`099717c`).

**Subtasks:**

- [x] Decide whether the tests or `worktree_task_file` is wrong: the docstring says `ValueError` propagates when the tasks file is outside the repository, so the likely fix is for the tests to run with `options.cwd` set to a repository that holds the tasks file, or to patch `ralphlib.verifier.worktree_task_file`
- [x] Fix it and run `uv run pytest src/tests/test_iteration.py`

**Acceptance Criteria:**

- [x] The three tests pass, and no other test in `src/tests/test_iteration.py` fails

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_iteration.py` passes

**Notes:**

- Blocks the `uv run pytest src/tests/test_iteration.py` check in Task 1 and the full-suite check in Task 13

---
