# Audit Review 1

**Date:** 2026-03-30
**Scope:** full

## Summary

The codebase is in good shape overall -- ruff passes cleanly, tests are comprehensive, and the architecture is clear. The main issues are: `signals.py` calls `console_print` with the old (pre-`options`) signature (a runtime bug), `giter.py:check_repo_clean` calls `lines_to_text` without `options` (another runtime bug), `AGENTS.md` project structure is out of date, and `giter.py:check_repo_clean` is missing the `options` type annotation.

## Findings

### Finding 1: `signals.py` calls `console_print` with old signature (missing `options`)

- **Category:** standards / architecture
- **Severity:** high
- **Location:** `src/ralphlib/signals.py:39-68`
- **Description:** `console_print` now requires `(options, message, message_type)` but `GracefulTerminator.handler` calls it as `console_print(message, message_type)` in 4 places (lines 39-42, 47-50, 58-61, 65-68). This will raise a `TypeError` at runtime when a signal is received.
- **Recommendation:** `GracefulTerminator` needs access to `options`. Either pass `options` to `__init__` and store it, or have these calls use `console.print()` directly (since signal handlers shouldn't rely on complex state). Given `looper.py:24` already creates `GracefulTerminator()` with no args, the constructor signature needs updating too.

### Finding 2: `giter.py:check_repo_clean` calls `lines_to_text` without `options`

- **Category:** standards
- **Severity:** high
- **Location:** `src/ralphlib/giter.py:77`
- **Description:** `lines_to_text` was updated to `lines_to_text(options, lines)` but `check_repo_clean` at line 77 calls `lines_to_text(lines)` (missing `options`). This will raise a `TypeError` at runtime when the git working tree is not clean.
- **Recommendation:** Change `lines_to_text(lines)` to `lines_to_text(options, lines)` at line 77.

### Finding 3: `giter.py:check_repo_clean` missing type annotation for `options`

- **Category:** standards
- **Severity:** medium
- **Location:** `src/ralphlib/giter.py:70`
- **Description:** `def check_repo_clean(options, repo: git.Repo) -> None:` -- `options` parameter has no type annotation. All other functions in the codebase annotate `options: RalpherOptions`.
- **Recommendation:** Change to `def check_repo_clean(options: RalpherOptions, repo: git.Repo) -> None:`.

### Finding 4: `giter.py:YNConfirm.make_prompt` missing type annotations

- **Category:** standards
- **Severity:** low
- **Location:** `src/ralphlib/giter.py:21`
- **Description:** `def make_prompt(self, default):` has no type annotations for `default` parameter or return type. AGENTS.md requires all function signatures to have annotations.
- **Recommendation:** Add annotations: `def make_prompt(self, default: bool) -> rich.text.Text:` (or the appropriate return type from rich).

### Finding 5: `AGENTS.md` project structure is outdated

- **Category:** documentation
- **Severity:** medium
- **Location:** `AGENTS.md:17-37`
- **Description:** The project structure section is missing several files that now exist: `exceptions.py`, `hooks.py`, `settings.py`, `signals.py`, `giter.py` in `src/ralphlib/`, and test files `test_giter.py`, `test_hooks.py`, `test_iteration.py`, `test_logger.py`, `test_looper.py`, `test_printer.py`, `test_process_termination.py`, `test_settings.py`, `test_signals.py`, `test_state.py` in `src/tests/`. Also missing `bin/ralpherun.sh` and `bin/rrq.sh`.
- **Recommendation:** Update the project structure tree in `AGENTS.md` to reflect the actual directory layout.

### Finding 6: `AGENTS.md` tests section only lists `test_templater.py`

- **Category:** documentation
- **Severity:** medium
- **Location:** `AGENTS.md:29-31`
- **Description:** The tests directory listing shows only `test_templater.py` but there are now 11 test files. This is misleading.
- **Recommendation:** Update to list all test files, or use a pattern like `test_*.py` to indicate the naming convention.

### Finding 7: No tests for `hooks.run_hook` command injection surface

- **Category:** security
- **Severity:** medium
- **Location:** `src/ralphlib/hooks.py:62-64`
- **Description:** `preprocess_hook` renders user-controlled Jinja2 templates from `event_context` directly into shell commands, which are then passed to `shlex.split` and `subprocess.Popen`. If `event_context` values contain shell metacharacters or Jinja2 injection payloads, this could lead to arbitrary command execution. The `shlex.split` mitigates some risk but Jinja2 template injection (e.g. `{{ self.__class__.__mro__[1].__subclasses__() }}`) is a known attack vector.
- **Recommendation:** Consider using `jinja2.SandboxedEnvironment` instead of `jinja2.Template` for hook preprocessing, or document that hook templates are trusted configuration only.

### Finding 8: `looper.py` uses `open()` instead of `pathlib` for file reads

- **Category:** standards
- **Severity:** low
- **Location:** `src/ralphlib/looper.py:38, 57`
- **Description:** `open(options.prompt, 'r', encoding='utf-8')` and `open(options.task_file, 'r', encoding='utf-8')` use bare `open()`. The rest of the codebase uses `pathlib.Path.open()`. Not a bug but inconsistent.
- **Recommendation:** Convert to `pathlib.Path(options.prompt).open(...)` for consistency, or leave as-is since it works fine.

### Finding 9: `iteration.py` unused `options` parameter in several write functions

- **Category:** standards
- **Severity:** low
- **Location:** `src/ralphlib/iteration.py:331,337,344,351,357,364,370`
- **Description:** Functions `write_progress`, `write_progress_lines`, `write_progress_eol`, `write_error`, `write_error_eol`, `write_stdout`, `write_stderr` all accept `options: RalpherOptions` but never use it. The parameter exists for API consistency but could be misleading.
- **Recommendation:** This is likely intentional for API symmetry with `print_*` counterparts. No action needed, just noting it.

### Finding 10: `state.py:110` re-raises after retry exhaustion but also logs

- **Category:** architecture
- **Severity:** low
- **Location:** `src/ralphlib/state.py:63-69`
- **Description:** `add_to_state` catches exceptions, logs them to both loguru and stderr, then re-raises. The `@tenacity.retry` decorator on `add_to_state_work` will also log on retry. This could result in the same error being logged multiple times during retry attempts.
- **Recommendation:** Consider whether the outer exception handler in `add_to_state` is needed given tenacity's `reraise=True`. If retry exhaustion should be visible, tenacity's `before_sleep` or `after` callbacks might be cleaner.

## Files reviewed

- `src/ralphlib/__init__.py` -- checked: standards (empty, fine)
- `src/ralphlib/types.py` -- checked: standards, security, architecture
- `src/ralphlib/options.py` -- checked: standards, security, architecture
- `src/ralphlib/settings.py` -- checked: standards, security, architecture
- `src/ralphlib/printer.py` -- checked: standards, security, architecture
- `src/ralphlib/logger.py` -- checked: standards, security, performance, architecture
- `src/ralphlib/looper.py` -- checked: standards, security, performance, architecture
- `src/ralphlib/exceptions.py` -- checked: standards, architecture
- `src/ralphlib/signals.py` -- checked: standards, security, architecture
- `src/ralphlib/hooks.py` -- checked: standards, security, architecture
- `src/ralphlib/state.py` -- checked: standards, security, performance, architecture
- `src/ralphlib/templater.py` -- checked: standards, security, architecture
- `src/ralphlib/iteration.py` -- checked: standards, security, performance, architecture
- `src/ralphlib/giter.py` -- checked: standards, security, architecture
- `src/tests/__init__.py` -- checked: standards (empty, fine)
- `src/tests/test_templater.py` -- checked: standards, testing
- `src/tests/test_looper.py` -- checked: standards, testing
- `src/tests/test_signals.py` -- checked: standards, testing
- `src/tests/test_iteration.py` -- checked: standards, testing
- `src/tests/test_state.py` -- checked: standards, testing
- `src/tests/test_settings.py` -- checked: standards, testing
- `src/tests/test_hooks.py` -- checked: standards, testing
- `src/tests/test_logger.py` -- checked: standards, testing
- `src/tests/test_process_termination.py` -- checked: standards, testing
- `src/tests/test_printer.py` -- checked: standards, testing
- `src/tests/test_giter.py` -- checked: standards, testing
- `AGENTS.md` -- checked: documentation
- `README.md` -- checked: documentation
- `pyproject.toml` -- checked: dependencies, standards

## Recommendations

1. **Fix `signals.py` `console_print` calls (high)** -- These will crash at runtime on any signal. Either pass `options` through or use `console.print()` directly.
2. **Fix `giter.py:77` `lines_to_text` call (high)** -- Missing `options` argument will crash when git tree is dirty.
3. **Add type annotation to `check_repo_clean` (medium)** -- Consistency fix.
4. **Update `AGENTS.md` project structure (medium)** -- Significantly outdated.
5. **Consider sandboxed Jinja2 for hooks (medium)** -- Mitigate template injection risk.
6. **Add type annotations to `YNConfirm.make_prompt` (low)** -- Consistency fix.

## Clean categories

- **Coding standards (ruff):** All checks passed, all files formatted correctly
- **Security (hardcoded secrets):** No secrets, API keys, or credentials found in source
- **Dependencies:** All declared in `pyproject.toml`, `uv.lock` committed
- **Performance:** No concerning patterns found
- **Testing:** Comprehensive test coverage across all major modules with both unit and property-based tests
- **Architecture:** Clear module responsibilities, no circular imports detected
