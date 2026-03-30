# Tasks: Audit Review 1

**Source:** `agents/audit-reviews/review-1.md`
**Created:** 2026-03-30
**Version:** 1

---

## Task 1: Fix `signals.py` `console_print` calls (missing `options`)

**Status:** done
**Priority:** high
**Complexity:** medium
**Source Reference:** Finding 1

**Technical Goal:** Fix 4 `console_print` calls in `GracefulTerminator.handler` that use the old `(message, message_type)` signature. The function now requires `(options, message, message_type)`. Without this fix, any Ctrl+C or SIGTERM will crash with `TypeError`.

**Subtasks:**

- [x] Decide approach: either (a) pass `options` to `GracefulTerminator.__init__` and store as `self.options`, then pass to `console_print`, or (b) replace `console_print` calls with direct `console.print(message, style=...)` calls since signal handlers should avoid complex state
- [x] Update all 4 `console_print` calls in `signals.py:39-42, 47-50, 58-61, 65-68`
- [x] If approach (a): update `looper.py:24` to pass `options` to `GracefulTerminator(options)`
- [x] Update `test_signals.py` to account for the new constructor signature or changed print calls
- [x] Run `uv run pytest src/tests/test_signals.py` and confirm all tests pass

**Acceptance Criteria:**

- [x] `GracefulTerminator.handler` does not raise `TypeError` when invoked
- [x] All existing signal tests pass
- [x] `uv run ruff check src/ralphlib/signals.py` passes

**Notes:**

- Key files: `src/ralphlib/signals.py`, `src/ralphlib/looper.py`, `src/tests/test_signals.py`
- Approach (b) is simpler and avoids threading `options` into signal handler context, but loses themed styling. Consider which trade-off is acceptable.

---

## Task 2: Fix `giter.py:check_repo_clean` missing `options` in `lines_to_text` calls

**Status:** done
**Priority:** high
**Complexity:** small
**Source Reference:** Finding 2

**Technical Goal:** Fix two `lines_to_text(lines)` calls at `giter.py:77` and `giter.py:86` that are missing the `options` first argument. These will crash with `TypeError` at runtime when the git working tree is dirty or has unpushed commits.

**Subtasks:**

- [x] Change `lines_to_text(lines)` to `lines_to_text(options, lines)` at line 77
- [x] Change `lines_to_text(lines)` to `lines_to_text(options, lines)` at line 86
- [x] Run `uv run ruff check src/ralphlib/giter.py` to confirm no lint issues
- [x] Run `uv run pytest src/tests/test_giter.py` and confirm all tests pass

**Acceptance Criteria:**

- [x] Both `lines_to_text` calls pass `options` as the first argument
- [x] All giter tests pass
- [x] `uv run ruff check src/ralphlib/giter.py` passes

**Notes:**

- Key files: `src/ralphlib/giter.py`
- Straightforward fix, no design decisions needed

---

## Task 3: Add type annotation to `giter.py:check_repo_clean`

**Status:** done
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding 3

**Technical Goal:** Add the missing `RalpherOptions` type annotation to the `options` parameter of `check_repo_clean`. All other functions in the codebase annotate this parameter.

**Subtasks:**

- [x] Change `def check_repo_clean(options, repo: git.Repo) -> None:` to `def check_repo_clean(options: RalpherOptions, repo: git.Repo) -> None:`
- [x] Ensure `RalpherOptions` is available via the existing `TYPE_CHECKING` import block
- [x] Run `uv run ruff check src/ralphlib/giter.py`

**Acceptance Criteria:**

- [x] `check_repo_clean` has full type annotations on all parameters and return type
- [x] Ruff passes

**Notes:**

- Key files: `src/ralphlib/giter.py`
- Can be combined with Task 2 since they touch the same function

---

## Task 4: Add type annotations to `giter.py:YNConfirm.make_prompt`

**Status:** done
**Priority:** low
**Complexity:** small
**Source Reference:** Finding 4

**Technical Goal:** Add type annotations for the `default` parameter and return type on `YNConfirm.make_prompt`. AGENTS.md requires all function signatures to have annotations.

**Subtasks:**

- [x] Check the parent class `rich.prompt.Confirm.make_prompt` for the correct types
- [x] Add annotations to `def make_prompt(self, default: ...) -> ...:` matching the parent signature
- [x] Run `uv run ruff check src/ralphlib/giter.py`

**Acceptance Criteria:**

- [x] `make_prompt` has full type annotations
- [x] Ruff passes

**Notes:**

- Key files: `src/ralphlib/giter.py`
- Can be combined with Tasks 2 and 3 since they all touch `giter.py`

---

## Task 5: Update `AGENTS.md` project structure

**Status:** todo
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding 5, Finding 6

**Technical Goal:** Update the project structure tree in `AGENTS.md` to reflect the actual directory layout. Currently missing ~8 source modules, ~10 test files, and 2 bin scripts.

**Subtasks:**

- [ ] Run `ls` on `src/ralphlib/`, `src/tests/`, and `bin/` to get current file lists
- [ ] Update the project structure tree in `AGENTS.md:17-37` with all current files in alphabetical order
- [ ] Verify the updated tree matches the actual filesystem

**Acceptance Criteria:**

- [ ] Every `.py` file in `src/ralphlib/` is listed in the project structure
- [ ] Every `test_*.py` file in `src/tests/` is listed
- [ ] Every script in `bin/` is listed
- [ ] Files are in alphabetical order within each directory

**Notes:**

- Key files: `AGENTS.md`

---

## Task 6: Use sandboxed Jinja2 for hook template rendering

**Status:** todo
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding 7

**Technical Goal:** Replace `jinja2.Template` with `jinja2.SandboxedEnvironment` in `hooks.py:preprocess_hook` to mitigate Jinja2 template injection. Hook templates come from settings files which are user-controlled configuration, but sandboxing prevents accidental or malicious access to Python internals.

**Subtasks:**

- [ ] Change `preprocess_hook` to use `jinja2.SandboxedEnvironment().from_string(cmd)` instead of `jinja2.Template(cmd)`
- [ ] Run `uv run pytest src/tests/test_hooks.py` and confirm all tests pass
- [ ] Run `uv run ruff check src/ralphlib/hooks.py`

**Acceptance Criteria:**

- [ ] `preprocess_hook` uses `SandboxedEnvironment` for template rendering
- [ ] Existing hook tests pass unchanged
- [ ] Normal template variables still render correctly
- [ ] Ruff passes

**Notes:**

- Key files: `src/ralphlib/hooks.py`, `src/tests/test_hooks.py`
- `jinja2.SandboxedEnvironment` is part of the `jinja2` package already in dependencies, no new dep needed

---
