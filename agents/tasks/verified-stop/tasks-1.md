# Tasks: Verified stop

**Spec:** `agents/specs/verified-stop/spec.md`
**Created:** 2026-10-08
**Version:** 1

The project has no type checker and no affected-tests tool. Each task's
Definition of Done names the changed modules' own test files and every test
file that imports a changed module directly. Every test file imports
`ralphlib.options.RalpherOptions`, so the tasks that change `options.py` or
`looper.py` run `src/tests`.

---

## Task 1: Parse task headings and statuses

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** API (`TaskStatus`, `StopCheck`, `parse_tasks`); Implementation > Parsing; Tests

**Technical Goal:** Create `src/ralphlib/verifier.py` with the `TaskStatus` and `StopCheck` dataclasses and `parse_tasks`, so later tasks can tell which tasks in a tasks file are not `done`.

**Subtasks:**

- [x] Create `src/ralphlib/verifier.py` with the `TaskStatus` and `StopCheck` dataclasses exactly as the spec's API section gives them
- [x] Implement `parse_tasks(text: str) -> list[TaskStatus]`: headings match `^## Task (\d+):\s*(.*)$`, status is the first `^\*\*Status:\*\*\s*(\S+)` line after the heading and before the next `## ` heading, lowercased and stripped, `''` when absent
- [x] Skip lines inside fenced code blocks (lines between a pair of lines starting with three backticks or three tildes)
- [x] Create `src/tests/test_verifier.py` with tests for: headings with and without status lines; mixed-case statuses (`Done` -> `done`); a task-shaped example inside a fenced block is ignored; text with no headings returns `[]`
- [x] Add a hypothesis test: generate a list of `(number, title, status)` tuples, render them in the tasks-file format, parse, and check that the numbers and statuses round-trip
- [x] Add `verifier.py` and `test_verifier.py` to the project structure tree in `AGENTS.md`, in alphabetical position

**Acceptance Criteria:**

- [x] `parse_tasks` returns tasks in file order with lowercased statuses
- [x] A heading with no status line yields status `''`
- [x] Example tasks inside fenced blocks are not returned
- [x] The hypothesis round-trip test passes

**Definition of Done:**

- [x] `pre-commit run --all-files` passes
- [x] `uv run ruff check` passes
- [x] `uv run ruff format --check` passes
- [x] `uv run pytest src/tests/test_verifier.py` passes

**Notes:**

- Key files: `src/ralphlib/verifier.py` (new), `src/tests/test_verifier.py` (new), `AGENTS.md`
- Status line format comes from the `taskdev` skill's template: `**Status:** todo`

---

## Task 2: Locate the tasks file inside the agent's worktree

**Status:** done
**Priority:** high
**Complexity:** medium
**Spec Reference:** API (`worktree_task_file`); Implementation > Finding the tasks file; Error handling; Tests

**Technical Goal:** Implement `worktree_task_file(options)` so the check reads the copy of the tasks file the agent edited, not the stale copy in the main checkout.

**Subtasks:**

- [x] Implement `worktree_task_file(options: RalpherOptions) -> pathlib.Path | None` in `src/ralphlib/verifier.py`
- [x] Get the repository with `ralphlib.giter.discover_repo_path(options.cwd)` and run `repo.git.worktree('list', '--porcelain')`
- [x] Parse the porcelain output into `(worktree path, branch)` pairs and pick the entry whose branch is `refs/heads/worktree-<slug>`, `<slug>` from `ralphlib.templater.task_file_slug(options.task_file)`
- [x] Return that worktree path joined with `options.task_file` relative to `repo.working_tree_dir`; return `None` when no entry matches or there is no repository
- [x] Let `git.GitCommandError` propagate from this function (Task 3 catches it)
- [x] Add tests to `src/tests/test_verifier.py` using a temporary git repository (`tmp_path`, an initial commit, then `git worktree add -b worktree-<slug> <path>`): the matching worktree is found and the returned path points at its copy of the tasks file; a repository with no matching worktree returns `None`

**Acceptance Criteria:**

- [x] With a worktree on branch `worktree-<slug>`, the returned path is inside that worktree
- [x] With no matching worktree, the result is `None`
- [x] A worktree on an unrelated branch is not returned

