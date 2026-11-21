# Tasks: Worktree setup

**Spec:** `agents/specs/worktree-setup/spec.md`
**Created:** 2026-11-21
**Version:** 1

The spec was approved on its review page on 2026-11-21, and its three
decisions are recorded in its Decisions section. A decision covers only what
it names: a task that meets a behaviour change the spec does not describe
stops for the user.

Line numbers in this list are as of commit `a362655` (2026-11-21). Earlier
tasks move lines; find code by its function name.

The project has no tool that selects affected tests. Each task runs the test
files it writes and the tests of the modules it changes. The last task runs
every test file that imports a module this list changed.

Every task's Definition of Done checks the task's own commit for the test
files it names, so a test reported but never committed is caught.

---

## Task 1: Validate the `worktree_setup` setting

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** API (`validate_settings`), Error handling, Settings, Tests and documentation

**User Story:** As someone configuring a project for queues, I want a `worktree_setup` setting of the wrong shape to stop the run with a clear error, so that a typo never reaches the agent's prompt.

**Subtasks:**

- [x] Confirm the work has not started: `grep -rnw 'worktree_setup' src/ralphlib` finds nothing; if it finds something, stop the task as `blocked` naming the hit
- [x] Add tests to `src/tests/test_settings.py`: a list of strings passes; a string, a list holding a number, and an object each raise `SettingsError` whose message is `Settings file <path>: worktree_setup must be a list of strings`; a later file's `worktree_setup` replaces an earlier one whole; confirm the new failure tests fail before the change
- [x] In `ralphlib.settings.validate_settings`, reject a `worktree_setup` that is not a list of strings with that message, and update its docstring to name the key

**Acceptance Criteria:**

- [x] A settings file with `"worktree_setup": "uv sync"` stops the run with the `Error:` line and exit status 1

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `git show --stat HEAD` lists `src/tests/test_settings.py`
- [x] `uv run pytest src/tests/test_settings.py` passes

**Notes:**

- Key files: `src/ralphlib/settings.py` (`validate_settings`, `load_settings_from_file`), `src/tests/test_settings.py`

---

## Task 2: Prompts get `worktree_setup`

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** API (`render`), Implementation (Prompt context), Error handling, Tests and documentation

**Technical Goal:** `templater.render` adds `worktree_setup` to the prompt context: a new list copied from `options.settings['worktree_setup']` when `--worktree` is given, else `[]`. `BUILTIN_VARS` gains `worktree_setup`, so `--vars worktree_setup=...` is rejected.

**Subtasks:**

- [x] Add tests to `src/tests/test_templater.py`: with `--worktree` and the setting, a template `{{ worktree_setup | join(',') }}` renders the commands in order; without `--worktree`, or without the setting, it renders empty; `--vars worktree_setup=x` raises `InvalidVarFormatError`; changing the rendered list inside a template does not change `options.settings`
- [x] Add `'worktree_setup'` to `BUILTIN_VARS` in `src/ralphlib/templater.py`, keeping the tuple alphabetical
- [x] In `render`, set `context['worktree_setup']` as the spec says, and update the context's type annotation and the docstring

**Acceptance Criteria:**

- [x] The new tests pass, and the existing `render` tests still pass

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `git show --stat HEAD` lists `src/tests/test_templater.py`
- [x] `uv run pytest src/tests/test_templater.py` passes

**Notes:**

- Depends on Task 1 (the tests build options with a valid setting)
- Key files: `src/ralphlib/templater.py` (`BUILTIN_VARS`, `parse_vars`, `render`), `src/tests/test_templater.py`

---

## Task 3: `one-task.md` tells the agent to run the commands

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** Implementation (Prompt text), Tests and documentation

**User Story:** As someone running a queue, I want the agent to set up the worktree's environment before anything else, and to stop rather than borrow another checkout's environment when setup fails, so that its checks run the project's own pinned tools.

**Subtasks:**

- [x] Add tests to `src/tests/test_templater.py` that render `agents/prompts/one-task.md`: with `--worktree` and `worktree_setup: ["uv sync", "pre-commit install"]`, the output lists both commands in order, inside the worktree rules, and names the `blocked` status; with an empty list, without the setting, and without `--worktree`, the output has no setup block
- [x] Add the block the spec's Implementation section gives to `agents/prompts/one-task.md`, inside the `{% if worktree %}` block, after the line about changing to the worktree directory

