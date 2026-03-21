# Tasks: Test Plan 1

**Source:** `agents/test-plans/plan-1.md`
**Created:** 2026-03-21
**Version:** 1

---

## Task 1: Test hooks.py

**Status:** todo
**Priority:** high
**Complexity:** medium
**Source Reference:** Gap 1

**Technical Goal:** Create `src/tests/test_hooks.py` to cover the event dispatching, template preprocessing, and hook execution logic in `ralphlib/hooks.py`.

**Subtasks:**

- [ ] Create `src/tests/test_hooks.py`
- [ ] Test `event` returns early when no hooks configured in settings
- [ ] Test `event` returns early when event type not in hooks dict
- [ ] Test `event` calls `preprocess_hook` and `run_hook` for matching event type
- [ ] Test `event` skips template preprocessing when `hook_templates` is False
- [ ] Test `event` calls `run_hook` for each command in the hook list
- [ ] Test `preprocess_hook` renders jinja2 template with context
- [ ] Test `preprocess_hook` passes through plain strings without templates
- [ ] Test `make_context` includes event_type, iterations, datetime fields, and time_epoch
- [ ] Test `make_context` includes task_file when set
- [ ] Test `make_context` merges event_context into result
- [ ] Test `run_hook` calls subprocess.Popen with correct args (mock Popen)
- [ ] Test `run_hook` logs exception on subprocess failure

**Acceptance Criteria:**

- [ ] All tests pass with `uv run pytest src/tests/test_hooks.py`
- [ ] `event` branching paths (no hooks, wrong event type, templates on/off) each have a test
- [ ] `preprocess_hook` tested as pure function
- [ ] `run_hook` tested with mocked subprocess

**Notes:**

- Key files: `src/ralphlib/hooks.py`
- Mock `subprocess.Popen` and `loguru.logger` to avoid side effects
- Use `make_options` helper with settings dict containing hooks config
- `make_context` contains time-dependent values — freeze or assert on type/presence rather than exact values

---

## Task 2: Test iteration.py pure functions — slugify, task_file_slug, add_worktree_arg

**Status:** todo
**Priority:** high
**Complexity:** small
**Source Reference:** Gaps 2, 3, 4

**Technical Goal:** Add tests for `slugify`, `task_file_slug`, and `add_worktree_arg` to the existing `src/tests/test_iteration.py`.

**Subtasks:**

- [ ] Test `slugify` lowercases input
- [ ] Test `slugify` replaces non-alphanumeric chars with hyphens
- [ ] Test `slugify` strips leading/trailing hyphens
- [ ] Test `slugify` collapses consecutive special chars into single hyphen
- [ ] Test `slugify` returns empty string for empty input
- [ ] Add hypothesis test for `slugify` — output contains only `[a-z0-9-]` and no leading/trailing hyphens
- [ ] Test `task_file_slug` with path having 2+ parts uses parent-stem
- [ ] Test `task_file_slug` with single-part path uses stem only
- [ ] Test `add_worktree_arg` appends `--worktree` when `options.worktree` is True
- [ ] Test `add_worktree_arg` appends task file slug when task_file is set
- [ ] Test `add_worktree_arg` does not add `--worktree` if already present
- [ ] Test `add_worktree_arg` does not add `-w` if already present
- [ ] Test `add_worktree_arg` is a no-op when `options.worktree` is False

**Acceptance Criteria:**

- [ ] All tests pass with `uv run pytest src/tests/test_iteration.py -k "slugify or task_file_slug or add_worktree_arg"`
- [ ] Hypothesis test for `slugify` uses `@settings(max_examples=20, deadline=10000)`

**Notes:**

- Key files: `src/ralphlib/iteration.py`, `src/tests/test_iteration.py`
- These are all pure functions — no mocking needed

---

## Task 3: Test iteration.py process_user

**Status:** todo
**Priority:** high
**Complexity:** small
**Source Reference:** Gap 5

**Technical Goal:** Add direct tests for `process_user` to `src/tests/test_iteration.py`, covering the deeply nested branching that extracts background tool IDs from user tool_result messages.

**Subtasks:**

- [ ] Test `process_user` with matching `tool_use_id` in `background_tools` extracts and stores background task ID via regex
- [ ] Test `process_user` with `tool_use_id` not in `background_tools` is a no-op
- [ ] Test `process_user` with empty message returns `NONE`
- [ ] Test `process_user` with non-user role returns `NONE`
- [ ] Test `process_user` with `tool_result` type but no regex match is a no-op
- [ ] Test `process_user` always returns `(NONE, line)`

**Acceptance Criteria:**

- [ ] All tests pass with `uv run pytest src/tests/test_iteration.py -k "process_user"`
- [ ] Each branching path in `process_user` has at least one test

**Notes:**

- Key files: `src/ralphlib/iteration.py`, `src/tests/test_iteration.py`
- Pre-populate `context.background_tools` for tests that need matching tool_use_ids
- Use the `tool_id_regex` pattern to construct valid test input

---

## Task 4: Test settings.py

**Status:** todo
**Priority:** high
**Complexity:** small
**Source Reference:** Gap 6

