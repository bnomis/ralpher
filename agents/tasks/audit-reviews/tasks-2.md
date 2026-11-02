# Tasks: Audit Review 2

**Source:** `agents/audit-reviews/review-2.md`
**Created:** 2026-11-02
**Version:** 2

The decisions this list depends on are recorded in the review's Answers
section (2026-11-02). They cover only what they name: a task that meets a
behaviour change they do not cover stops for the user.

Review-2 Finding 19 (the D2 hits on plugin dependencies) has no task here. Its
fix is a refinement to the shared auditme skill, requested in that skill's
`requests.md`, and is out of this repository.

No task has a test tool that selects affected tests, because the project has
none. Each task runs the tests of the modules it changes. The last task runs
every test file that imports a module this list changed.

---

## Task 1: An exception during an iteration ends the run as an error

**Status:** done
**Priority:** high
**Complexity:** small
**Source Reference:** Finding 1

**User Story:** As someone running a ralpher queue, I want a crash inside an iteration to exit non-zero, so that the queue script stops instead of moving on as if the tasks were done.

**Subtasks:**

- [x] In `looper.loop`, on an exception from `ralphlib.iteration.run`, set `error = True` and set `exit_reason` to name the failure (for example `'exception during iteration {i}'`) before breaking, keeping `loguru.logger.exception`
- [x] Check that the `error` hook (`looper.py`, the `if error:` block near line 248) fires and the state file records the exit reason; the `iteration_end` hook stays skipped for an iteration that did not end
- [x] Add a row for this case to `docs/reference/exit-statuses.md` and a line to `docs/guide/stopping.md`
- [x] Add a test to `src/tests/test_looper.py` that makes `iteration.run` raise, and asserts that `loop` returns `True`, that the exit reason names the exception, and that the `error` hook event is fired
- [x] Confirm the new test fails against the current code before the fix

**Acceptance Criteria:**

- [x] `loop` returns `True` after an iteration raises
- [x] The printed and stored exit reason is not `completed all iterations`
- [x] The docs list the exit status for this case

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_looper.py` passes
- [x] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Key files: `src/ralphlib/looper.py` (handler near line 134, `error` initialised near line 101, return at line 278 on 2026-11-02), `bin/ralpher.py`, `src/tests/test_looper.py`
- Do not just change the log level of the handler (the auditme A19 no-winner ruling); setting the error state is the fix

---

## Task 2: Never overwrite an unreadable state file

**Status:** done
**Priority:** high
**Complexity:** small
**Source Reference:** Finding 2

**User Story:** As someone reading a run's state file, I want ralpher to stop rather than replace a state file it cannot read, so that earlier iterations' records are never lost.

**Subtasks:**

- [x] In `state.load_state`, return `{}` only when the file does not exist; remove the `except Exception` so a read or parse failure propagates
- [x] Translate `OSError`, `UnicodeDecodeError` and `json.JSONDecodeError` from the read into a new domain error `StateFileError` in `src/ralphlib/exceptions.py`, naming the path
- [x] Add tests to `src/tests/test_state.py`: a corrupt state file makes `add_to_state` raise and leaves the file's bytes unchanged; a missing file still gives `{}`
- [x] Confirm the corrupt-file test fails against the current code

**Acceptance Criteria:**

- [x] A corrupt state file is unchanged after `add_to_state`
- [x] The error names the state file path

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_state.py` passes

**Notes:**

- Key files: `src/ralphlib/state.py` (`load_state` near line 20), `src/ralphlib/exceptions.py`, `src/tests/test_state.py`
- Task 6 adds the rest of the domain errors and should reuse `StateFileError`

---

## Task 3: Let the state-lock retry actually retry

**Status:** done
**Priority:** high
**Complexity:** small
**Source Reference:** Prior findings re-verified, review-1 Finding 10

**Technical Goal:** `add_to_state_work` catches `filelock.Timeout` and only logs it, so the `tenacity.retry` on `Timeout` never fires and the update is dropped silently. Let the timeout reach the retry, and let the final failure reach `add_to_state`.

**Subtasks:**

