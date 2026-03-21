# Test Plan 1

**Date:** 2026-03-21
**Scope:** full

## Summary

Of 14 source modules, 7 have test files with good coverage (`iteration`, `logger`, `looper`, `signals`, `state`, `templater`, `process_termination`). Four modules with non-trivial logic have no tests at all: `hooks`, `settings`, `giter`, and `printer`. Additionally, several pure functions in `iteration.py` (`slugify`, `task_file_slug`, `add_worktree_arg`, `process_user`) lack dedicated tests despite having meaningful branching logic.

## Gaps

### Gap 1: hooks.py — no tests

- **Module:** `src/ralphlib/hooks.py`
- **Function(s):** `event`, `make_context`, `preprocess_hook`, `run_hook`
- **Test file:** missing
- **What's missing:** Entire module untested. `event` has branching logic (missing hooks, unknown event types, template toggle). `preprocess_hook` is a pure function suitable for direct testing. `make_context` builds a dict with timestamps and options.
- **Suggested approach:** pytest
- **Priority:** high

### Gap 2: iteration.py — slugify

- **Module:** `src/ralphlib/iteration.py`
- **Function(s):** `slugify`
- **Test file:** `src/tests/test_iteration.py` (existing)
- **What's missing:** `slugify` is a pure function with regex substitution, stripping, and lowercasing — no tests exist. Edge cases: empty string, leading/trailing special chars, consecutive special chars.
- **Suggested approach:** hypothesis (well-defined string input domain)
- **Priority:** high

### Gap 3: iteration.py — task_file_slug

- **Module:** `src/ralphlib/iteration.py`
- **Function(s):** `task_file_slug`
- **Test file:** `src/tests/test_iteration.py` (existing)
- **What's missing:** Pure function with path decomposition and a branch on path depth. No tests.
- **Suggested approach:** pytest
- **Priority:** high

### Gap 4: iteration.py — add_worktree_arg

- **Module:** `src/ralphlib/iteration.py`
- **Function(s):** `add_worktree_arg`
- **Test file:** `src/tests/test_iteration.py` (existing)
- **What's missing:** Branching logic: skip if already present (`--worktree` or `-w`), append `--worktree`, optionally append task file slug. No tests.
- **Suggested approach:** pytest
- **Priority:** high

### Gap 5: iteration.py — process_user

- **Module:** `src/ralphlib/iteration.py`
- **Function(s):** `process_user`
- **Test file:** `src/tests/test_iteration.py` (existing)
- **What's missing:** Only tested indirectly via `process_line` dispatch. Deeply nested branching to extract background tool IDs from user tool_result messages. Needs direct tests for: matching tool_use_id in background_tools, regex extraction of background task ID, and no-op paths.
- **Suggested approach:** pytest
- **Priority:** high

### Gap 6: settings.py — no tests

- **Module:** `src/ralphlib/settings.py`
- **Function(s):** `load_settings`, `load_settings_from_file`
- **Test file:** missing
- **What's missing:** `load_settings_from_file` reads JSON from disk and merges into options.settings. `load_settings` chains default → home config → custom file. No coverage for: missing file (no-op), valid file merging, override precedence.
- **Suggested approach:** pytest (using tmp_path for file fixtures)
- **Priority:** high

### Gap 7: giter.py — pure functions

- **Module:** `src/ralphlib/giter.py`
- **Function(s):** `discover_repo_path`, `is_git_repo`, `is_working_tree_clean`, `is_clean_strict`, `is_clean_no_untracked`, `has_unpushed_commits`, `get_upstream_branch`
- **Test file:** missing
- **What's missing:** All git helper functions lack tests. `discover_repo_path` and `is_git_repo` can be tested against real tmp repos. The `is_clean_*` and `has_unpushed_commits` functions have branching worth covering. `check_git` and `check_repo_clean` require interactive prompts and are lower priority.
- **Suggested approach:** pytest (using tmp_path with git.Repo.init)
- **Priority:** medium

### Gap 8: logger.py — state_lock_file

- **Module:** `src/ralphlib/logger.py`
- **Function(s):** `state_lock_file`
- **Test file:** `src/tests/test_logger.py` (existing)
- **What's missing:** `state_lock_file` mirrors `state_file` logic but appends `.lock`. Not tested. Three branches: state not set → None, with logdir, without logdir.
- **Suggested approach:** pytest
- **Priority:** medium

### Gap 9: logger.py — init

- **Module:** `src/ralphlib/logger.py`
- **Function(s):** `init`
- **Test file:** `src/tests/test_logger.py` (existing)
- **What's missing:** `init` creates the log directory. Not tested. Two branches: logdir set (creates dir), logdir not set (no-op).
- **Suggested approach:** pytest (using tmp_path)
- **Priority:** medium

### Gap 10: printer.py — type_to_style

- **Module:** `src/ralphlib/printer.py`
- **Function(s):** `type_to_style`
- **Test file:** missing
- **What's missing:** Pure mapping function from MessageType to style string. Not tested. Should verify all defined message types return expected styles and unknown types fall back to default.
- **Suggested approach:** pytest (parametrize over MessageType values)
- **Priority:** low

## Well-covered modules

- **`ralphlib/templater.py`** — 7 tests covering vars, iteration context, error handling, edge cases
- **`ralphlib/state.py`** — 11 tests covering load, save, nested updates, error cases
- **`ralphlib/signals.py`** — 8 tests covering SIGINT, SIGTERM, shutdown state, round-trip
- **`ralphlib/iteration.py`** — 60 tests covering process_line dispatch, process_result, process_assistant, process_stream_event, helper functions, subprocess behavior (gaps above are additive)
- **`ralphlib/looper.py`** — 14 tests covering timedelta_to_readable with hypothesis
- **`ralphlib/types.py`** — Trivial enum definitions, no tests needed
- **`ralphlib/exceptions.py`** — Trivial exception classes, no tests needed
