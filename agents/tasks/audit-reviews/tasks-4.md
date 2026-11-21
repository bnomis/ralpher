# Tasks: Audit Review 4

**Source:** `agents/audit-reviews/review-4.md`
**Created:** 2026-11-21
**Version:** 4

Every finding in review-4 was approved, and its three decisions were answered
(untrack `.claude/settings.local.json`, leave the long specs whole, refuse a
test-log path outside the repository), on 2026-11-21; the answers are in the
review's Answers section. The fail-soft sites of Finding 4 and the `loop`
handler of Finding 5 are already dismissed in `agents/audit-reviews/ledger/`.
A decision covers only what it names: a task that meets a behaviour change the
review does not recommend stops for the user.

Line numbers in this list are as of commit `e41c205` (2026-11-21). Earlier
tasks move lines; find code by its function name.

The project has no tool that selects affected tests. Each task runs the test
files it writes and the tests of the modules it changes. The last task runs
every test file that imports a module this list changed.

Every task's Definition of Done checks the task's own commit for the test
files it names, so a test reported but never committed is caught.

---

## Task 1: Order-file I/O errors end `rro` with its error line

**Status:** in-progress
**Priority:** high
**Complexity:** medium
**Source Reference:** Finding 1

**User Story:** As someone running an order with `rro`, I want an unreadable or undecodable order file or test log to end with `rro`'s `{error, message}` line and exit 2, so that the calling command can report it instead of a Python traceback.

**Subtasks:**

- [ ] Add tests to `src/tests/test_order.py`: `read_order`, `set_status` and `set_setting` raise `OrderFormatError` naming the path when the read raises `OSError` (patch `pathlib.Path.read_text` / `read_bytes`) and when the file is not valid UTF-8; `check_test_log` raises `OrderFormatError` when the log read raises `OSError`; a failed write in `set_status` and `set_setting` raises `OrderFormatError`; confirm they fail before the fix
- [ ] Add a test to `src/tests/test_rro.py` that an undecodable order file makes `rro next` print the `{error, message}` line and exit 2
- [ ] In `src/ralphlib/order.py`, add one read helper and one write helper that translate `OSError` and `UnicodeDecodeError` to `OrderFormatError` naming the path (`raise ... from e`), and route every order-file read and write in `read_order`, `set_setting`, `set_status` and the test-log read in `check_test_log` through them
- [ ] In `set_setting`, when the restore write after a failed `read_order` itself fails, raise `OrderFormatError` naming both failures, chained from the restore error, so the original error is not lost
- [ ] Add `OSError` and `UnicodeDecodeError` to the handler at `src/ralphlib/order.py:428` if it still catches only `OrderFormatError` after the helpers land
- [ ] Update the `Raises:` sections of the changed functions

**Acceptance Criteria:**