- [x] Remove the `except filelock.Timeout` block from `add_to_state_work`
- [x] Check that `add_to_state` still logs once and re-raises after the last attempt
- [x] Add a test to `src/tests/test_state.py` that holds the lock (or patches `lock.acquire` to raise `filelock.Timeout`) and asserts three attempts are made and `add_to_state` raises; patch `tenacity`'s wait so the test does not sleep
- [x] Confirm the test fails against the current code

**Acceptance Criteria:**

- [x] A held lock gives three attempts, then an exception
- [x] No state update is silently dropped

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_state.py` passes

**Notes:**

- Depends on Task 2 (same file)
- Key files: `src/ralphlib/state.py` (handler near line 110 on 2026-11-02)

---

## Task 4: Any `is_error` result is an error

**Status:** done
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding 3; review-2 Answers (2026-11-02)

**User Story:** As someone running ralpher, I want an agent result flagged as an error to stop the loop as an error whatever its subtype, so that a turn-limit or execution failure is not mistaken for progress.

**Subtasks:**

- [x] In `iteration.py` (the `result` handler near line 897), set the error flag for any payload with `is_error` true, not only `subtype == 'success'`
- [x] Add parametrised tests to `src/tests/test_iteration.py` for `success`, `error_max_turns` and `error_during_execution` with `is_error` true, and for `success` with `is_error` false
- [x] Check `docs/guide/stopping.md:35` and `docs/concepts.md:50` still describe the behaviour exactly

**Acceptance Criteria:**

- [x] Every subtype with `is_error: true` sets the error flag

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_iteration.py` passes

**Notes:**

- Key files: `src/ralphlib/iteration.py`, `src/tests/test_iteration.py`

---

## Task 5: Validate `--vars` before the loop starts

**Status:** done
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding 5

**User Story:** As someone starting ralpher, I want a malformed `--vars` value rejected before anything runs, so that no hooks fire and no state is written for a run that cannot work.

**Subtasks:**

- [x] Add `templater.parse_vars(options) -> dict[str, str]`, which raises `InvalidVarFormat` for a value without `=` and for a key that names a built-in template variable (the keys `render` sets itself)
- [x] Call it in `looper.loop` before the `start` hook, print the error and return `True` (error) without starting an iteration; have `render` use the parsed dict
- [x] Add tests to `src/tests/test_templater.py` (bad format, reserved key, good vars) and to `src/tests/test_looper.py` (no `start` hook and no iteration on bad vars)
- [x] Check `docs/reference/exit-statuses.md:11` and the `--vars` entry in `docs/reference/cli.md` describe the behaviour, including the reserved keys

**Acceptance Criteria:**

- [x] Bad `--vars` exits non-zero before the `start` hook, with no traceback
- [x] A `--vars` key cannot replace a built-in variable

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_templater.py src/tests/test_looper.py` passes
- [x] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Task 1 (same `looper.py` region)
- Key files: `src/ralphlib/templater.py` (near line 56), `src/ralphlib/looper.py`, `src/ralphlib/exceptions.py`

---

## Task 6: Translate I/O errors into domain errors

**Status:** done
**Priority:** medium
**Complexity:** large
**Source Reference:** Finding 6 (A1, A2, A3)

**Technical Goal:** Give ralphlib one domain error per area and wrap every external call in the review's A1 list in it, widen the A2 except tuples to include `OSError`, and replace the two stdlib raises (A3).

**Subtasks:**

- [x] In `exceptions.py`, add a base `RalpherError` and `GitError`, `LogFileError`, `SettingsError`, `TasksFileError` (with `StateFileError` from Task 2), each subclassing `RalpherError`; rename the existing classes to end in `Error` (`NoStateFilePathError`, `ValueNotADictError`, `InvalidVarFormatError`, `NoStateLockFilePathError`) and update every reference
- [x] `giter.py`: wrap the calls at lines 77, 117, 145, 150-155 and 197-199 (2026-11-02) in `GitError`; add `OSError` to the tuples at 76, 125, 186 and `OSError, UnicodeDecodeError` at 131
- [x] `state.py`: translate `OSError` from `save_state` and from `lock.acquire` (tuple at line 88) into `StateFileError`
- [x] `logger.py`: `mkdir` (line 16) raises `LogFileError`; replace `raise ValueError` (line 21) with `LogFileError`
- [x] `settings.py`: `load_settings_from_file` translates `OSError`, `UnicodeDecodeError` and `json.JSONDecodeError` into `SettingsError`, naming the path
- [x] `looper.py`: `os.chdir` and the prompt and tasks-file reads (lines 32, 43, 63) translate into `RalpherError` subclasses; convert the two `open()` calls to `pathlib.Path(...).read_text(encoding='utf-8')` (review-1 Finding 8)
- [x] `verifier.py`: replace `raise LookupError` (line 115) with `TasksFileError`, and update `READ_ERRORS` and its callers
- [x] `iteration.py`: translate the log-file opens (lines 211-220) into `LogFileError` and `Popen` (line 443) into `RalpherError`; in the reader threads, catch `OSError` from `readline` and the log writes, log it with `loguru.logger.exception`, and stop the thread cleanly
- [x] `printer.py:23` and `hooks.py:104` (`tzlocal`): translate into `LogFileError` and `RalpherError`
- [x] `bin/ralpher.py`: catch `RalpherError` around `loop`, print its message without a traceback and exit 1
- [x] Add a test per area to the matching `src/tests/test_<module>.py`, each forcing the failure and asserting the domain error

**Acceptance Criteria:**

- [x] Every call in review-2's A1 list is inside an envelope that raises a `RalpherError` subclass
- [x] Every A2 tuple includes `OSError`
- [x] No `raise ValueError` or `raise LookupError` remains in `src/ralphlib`

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_giter.py src/tests/test_state.py src/tests/test_logger.py src/tests/test_settings.py src/tests/test_looper.py src/tests/test_verifier.py src/tests/test_iteration.py src/tests/test_printer.py src/tests/test_hooks.py src/tests/test_templater.py` passes