**Definition of Done:**

- [x] `pre-commit run --all-files` passes
- [x] `uv run ruff check` passes
- [x] `uv run ruff format --check` passes
- [x] `uv run pytest src/tests/test_verifier.py` passes

**Notes:**

- Depends on Task 1
- Key files: `src/ralphlib/verifier.py`, `src/ralphlib/giter.py` (`discover_repo_path`), `src/ralphlib/templater.py` (`task_file_slug`)
- Confirmed on 2026-10-08 from litrev logs: Claude Code places the worktree at `<repo>/.claude/worktrees/<slug>` on branch `worktree-<slug>`. Match on the branch, not the path
- `iteration.py` has its own copy of `task_file_slug`; use the `templater` one, as `looper.cleanup_cmds` does

---

## Task 3: Check a stop signal against the tasks file

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** API (`check_stop`); Implementation > Finding the tasks file; Error handling; Tests

**Technical Goal:** Implement `check_stop(options) -> StopCheck`, which reports whether every task is `done`, or why the check could not be made.

**Subtasks:**

- [x] Implement `check_stop` in `src/ralphlib/verifier.py`: with `options.worktree` set, use `worktree_task_file(options)`; otherwise use `pathlib.Path(options.task_file)`
- [x] Return `verified=False` with reason `worktree for <slug> not found` when `worktree_task_file` returns `None`
- [x] Catch `OSError`, `UnicodeDecodeError` and `git.GitCommandError` only, returning `verified=False` with a reason naming the path and the error
- [x] Return `verified=False` with reason `no tasks found in <path>` when `parse_tasks` returns `[]`
- [x] Otherwise return `verified=True`, `all_done` true when every status is `done`, `not_done` listing the others, and `total` the number of tasks
- [x] Add tests without a worktree: all done; some not done (`not_done` lists them in order); missing file; empty file
- [x] Add a test with a worktree (reusing Task 2's fixture): the worktree copy says not done while the main checkout copy says done, and `check_stop` reports not done

**Acceptance Criteria:**

- [x] Every outcome row in the spec's Implementation > Outcomes table can be produced by `check_stop`
- [x] With `--worktree`, the worktree copy is read and the main copy is never used as a fallback
- [x] No exception other than the three named escapes the function in the tested failure cases

**Definition of Done:**

- [x] `pre-commit run --all-files` passes
- [x] `uv run ruff check` passes
- [x] `uv run ruff format --check` passes
- [x] `uv run pytest src/tests/test_verifier.py` passes

**Notes:**

- Depends on Task 1 and Task 2
- Key files: `src/ralphlib/verifier.py`, `src/tests/test_verifier.py`

---

## Task 4: Reject an unverified stop in the loop

**Status:** done
**Priority:** high
**Complexity:** medium
**Spec Reference:** API (`no_verify_stop` option); Implementation > When the check runs; Implementation > Outcomes; Settings; Tests

**User Story:** As an operator running a queue, I want ralpher to ignore a completion marker while tasks remain unfinished, so that one slip by the agent doesn't end the queue early.

**Subtasks:**

- [x] Add `no_verify_stop` to `RalpherOptions` in `src/ralphlib/options.py`, after `stops`, with `long='--no-verify-stop'` and the spec's help text
- [x] In `looper.loop`, after the iteration's end is recorded and before the exit test, call `ralphlib.verifier.check_stop(options)` when `complete and options.task_file and not options.no_verify_stop and not error`
- [x] When `verified` and not `all_done`: set `complete = False`; print `===== Loop complete signal rejected, <n> of <m> tasks not done =====` with `print_both` and `MessageType.SYSTEM`, followed by one `  Task <n>: <title> (<status>)` line per unfinished task (`(no status)` for `''`); record `stop_rejected` with `total` and the `not_done` task numbers under the iteration's key in `state.json`
- [x] When not `verified`: log `loguru.logger.warning` with the reason and stop as today
- [x] Add tests to `src/tests/test_looper.py` with `ralphlib.iteration.run` patched to return `(True, False)`: unfinished task -> the loop runs a second iteration and prints the rejection line; all done -> stops after one iteration; `--no-verify-stop` -> stops after one iteration; unreadable tasks file -> stops after one iteration and a warning is logged
- [x] Add a test that a rejected signal on the last iteration ends with exit reason `completed all iterations`

**Acceptance Criteria:**

- [x] A false stop signal no longer ends the loop when `--task-file` is given
- [x] A true stop signal ends the loop exactly as before
- [x] Without `--task-file`, or with `--no-verify-stop`, behaviour is unchanged
- [x] `state.json` records `stop_rejected` for a rejected iteration

**Definition of Done:**

- [x] `pre-commit run --all-files` passes
- [x] `uv run ruff check` passes
- [x] `uv run ruff format --check` passes
- [x] `uv run pytest src/tests` passes

**Notes:**

- Depends on Task 3
- Key files: `src/ralphlib/looper.py`, `src/ralphlib/options.py`, `src/tests/test_looper.py`
- The rejection line must not contain `signal received`, so the existing rrq filter and any log searches still mean "the loop stopped"
- `loop` resolves `options.task_file` to an absolute path before the loop starts; `check_stop` relies on that
- `uv run pytest src/tests` fails on three `test_iteration.py` tests that also fail on the base commit (stale since `9faa842`, see Task 6). Task 4's own tests in `test_looper.py` pass. Task 4 is done once Task 6 is done and the full run is green
- `uv run ruff check` and `uv run ruff format --check` pass

---

## Task 5: Relay rejections in rrq and document the behaviour

**Status:** done
**Priority:** medium
**Complexity:** small
**Spec Reference:** rrq relay; Settings; Module location (`README.md`)

**User Story:** As an operator watching `/rrq`, I want to see when ralpher rejects a completion signal, so that I know why the queue kept running.

**Subtasks:**

- [x] In `claude/commands/rrq.md`, widen the monitor's grep pattern from `^=+ Loop .* signal received` to `^=+ Loop .* signal (received|rejected)`
- [x] Add a relay rule to `rrq.md`: `===== Loop complete signal rejected, <n> of <m> tasks not done =====` -> `■ loop complete rejected, <n> of <m> tasks not done`
- [x] In `README.md`, describe the verified stop: when it applies (`--task-file`), what it checks (every `**Status:**` is `done`, worktree copy with `--worktree`), what happens on rejection, that an unverifiable signal is trusted with a warning, and the `--no-verify-stop` flag with its default

**Acceptance Criteria:**

- [x] The rrq monitor command matches both the stop line and the rejection line (check with `grep -E` against sample lines)
- [x] `README.md` documents `--no-verify-stop` with its default and trade-off

**Definition of Done:**

- [x] `pre-commit run --all-files` passes
- [x] `uv run ruff check` passes
- [x] `uv run ruff format --check` passes
- [x] `uv run pytest src/tests` passes

**Notes:**

- Depends on Task 4
- Key files: `claude/commands/rrq.md`, `README.md`
- `rrq.md` is symlinked from `~/.claude/commands/rrq.md`, so the change takes effect on the next `/rrq`
- Last task of the list: the full `uv run pytest src/tests` run above is the whole-suite gate before merging

---

## Task 6: Fix stale stop-marker tests in test_iteration.py

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** none (pre-existing failure found while running Task 4's Definition of Done)

**Technical Goal:** Make `uv run pytest src/tests` pass again. Three tests in `src/tests/test_iteration.py` expect a stop marker embedded in a longer line to set `complete`, but `iteration.is_stop` has matched whole lines only since commit `9faa842`.

**Subtasks:**

- [x] Update `test_process_result_with_stop_marker_sets_complete`, `test_process_assistant_text_with_stop_marker_sets_complete` and `test_process_result_custom_stop_markers_respected` so the marker is on a line of its own
- [x] Add a test that a marker embedded in a longer line does not set `complete`

**Acceptance Criteria:**

- [x] `uv run pytest src/tests` passes with no changes to `src/ralphlib/iteration.py`

**Definition of Done:**

- [x] `pre-commit run --all-files` passes
- [x] `uv run ruff check` passes
- [x] `uv run ruff format --check` passes
- [x] `uv run pytest src/tests` passes

**Notes:**

- Blocks Task 4's last Definition of Done item; after it, mark Task 4 `done`
- Key files: `src/tests/test_iteration.py`