**Technical Goal:** Create `src/tests/test_settings.py` to cover settings loading and merging logic.

**Subtasks:**

- [ ] Create `src/tests/test_settings.py`
- [ ] Test `load_settings_from_file` with non-existent file is a no-op (settings unchanged)
- [ ] Test `load_settings_from_file` with valid JSON file merges into options.settings
- [ ] Test `load_settings_from_file` overwrites existing keys on conflict
- [ ] Test `load_settings` applies default settings, then home config, then custom file in order
- [ ] Test `load_settings` with no settings_file only loads home config
- [ ] Test `load_settings` with settings_file overrides home config values

**Acceptance Criteria:**

- [ ] All tests pass with `uv run pytest src/tests/test_settings.py`
- [ ] File merging precedence (default → home → custom) is verified

**Notes:**

- Key files: `src/ralphlib/settings.py`
- Use `tmp_path` for creating test JSON files
- Mock or override the `~/.ralpher/settings.json` path to avoid depending on the real home directory

---

## Task 5: Test giter.py

**Status:** todo
**Priority:** medium
**Complexity:** medium
**Source Reference:** Gap 7

**Technical Goal:** Create `src/tests/test_giter.py` to cover the git helper functions. Focus on pure/testable functions; skip interactive prompt functions (`check_git`, `check_repo_clean`).

**Subtasks:**

- [ ] Create `src/tests/test_giter.py`
- [ ] Test `discover_repo_path` returns `git.Repo` for a valid git repo (use `tmp_path` + `git.Repo.init`)
- [ ] Test `discover_repo_path` returns `None` for a non-git directory
- [ ] Test `is_git_repo` returns `True` for a valid git repo
- [ ] Test `is_git_repo` returns `False` for a non-git directory
- [ ] Test `is_working_tree_clean` returns `True` for clean repo
- [ ] Test `is_working_tree_clean` returns `False` for repo with modified file
- [ ] Test `is_working_tree_clean` with `include_untracked=False` ignores untracked files
- [ ] Test `is_working_tree_clean` with `include_untracked=True` detects untracked files
- [ ] Test `is_clean_strict` delegates correctly (includes untracked)
- [ ] Test `is_clean_no_untracked` delegates correctly (excludes untracked)
- [ ] Test `get_upstream_branch` returns `None` for detached HEAD
- [ ] Test `get_upstream_branch` returns `None` when no tracking branch set
- [ ] Test `lines_to_text` returns a `rich.text.Text` with joined lines

**Acceptance Criteria:**

- [ ] All tests pass with `uv run pytest src/tests/test_giter.py`
- [ ] Tests use temporary git repos (not the project repo)

**Notes:**

- Key files: `src/ralphlib/giter.py`
- Use `tmp_path` with `git.Repo.init()` to create isolated test repos
- `has_unpushed_commits` requires a remote, which is harder to set up in tests — consider skipping or mocking
- Mark tests that create git repos as potentially slow if they take >10s

---

## Task 6: Test logger.py — state_lock_file and init

**Status:** todo
**Priority:** medium
**Complexity:** small
**Source Reference:** Gaps 8, 9

**Technical Goal:** Add tests for `state_lock_file` and `init` to the existing `src/tests/test_logger.py`.

**Subtasks:**

- [ ] Test `state_lock_file` returns `None` when `options.state` is not set
- [ ] Test `state_lock_file` prepends logdir and appends `.lock` when both are set
- [ ] Test `state_lock_file` returns plain path with `.lock` when logdir is not set
- [ ] Test `init` creates log directory when logdir is set (use `tmp_path`)
- [ ] Test `init` is a no-op when logdir is not set

**Acceptance Criteria:**

- [ ] All tests pass with `uv run pytest src/tests/test_logger.py`
- [ ] `state_lock_file` has parity with `state_file` test coverage

**Notes:**

- Key files: `src/ralphlib/logger.py`, `src/tests/test_logger.py`
- Use `tmp_path` for `init` tests to verify directory creation

---

## Task 7: Test printer.py — type_to_style

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Gap 10

**Technical Goal:** Create `src/tests/test_printer.py` to cover the `type_to_style` mapping function.

**Subtasks:**

- [ ] Create `src/tests/test_printer.py`
- [ ] Test each defined `MessageType` maps to expected style string (parametrize)
- [ ] Test fallback to `'grey30'` for an unknown/unmapped message type (e.g. `NONE`, `CONTENT_START`)

**Acceptance Criteria:**

- [ ] All tests pass with `uv run pytest src/tests/test_printer.py`
- [ ] Every `MessageType` that has a defined style is verified

**Notes:**

- Key files: `src/ralphlib/printer.py`
- Pure function — no mocking needed

---

## Completion checklist

- [x] Every gap from plan-1.md is covered by at least one task
- [x] No task is so large it should be split further
- [x] Dependencies between tasks are explicitly stated (none in this case — all independent)
- [x] Existing completed work is marked as done (all prior test tasks in tasks-1.md are done)
- [x] Task order respects dependency chains (high priority first, then medium, then low)
- [x] Prior task files were reviewed to avoid duplicating already-planned work