**Notes:**

- Depends on Tasks 2, 3 and 5 (they touch `state.py`, `templater.py` and `exceptions.py`)
- `bin/install-claude.py` is a standalone script with its own catch-all; leave it out of the domain errors
- Large: if it will not fit one session, split by module and commit each module separately

---

## Task 7: Narrow the broad graceful-degradation handlers

**Status:** done
**Priority:** medium
**Complexity:** medium
**Source Reference:** Finding 7 (A19)

**Technical Goal:** Each of `hooks.py:222`, `iteration.py:233`, `iteration.py:609` and `iteration.py:769` catches `Exception`, logs it and carries on. Narrow each one to the exceptions it expects and log those with `loguru.logger.warning`, as the auditme no-winner ruling for A19 requires.

**Subtasks:**

- [x] `hooks.run_hook`: catch the expected failures (`ValueError` from `shlex.split`, `OSError` from `Popen`, `jinja2.TemplateError`) and log them with `warning`; let anything else propagate
- [x] `iteration.flush_and_close_fd`: catch `OSError` only
- [x] `iteration.process_line`: catch the JSON decode error and the payload-shape errors (`KeyError`, `TypeError`, `AttributeError`) only
- [x] `iteration.process_task_progress`: catch only what its parsing can raise
- [x] Add or adjust tests in `src/tests/test_hooks.py` and `src/tests/test_iteration.py`: each expected failure is logged and carries on, and an unexpected one propagates

**Acceptance Criteria:**