- [ ] No `read_text`, `read_bytes` or `write_bytes` call in `src/ralphlib/order.py` sits outside the two helpers (`rg -n 'read_text|read_bytes|write_bytes' src/ralphlib/order.py`)
- [ ] The new tests pass

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_order.py` and `src/tests/test_rro.py`
- [ ] `uv run pytest src/tests/test_order.py src/tests/test_rro.py` passes

**Notes:**

- Key files: `src/ralphlib/order.py`, `bin/rro.py` (`main` catches `RalpherError` only; leave it so), `src/tests/test_order.py`, `src/tests/test_rro.py`

---

## Task 2: `rro set-status` refuses line breaks

**Status:** todo
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding 8

**User Story:** As someone running an order, I want `rro set-status` to refuse a status containing a line break and to leave the order file intact on any failed write, so that a bad status cannot break the table or forge a checkpoint line.

**Subtasks:**

- [ ] Add tests to `src/tests/test_order.py`: a status containing `\n` or `\r` raises `OrderFormatError` and leaves the file byte-for-byte unchanged; a write that leaves the file unparseable is restored, as `set_setting`'s tests check
- [ ] In `ralphlib.order.set_status`, refuse a status containing `\r` or `\n` with `OrderFormatError` before writing
- [ ] After the write, re-parse the file with `read_order` and restore the original bytes on `OrderFormatError`, as `set_setting` does
- [ ] Say in `docs/run-order.md` (the `set-status` description) that a status cannot contain a line break

**Acceptance Criteria:**

- [ ] A forged `Checkpoint after X: passed` line cannot be written through `set_status`

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_order.py`
- [ ] `uv run pytest src/tests/test_order.py src/tests/test_rro.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Task 1 (the write helper)
- Key files: `src/ralphlib/order.py` (`set_status`, `replace_cell`, `set_setting`), `docs/run-order.md`

---

## Task 3: The test log stays inside the repository

**Status:** todo
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding 9, Decision 3

**User Story:** As someone running an order, I want an order file whose `test log` setting is absolute or contains `..` to be refused, so that `rro check-log` never reads a file outside the repository.

**Subtasks:**

- [ ] Add tests to `src/tests/test_order.py`: an absolute `test log` path and one containing `..` make `check_test_log` raise `OrderFormatError`; the default path still works
- [ ] In `ralphlib.order.check_test_log` (or where the setting is read), refuse such paths with `OrderFormatError`, matching how `ralphlib.logger.state_path` refuses absolute and `..` paths
- [ ] Document the rule beside the `test log` setting in `docs/run-order.md`

**Acceptance Criteria:**

- [ ] `rro check-log` on such an order prints the `{error, message}` line and exits 2

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_order.py`
- [ ] `uv run pytest src/tests/test_order.py src/tests/test_rro.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Task 1
- Key files: `src/ralphlib/order.py:306`, `src/ralphlib/logger.py` (`state_path`), `docs/run-order.md`

---

## Task 4: Git handlers also catch `OSError`

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Finding 2

**Technical Goal:** The handlers at `src/ralphlib/giter.py:44`, `src/ralphlib/order.py:446` and `:462` catch GitPython's errors but not the `OSError` that reading `.git` from disk can raise. Add it, raising `GitError`.

**Subtasks:**

- [ ] Add tests to `src/tests/test_giter.py` and `src/tests/test_order.py` that an `OSError` from each guarded call (patch the GitPython call) raises `GitError`
- [ ] Add `OSError` to each handler and raise `GitError` from it, keeping each handler's existing behaviour for the errors it already catches
- [ ] Update the `Raises:` sections where they change

**Acceptance Criteria:**

- [ ] Each of the three handlers names `OSError`

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_giter.py` and `src/tests/test_order.py`
- [ ] `uv run pytest src/tests/test_giter.py src/tests/test_order.py` passes

**Notes:**

- Key files: `src/ralphlib/giter.py` (the function at line 44), `src/ralphlib/order.py` (`default_branch`, `decisions_since`)

---

## Task 5: `Popen` handlers cover `SubprocessError`

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Findings 3 and 4

**Technical Goal:** `iteration.process` translates `OSError` from `subprocess.Popen` to `RalpherError` but not `subprocess.SubprocessError`; `hooks.run_hook`'s fail-soft handler also misses it. Cover both, keeping `run_hook` fail-soft.

**Subtasks:**

- [ ] Add a test to `src/tests/test_iteration.py` that a `subprocess.SubprocessError` from `Popen` in `process` raises `RalpherError`
- [ ] Add a test to `src/tests/test_hooks.py` that a `subprocess.SubprocessError` from `Popen` in `run_hook` is logged as a warning and the run carries on
- [ ] Catch `(OSError, subprocess.SubprocessError)` in both handlers

**Acceptance Criteria:**

- [ ] `run_hook` still never raises for a failed hook command

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_iteration.py` and `src/tests/test_hooks.py`
- [ ] `uv run pytest src/tests/test_iteration.py src/tests/test_hooks.py` passes

**Notes:**

- Key files: `src/ralphlib/iteration.py` (`process`), `src/ralphlib/hooks.py` (`run_hook`)
- The fail-soft verdicts for `run_hook`, `claude_worktree_base_ref`, `verify_stop` and `read_tasks` are already dismissed in the ledger; do not change their behaviour

---

## Task 6: Reader-thread log level and `process`'s `Raises`

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Findings 5 and 6

**Technical Goal:** `iteration.process_stdout` and `process_stderr` log an expected `(OSError, LogFileError)` failure with `logger.exception`; log it with `logger.error`, since the error flag already reports the failure. Add `LogFileError` to `iteration.process`'s `Raises:` section.

**Subtasks:**

- [ ] Change `logger.exception` to `logger.error` in the `(OSError, LogFileError)` handlers of `process_stdout` and `process_stderr`, keeping the message and the `set_error` call
- [ ] Update any test in `src/tests/test_iteration.py` that asserts the old level
- [ ] Add `LogFileError` to the `Raises:` section of `process`
- [ ] Leave the handler in `looper.loop` unchanged (review-3 Decision 1)

**Acceptance Criteria:**

- [ ] `rg -n 'logger.exception' src/ralphlib/iteration.py` no longer lists the two reader-thread handlers

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_iteration.py` passes