**Acceptance Criteria:**

- [x] A prompt rendered without the setting is unchanged from before the task (compare against the output at `a362655` in the test or by hand)

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `git show --stat HEAD` lists `src/tests/test_templater.py`
- [x] `uv run pytest src/tests/test_templater.py` passes

**Notes:**

- Depends on Task 2
- Key files: `agents/prompts/one-task.md`, `src/tests/test_templater.py`

---

## Task 4: Warn when a worktree run has no setup

**Status:** todo
**Priority:** medium
**Complexity:** small
**Spec Reference:** API (`warn_missing_worktree_setup`), Implementation (Warning), Tests and documentation

**User Story:** As someone running a queue in a project without `worktree_setup`, I want a warning before the first iteration, so that I know the agent's worktree has no project environment.

**Subtasks:**

- [ ] Add tests to `src/tests/test_looper.py`: `warn_missing_worktree_setup` prints `Warning: no worktree_setup setting; the agent's worktree has no project environment.` to stderr with `--worktree` and no setting, and with an empty list; prints nothing with the setting, or without `--worktree`
- [ ] Add `warn_missing_worktree_setup` to `src/ralphlib/looper.py`, using `loguru.logger.warning` and `ralphlib.printer.console_stderr.print`
- [ ] Call it once in `loop`, after `ralphlib.giter.confirm_git_state(options)` and before the first iteration
- [ ] Check that the end-to-end loop tests in `src/tests/test_looper.py` still pass with the new call

**Acceptance Criteria:**

- [ ] The warning does not stop the run

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_looper.py`
- [ ] `uv run pytest src/tests/test_looper.py` passes

**Notes:**

- Depends on Task 1
- Key files: `src/ralphlib/looper.py` (`loop`), `src/ralphlib/printer.py` (`console_stderr`), `src/tests/test_looper.py`

---

## Task 5: User docs, and close the spec

**Status:** todo
**Priority:** medium
**Complexity:** small
**Spec Reference:** Tests and documentation (User docs), Settings

**Technical Goal:** Document `worktree_setup` in the user guide, mark the spec implemented, move its `TODO.md` item to `DONE.md`, and run the whole-tree checks before the branch merges.

**Subtasks:**

- [ ] `docs/reference/settings.md`: a row for `worktree_setup` in the Keys table (list of strings, no default, what it does, must be safe to repeat)
- [ ] `docs/reference/variables.md`: a `worktree_setup` row under Prompts (the commands with `--worktree`, else an empty list)
- [ ] `docs/guide/worktrees.md`: a section on giving the worktree an environment: the `["uv sync"]` example in `.ralpher/settings.json`, why it matters (a check that falls back to `PATH` sees other tools), the warning, that every iteration's agent runs the commands, and that they must be safe to repeat
- [ ] `docs/guide/prompts.md`: that `one-task.md` shows the commands, and that a custom prompt can use `worktree_setup`
- [ ] Set the spec's `**Status:**` to `implemented`
- [ ] Move the `TODO.md` item "A queue's worktree has no environment, so its audit runs PATH's ruff" to the end of `DONE.md`: append its heading and body unchanged, then `Done: <date> - spec agents/specs/worktree-setup/spec.md, tasks agents/tasks/worktree-setup/tasks-1.md.`, and remove it from `TODO.md`

**Acceptance Criteria:**

- [ ] Every page the spec's User docs list names `worktree_setup`

**Definition of Done:**

- [ ] `pre-commit run --all-files` passes
- [ ] `pre-commit run --hook-stage pre-push auditme-all --all-files` passes
- [ ] `uv run pytest src/tests/test_giter.py src/tests/test_iteration.py src/tests/test_looper.py src/tests/test_options.py src/tests/test_printer.py src/tests/test_ralpher.py src/tests/test_settings.py src/tests/test_templater.py src/tests/test_verifier.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes
- [ ] `python3 ~/.claude/skills/todo-review/verify_bodies.py <baseline> TODO.md DONE.md` exits 0, where `<baseline>` is `TODO.md` as of the commit that added this task list (`git show "$(git log --diff-filter=A --format=%H -- agents/tasks/worktree-setup/tasks-1.md)":TODO.md`)

**Notes:**

- Depends on Tasks 1-4
- The last task: its test run covers every test file that imports a module this list changed

---