- [x] None of the four handlers catches `Exception`
- [x] The auditme sweep still has no unaccepted hits

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_hooks.py src/tests/test_iteration.py` passes

**Notes:**

- Depends on Task 6 (same functions in `iteration.py`)
- If an unexpected exception on a reader thread would now kill the run in a way that needs a behaviour decision, stop and ask the user

---

## Task 8: One resolver for the tasks file, worktree and base ref, resolved once

**Status:** todo
**Priority:** medium
**Complexity:** large
**Source Reference:** Findings 8 and 9 (A5, A14, A24, P2, P3)

**Technical Goal:** Hooks and the verifier choose the tasks file by different rules, `--args` silently overrides `--worktree` and `--worktree-base-ref`, and `git worktree list` runs on every 3 s poll and every hook event. Give each value one owner, resolve it once per iteration, and document the precedence.

**Subtasks:**

- [ ] Make `verifier.agent_task_file` the only function that chooses the tasks file; have `hooks.event` (line 44) call it, so the worktree copy is used only under `--worktree`
- [ ] Move the duplicate-event check in `hooks.event` before any git call
- [ ] Cache the worktree path once it is found during an iteration (on `IterationContext`, or with a per-iteration memo cleared by `make_context`), so the poll loop (`iteration.py:484`, `:817`) and hook events reuse it
- [ ] Have `giter.last_commit_summary` computed once per hook event at most, and not on events whose hooks do not use templates
- [ ] Compute `options.passed_worktree_base_ref` once (in `parse_options`) and read the stored value in `giter.py:87`, `:163` and `iteration.py:178`
- [ ] When `--args` holds `--worktree`/`-w` or `--settings`, log a warning at start naming which value wins, and document the precedence in `docs/guide/worktrees.md`
- [ ] Add tests: `hooks.event` uses the same tasks file as the verifier with and without `--worktree`; `git worktree list` runs once per iteration in a poll-loop test (count subprocess calls); a duplicate event runs no git

**Acceptance Criteria:**

- [ ] One function chooses the tasks file
- [ ] `git worktree list` runs at most once per iteration after the worktree is found
- [ ] The precedence between `--args` and ralpher's own options is documented

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_hooks.py src/tests/test_verifier.py src/tests/test_iteration.py src/tests/test_giter.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Task 7
- Key files: `src/ralphlib/verifier.py` (lines 83-115), `src/ralphlib/hooks.py`, `src/ralphlib/iteration.py`, `src/ralphlib/giter.py`, `src/ralphlib/options.py`

---

## Task 9: End-to-end test of an iteration

**Status:** todo
**Priority:** medium
**Complexity:** medium
**Source Reference:** Finding 10 (T1, T3)

**Technical Goal:** Drive `iteration.run` with a real child process that prints canned stream-JSON on stdout and text on stderr, so that `make_context`, `process`, the per-line branches of `process_stdout` and `process_stderr`, `summary` and `unmake_context` are all exercised.

**Subtasks:**

- [ ] Add a fixture script under `src/tests/fixtures/` that prints a short stream-JSON session (system, assistant text, a tool use, a tool use with no input, a `result`) and one stderr line
- [ ] Add tests to `src/tests/test_iteration.py` that run `iteration.run` with `--agent` pointing at it: assert `(complete, error)`, the contents of the stdout, stderr, progress and errors log files, and the summary lines (tools used, unknown tools)
- [ ] Add a variant that emits the stop marker and asserts `complete`, and one that emits an `is_error` result and asserts `error`

**Acceptance Criteria:**

- [ ] `run`, `make_context`, `unmake_context`, `summary`, `add_unknown_tool`, `write_stdout` and `write_stderr` each run in at least one test

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_iteration.py` passes

**Notes:**

- Depends on Tasks 4 and 8 (it asserts their behaviour)
- Follow the existing child-process pattern in `src/tests/test_process_termination.py`

---

## Task 10: Bring the user docs in line with the code, and fix `task_file_number`

**Status:** todo
**Priority:** medium
**Complexity:** medium
**Source Reference:** Findings 4 and 11 (Doc5); review-2 Answers (2026-11-02)

**User Story:** As someone reading the ralpher docs, I want every documented behaviour to match what ralpher does, so that I can rely on the docs without reading the code.

**Subtasks:**

- [ ] `hooks.py` (lines 115-130): compute `task_file_number` as the digits after the last `-` in `pathlib.Path(task_file).stem`, kept as written (`tasks-3` gives `3`, `tasks-0.md` gives `0`, no number gives empty); add a hypothesis test in `src/tests/test_hooks.py` (`@hypothesis.settings(max_examples=20, deadline=10000)`)
- [ ] `docs/reference/variables.md:30`: `current_iteration` in `end` and `error` hooks is the last iteration that ran, or 0 if none ran
- [ ] `docs/guide/terminal.md:13,56`: make agent stderr use the theme's `error` style in `iteration.py:324`, or document the fixed red; use the theme style unless that changes another printed line
- [ ] `docs/reference/scripts.md:3-4`: `ralpherun.sh` needs `RALPHER_PATH` too, and `install-claude.py` does not activate `.venv`
- [ ] `docs/install.md:59-60`: an existing symlink at the destination is replaced, and only regular files are renamed `.orig`
- [ ] `docs/reference/settings.md` and `docs/guide/hooks.md`: say that `.ralpher/settings.json` in the `--cwd` repository can define hooks, which run as commands, so ralpher should be run only on repositories you trust (Finding 4)