**Notes:**

- Depends on Task 5 (same module)
- Key files: `src/ralphlib/iteration.py`

---

## Task 7: Names that say they do I/O

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Finding 7

**Technical Goal:** Rename `order.find_root` to `discover_root`, `order.check_test_log` to `read_test_log_verdict` and `rro`'s `check_log` to `read_log_verdict`, and mark `IterationContext.tasks_signature` as run-time state like the other such fields.

**Subtasks:**

- [ ] Rename the three functions and update every caller and test (`bin/rro.py`, `src/tests/test_order.py`, `src/tests/test_rro.py`); the `rro check-log` subcommand name stays
- [ ] Update the run-order spec's API section and test notes for the new names (`agents/specs/run-order/spec.md:211`, `:330` and any other mention)
- [ ] Change the docstring of `IterationContext.tasks_signature` (`src/ralphlib/iteration.py:64`) to start "Set at run time:", as the other run-time fields do

**Acceptance Criteria:**

- [ ] `rg -nw 'find_root|check_test_log|check_log' src bin agents/specs docs claude` finds nothing (records under `agents/audit-reviews/` and earlier task lists keep the old names)

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_order.py src/tests/test_rro.py src/tests/test_iteration.py` passes

**Notes:**

- Depends on Tasks 1-3 (they edit the renamed functions)

---

## Task 8: f-strings in `test_order.py`

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Finding 10

**Technical Goal:** Replace the `.format()` row templates `L1`-`L4`, `CP` and `FINAL` (`src/tests/test_order.py:175-180`) with small functions returning f-strings, as AGENTS.md's string-formatting rule asks.

**Subtasks:**

- [ ] Replace each template with a function taking the status (`def l1(status: str) -> str`), and update every use in the module
- [ ] Leave `src/ralphlib/order.py`'s `.format()` of the user-supplied template alone

**Acceptance Criteria:**

- [ ] `rg -n '\.format\(' src/tests/test_order.py` finds nothing

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_order.py` passes

**Notes:**

- Depends on Task 7 (it edits the same file)

---

## Task 9: Direct and property tests for the untested functions

**Status:** todo
**Priority:** low
**Complexity:** large
**Source Reference:** Finding 11

**Technical Goal:** Give the public functions review-4's T1 list names a direct test, and add the three property tests its T2 list names.

**Subtasks:**

- [ ] Direct tests for the functions with error paths or real branches: `hooks.local_timezone` (its `RalpherError` path), `hooks.fixed_context`, `hooks.last_commit_summary`, `logger.state_path`, `settings.validate_settings`, `order.build_settings`, `order.discover_root`, `order.default_branch`, `state.add_to_state_work`, `iteration.signal_agent` (the `terminate` fallback), `iteration.write_log`, `iteration.read_task_statuses`, `iteration.kill_agent`, `iteration.open_log_file`, `looper.reject_unverified_stop`, and `rro.step_json` with its finished case
- [ ] Direct tests for the rest of the list: `rro.read_log_verdict`, `rro.run`, `iteration.get_tool_input`, `iteration.last_message_type`, `iteration.mark_started`, `iteration.process_system`, `iteration.read_stdout`, `iteration.summary`, `iteration.unmake_context`, `looper.print_cleanup_cmds`, `looper.print_stopping_prompt`, `signals.GracefulTerminator.perform_shutdown`
- [ ] One parametrised test for `iteration.print_error`, `print_error_eol`, `print_progress`, `print_progress_eol` and `print_progress_lines`, quiet and not quiet
- [ ] Hypothesis tests: `hooks.fixed_context` (basename equals stem plus suffix; `cwd` joined with the relative path gives back the task file when it is under `cwd`); `order.replace_cell` (the replaced cell reads back through `split_cells` as the new text, bars included, every other cell unchanged); `order.split_cells` (round trip of a row built from cells, escaped bars included)

**Acceptance Criteria:**

- [ ] Each function named above is called by name in at least one test

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists every test file the task edits
- [ ] `uv run pytest src/tests/test_hooks.py src/tests/test_logger.py src/tests/test_settings.py src/tests/test_order.py src/tests/test_state.py src/tests/test_iteration.py src/tests/test_looper.py src/tests/test_rro.py src/tests/test_signals.py` passes

**Notes:**