**Acceptance Criteria:**

- [ ] Every Doc5 item in review-2 is fixed
- [ ] `task_file_number` follows the documented rule for names with and without an extension

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_hooks.py src/tests/test_iteration.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- The exit-status, `--vars` and `is_error` doc items are handled in Tasks 1, 4 and 5
- Key files: `src/ralphlib/hooks.py`, `src/ralphlib/iteration.py`, `docs/`

---

## Task 11: Bring AGENTS.md and the specs in line with the repository

**Status:** todo
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding 11 (Doc1-Doc4), Spec review

**Technical Goal:** Fix the drift review-2 lists in `AGENTS.md`, `README.md` and both specs.

**Subtasks:**

- [ ] `AGENTS.md` project structure: add `conftest.py`, `test_shlex.py`, `install-claude.py`, `rcl.sh`, `agents/`, `claude/`, `TODO.md`, `DONE.md` and `NOTES.md`; describe `logs/` correctly or remove it; add `ralpher-logs/`; add any test file or module the earlier tasks created
- [ ] `AGENTS.md` tools: Python 3.14.5 or later; remove Docker; list `filelock`, `gitpython`, `jinja2`, `orjson`, `rich`, `tenacity`, `tzlocal`, the pytest plugins, `mkdocs`, `mkdocs-material` and `pre-commit`
- [ ] `AGENTS.md` Goals: add verified stops, worktree queues and hooks, matching `README.md`
- [ ] `agents/specs/verified-stop/spec.md`: fix lines 32, 72, 165 and 167 as review-2 Doc4 lists
- [ ] `agents/specs/auditme-adoption/spec.md`: release-tag pins (lines 115, 148), the `no-project-names` hook (line 105), the verified-stop status (line 158, with a relative link), and docstrings for `load_state` and `save_state` (lines 61-62)

**Acceptance Criteria:**

- [ ] Every Doc1-Doc4 item and spec-review gap in review-2 is fixed

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Tasks 1-10, so the structure tree includes files they added
- Leave the verified-stop spec's size as it is; it is implemented, and splitting it now is not worth the churn

---

## Task 12: Keep agent output and credentials out of WARNING logs, and contain user paths

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Findings 12 and 13 (Sec2, Sec4, Sec5)

**Technical Goal:** Stop raw agent JSON and credential-bearing remote URLs reaching WARNING-level logs, and keep user-supplied names inside the paths they are meant for.

**Subtasks:**

- [ ] `iteration.py:723`, `:739`, `:747`: log the payload type and length at WARNING and the raw line at DEBUG
- [ ] `giter.py:135`: strip the user-info part of `origin.url` before logging it
- [ ] `logger.py:68`, `:78`: reject a `--state` value that is absolute or contains `..` with a domain error
- [ ] `bin/rrq.sh:31`, `bin/rcl.sh:31`: reject `TASKS-SPEC` and `TASKS-INDEX` containing `/` or `..`, with a usage message
- [ ] Add tests to `src/tests/test_iteration.py`, `src/tests/test_giter.py` and `src/tests/test_logger.py`

**Acceptance Criteria:**