- Depends on Task 7 (renamed functions) and Task 8 (`test_order.py`)
- A test that finds a real defect stops the task for the user; do not change behaviour here

---

## Task 10: The user docs say what the code does

**Status:** todo
**Priority:** high
**Complexity:** small
**Source Reference:** Finding 14

**User Story:** As someone reading the ralpher docs, I want the stop conditions, exit reasons and cleanup output to match what ralpher does and prints, so that I can rely on them.

**Subtasks:**

- [ ] `docs/concepts.md` "Ending the loop": add the stop on an exception in an iteration (exit reason `exception during iteration <i>`, exit status 1), and say that an I/O failure on the output reader threads also counts as an error
- [ ] `docs/guide/logs.md` "The state file": add `exception during iteration <i>` to the `exit_reason` values
- [ ] `docs/getting-started.md` and `docs/guide/worktrees.md`: show the cleanup output exactly as an `rrq.sh` run prints it (the `Probable cleanup commands...` header, the two-space indent and the leading `cd <repository root> && \`); produce it by running `bin/ralpher.sh --cleanup --worktree --cwd=<dir> --task-file=<file>` in a scratch repository rather than writing it by hand
- [ ] `docs/run-order.md:47`: say `agents/tasks/run-order/example-order.md` holds the same tables, not that it is the same file

**Acceptance Criteria:**

- [ ] Each changed example matches the command output it shows

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Key files: `src/ralphlib/looper.py` (`loop`, `cleanup_cmds`, `print_cleanup_cmds`), `bin/rrq.sh`

---

## Task 11: AGENTS.md matches the tree, and the local settings file is untracked

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Finding 12, Decision 1

**Technical Goal:** Bring the AGENTS.md project structure and tools list up to date, and stop tracking `.claude/settings.local.json`.

**Subtasks:**

- [ ] `git rm --cached .claude/settings.local.json` (the file stays on disk; `~/.gitignore` already ignores it)
- [ ] Add `claude/templates/` (the progress page template) to the AGENTS.md tree beside `claude/commands/`
- [ ] Add the `auditme-changed` (every commit) and `auditme-all` (every push and CI) hooks from the auditor repository to the tools list
- [ ] Check the tree against `git ls-files` once more for any other tracked directory it omits

**Acceptance Criteria:**

- [ ] `git ls-files .claude` prints nothing
- [ ] Every tracked top-level directory and `claude/` subdirectory appears in the tree

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)

**Notes:**

- Key files: `AGENTS.md`, `.pre-commit-config.yaml` (read only; it stays under "Do not modify")

---

## Task 12: Spec fixes, and the whole-tree checks

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Finding 13, Decision 2

**Technical Goal:** Correct the spec statements review-4 found stale, fill the structural gaps it found, leave the two long specs whole, and run the whole-tree checks before the branch merges.

**Subtasks:**

- [ ] `agents/specs/auditme-adoption/spec.md`: `message_type_to_str` to `MESSAGE_TYPE_TO_STR` (line 56), `ralpher_event_type_to_str` to `RALPHER_EVENT_TYPE_TO_STR` (line 57), `is_working_tree_clean` to `working_tree_is_clean` (line 80), `bin/install-claude.py` to `bin/install-claude.sh` in Module location (line 37); leave the dated Implementation table as written
- [ ] `agents/specs/verified-stop/spec.md:180`: say a missing worktree gives the `TasksFileError` text `worktree for <slug> not found` as the reason, as line 173 does
- [ ] `agents/specs/verified-stop/spec.md`: add an External dependencies section (GitPython, `re`) and declare `TasksFileError` in the API
- [ ] `agents/specs/run-order/spec.md`: define `LogVerdict` and `Decision` in the API, with the fields `src/ralphlib/order.py` gives them
- [ ] Do not split either spec (Decision 2)

**Acceptance Criteria:**

- [ ] Each statement review-4's Doc4 list names now matches the code

**Definition of Done:**

- [ ] `pre-commit run --all-files` passes
- [ ] `pre-commit run --hook-stage pre-push auditme-all --all-files` passes
- [ ] `uv run pytest src/tests/test_giter.py src/tests/test_hooks.py src/tests/test_iteration.py src/tests/test_logger.py src/tests/test_looper.py src/tests/test_order.py src/tests/test_ralpher.py src/tests/test_rro.py src/tests/test_settings.py src/tests/test_signals.py src/tests/test_state.py src/tests/test_verifier.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Task 7 (the run-order spec names the renamed functions)
- The last task: its test run covers every test file that imports a module this list changed

---