- [ ] No WARNING log line contains a raw agent payload or URL credentials
- [ ] A `--state` value outside the log directory is rejected

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`), shellcheck included
- [ ] `uv run pytest src/tests/test_iteration.py src/tests/test_giter.py src/tests/test_logger.py` passes

**Notes:**

- Depends on Task 6 (domain errors)
- Update `docs/reference/cli.md` (`--state`) and `docs/reference/scripts.md` if they describe the accepted values

---

## Task 13: Code clean-ups (names, mutation, duplication, standards)

**Status:** todo
**Priority:** low
**Complexity:** medium
**Source Reference:** Findings 14, 15, 16 and 17 (A8, A9, A10, A13, A15, S1, S4)

**Technical Goal:** Clear the low-severity architecture and standards findings in review-2.

**Subtasks:**

- [ ] Rename the interactive git checks to say they prompt (`check_git` to `confirm_git_state`, `check_repo_clean` to `confirm_repo_clean`, `check_divergence` to `confirm_divergence`) and update the callers and tests; leave the other A9 names, which read state their names state
- [ ] `giter.has_unpushed_commits`: return `bool | None`, with `None` for "cannot tell", and have `confirm_repo_clean` treat `None` as a reason to warn
- [ ] `iteration.make_context`: open the log files first and pass them to the `IterationContext` constructor (A8)
- [ ] Move the two shared `rich.console.Console` instances to `printer.py` and import them in `giter.py`, `state.py` and `iteration.py`
- [ ] Add `verifier.verified()` beside `unverified()` and use it at `verifier.py:142`
- [ ] Add a one-line docstring to `hooks.run_hook` and `iteration.process` saying that stdout and stderr share a value on purpose (A13)
- [ ] Annotate the `bin/install-claude.py` parameters (S1); add the annotations missing in `src/tests/test_process_termination.py`
- [ ] Sort the literals at `iteration.py:93`, `iteration.py:627`, `hooks.py:136-151` and `templater.py:31`, and delete the obvious comments review-2 S4 lists
- [ ] Remove the unused `options` parameter from the `iteration.py` `write_*` functions (review-1 Finding 9), or keep it and leave a one-line reason, whichever keeps the call sites simpler

**Acceptance Criteria:**

- [ ] Every A8, A10, A13, A15, S1 and S4 item in review-2 is fixed, along with the A9 items named above

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_giter.py src/tests/test_iteration.py src/tests/test_verifier.py src/tests/test_hooks.py src/tests/test_templater.py src/tests/test_printer.py src/tests/test_state.py src/tests/test_looper.py src/tests/test_process_termination.py` passes

**Notes:**

- Depends on Tasks 6-12 (it touches the same files; doing it last avoids conflicts)
- Update `docs/` if a renamed function or a printed line appears there

---

## Task 14: Property tests for parsers and formatters, then the whole-tree gates

**Status:** todo
**Priority:** low
**Complexity:** medium
**Source Reference:** Finding 18 (T1, T2)

**Technical Goal:** Add hypothesis tests for the parsers and formatters review-2 T2 lists, plain tests for `parse_worktrees` and `bin/install-claude.py`, then run the whole-tree checks before the branch merges.

**Subtasks:**

- [ ] Hypothesis tests (`@hypothesis.settings(max_examples=20, deadline=10000)`), at least for: `hooks.render_hook_args` (an arbitrary value round-trips through `shlex.split` as one argument), `verifier.parse_worktrees`, `iteration.process_task_progress`, `iteration.is_stop`, `iteration.indent_lines`, `templater.task_file_slug`, `logger.iteration_to_str` and `looper.cleanup_cmds`
- [ ] Example tests for `verifier.parse_worktrees` (porcelain output with and without a branch, bare and detached) and for `bin/install-claude.py` (`symlink_file`, `find_dangling_symlinks`) in `tmp_path`
- [ ] Tests for `giter.YNConfirm.make_prompt`, `get_origin` with no `origin/HEAD`, and `get_current_branch` on a detached HEAD
- [ ] Run `pre-commit run --all-files` and `pre-commit run --hook-stage pre-push auditme-all --all-files`
- [ ] Run every test file that imports a module this list changed; the list changed nearly every `ralphlib` module, so that is every file in `src/tests/` that imports `ralphlib`

**Acceptance Criteria:**

- [ ] Every function in review-2 T2 has a property test, or the task notes why one does not fit
- [ ] Every remaining T1 function in review-2 has a test

**Definition of Done:**

- [ ] `pre-commit run --all-files` passes
- [ ] `pre-commit run --hook-stage pre-push auditme-all --all-files` passes
- [ ] `uv run pytest src/tests/test_giter.py src/tests/test_hooks.py src/tests/test_iteration.py src/tests/test_logger.py src/tests/test_looper.py src/tests/test_printer.py src/tests/test_process_termination.py src/tests/test_settings.py src/tests/test_shlex.py src/tests/test_signals.py src/tests/test_state.py src/tests/test_templater.py src/tests/test_verifier.py` plus any test file this list added passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Tasks 1-13
- After this list ships, update `agents/audit-reviews/summary.md`: move the resolved findings to Recently resolved (auditme step 8b)
