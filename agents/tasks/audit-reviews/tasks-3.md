# Tasks: Audit Review 3

**Source:** `agents/audit-reviews/review-3.md`
**Created:** 2026-11-02
**Version:** 3

Every finding in review-3 was approved, and Decision 1 was answered (keep the
`except Exception` in `loop` and accept it with a scoped marker), on
2026-11-02; the answers are in the review's Answers section. A decision covers
only what it names: a task that meets a behaviour change the review does not
recommend stops for the user.

Line numbers in this list are as of commit `fc0641c` (2026-11-02). Earlier
tasks move lines; find code by its function name.

The project has no tool that selects affected tests. Each task runs the test
files it writes and the tests of the modules it changes. The last task runs
every test file that imports a module this list changed.

A queue agent on the previous list reported tests it never committed. Every
task's Definition of Done therefore checks the task's own commit for the test
files it names.

---

## Task 1: A state-lock timeout is reported as a ralpher error

**Status:** done
**Priority:** high
**Complexity:** small
**Source Reference:** Finding 1

**User Story:** As someone running ralpher with `--state`, I want a busy state lock to end the run with an error message rather than a Python traceback, so that I can tell what went wrong.

**Subtasks:**

- [x] Add a test to `src/tests/test_state.py` that holds the lock (patch `filelock.FileLock.acquire` to raise `filelock.Timeout`) and asserts `add_to_state` raises `ralphlib.exceptions.StateFileError` naming the lock file; confirm it fails before the fix
- [x] In `ralphlib.state.add_to_state`, translate the `filelock.Timeout` that leaves the tenacity retry into `StateFileError` (`raise ... from e`), keeping the retry in `add_to_state_work`
- [x] Update `test_lock_timeout_is_retried_then_raised` in `src/tests/test_state.py` if it asserts the old exception type, keeping its check that the retry ran three times

**Acceptance Criteria:**

- [x] A held lock makes `add_to_state` raise `StateFileError` after three attempts
- [x] `bin/ralpher.py` prints `Error: ...` for it, since `StateFileError` is a `RalpherError`

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `git show --stat HEAD` lists `src/tests/test_state.py`
- [x] `uv run pytest src/tests/test_state.py` passes

**Notes:**

- Key files: `src/ralphlib/state.py` (`add_to_state`, `add_to_state_work`), `src/tests/test_state.py`

---

## Task 2: Bad settings files and bad `--args` end with an error message

**Status:** done
**Priority:** high
**Complexity:** small
**Source Reference:** Finding 2

**User Story:** As someone starting ralpher, I want a broken settings file or a mistyped `--args` to stop with a one-line error, so that I am not left reading a traceback.

**Subtasks:**

- [x] Add tests: a settings file whose top level is not a JSON object raises `SettingsError` naming the file (`src/tests/test_settings.py`); an `--args` value with an unbalanced quote raises a new `InvalidArgsError(RalpherError)` naming the value (`src/tests/test_options.py`); confirm both fail first
- [x] In `ralphlib.settings.load_settings_from_file`, raise `SettingsError` when the loaded value is not a `dict`
- [x] Add `InvalidArgsError` to `src/ralphlib/exceptions.py` and raise it from `RalpherOptions.__post_init__` when `shlex.split` raises `ValueError`
- [x] In `bin/ralpher.py`, move `ralphlib.options.parse_options()` inside the `try` so its `RalpherError` prints `Error: ...` and exits 1
- [x] Add a row to `docs/reference/exit-statuses.md` for ralpher's own errors before the first iteration (`Error: ...`, status 1): an unreadable or invalid settings file, an invalid `--args`, a `--cwd` that cannot be entered, a log directory that cannot be created, a `--state` path outside the log directory

**Acceptance Criteria:**

- [x] `bin/ralpher.sh` with an invalid settings file prints one `Error:` line and exits 1
- [x] The exit-status page lists the case

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `git show --stat HEAD` lists `src/tests/test_settings.py` and `src/tests/test_options.py`
- [x] `uv run pytest src/tests/test_settings.py src/tests/test_options.py` passes
- [x] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Key files: `bin/ralpher.py`, `src/ralphlib/options.py` (`__post_init__`, `parse_options`), `src/ralphlib/settings.py`, `src/ralphlib/exceptions.py`
- Task 12 adds the tests for `bin/ralpher.py` itself

---

## Task 3: Hook settings of the wrong shape are refused

**Status:** todo
**Priority:** high
**Complexity:** small
**Source Reference:** Finding 3

**User Story:** As someone writing hooks, I want a mistake in their shape to stop ralpher with a message naming the key, so that it never runs single characters as commands.

**Subtasks:**

- [ ] Add tests to `src/tests/test_settings.py`: `hooks` that is not an object, an event whose value is a string or a list holding a non-string, `hook_templates` that is not a bool and `theme` that is not an object each raise `SettingsError` naming the key and the file; confirm they fail first
- [ ] Add one validation function in `src/ralphlib/settings.py`, called after each file is merged in `load_settings_from_file`, that checks those keys
- [ ] State the accepted shapes in `docs/reference/settings.md`

**Acceptance Criteria:**

- [ ] `{"hooks": {"end": "notify"}}` stops ralpher with an error naming `hooks.end`
- [ ] `{"hook_templates": "false"}` stops ralpher with an error naming `hook_templates`

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_settings.py`
- [ ] `uv run pytest src/tests/test_settings.py src/tests/test_hooks.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Task 2 (`load_settings_from_file` already raises for a non-object top level)
- Key files: `src/ralphlib/settings.py`, `src/ralphlib/hooks.py` (`event`, which reads `hooks` and `hook_templates`), `src/ralphlib/printer.py` (reads `theme`)

---

## Task 4: The broad handlers follow the coding standard

**Status:** todo
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding 6; review-3 Decision 1

**Technical Goal:** Narrow `giter.last_commit_summary` and accept the `loop` handler as decided, so no broad handler remains without a recorded reason.

**Subtasks:**

- [ ] Add a test to `src/tests/test_giter.py` that `last_commit_summary` returns `''` in a repository with no commits, and that a `KeyboardInterrupt` raised while reading the commit propagates; confirm the second fails first
- [ ] Replace `contextlib.suppress(BaseException)` in `giter.last_commit_summary` with a handler for the errors a repository without commits raises (`ValueError`) and the git errors (`git.GitCommandError`, `git.GitCommandNotFound`), logged at `warning`
- [ ] Add a scoped accept marker on the `except Exception` in `looper.loop` naming review-3 Decision 1 (2026-11-02); change nothing else in that handler

**Acceptance Criteria:**

- [ ] `rg 'suppress\(BaseException\)' src` finds nothing
- [ ] The `loop` handler carries a marker scoped to its rule, with the decision named in its reason

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_giter.py`
- [ ] `uv run pytest src/tests/test_giter.py src/tests/test_looper.py src/tests/test_hooks.py` passes

**Notes:**

- Key files: `src/ralphlib/giter.py` (`last_commit_summary`), `src/ralphlib/looper.py` (the handler around `ralphlib.iteration.run`)
- The marker is `# auditme: accept[logger-exception-graceful-degradation] <reason>`, the form the auditme skill's no-winner ruling gives for a broad handler the user decided to keep
- Decision 1 covers only the `loop` handler; do not extend it to other handlers

---

## Task 5: I/O errors are translated

**Status:** todo
**Priority:** medium
**Complexity:** medium
**Source Reference:** Finding 5

**Technical Goal:** Make the git checks and the iteration log writes raise ralpher's own errors, so that no third-party or `OSError` exception escapes from them.

**Subtasks:**

- [ ] Tests in `src/tests/test_giter.py`: `git.GitCommandNotFound` from `is_dirty`, `fetch` and `iter_commits`, and a repository with no `origin`, each give the handled outcome (a `GitError`, or `None` from `has_unpushed_commits`) rather than escaping; `Path.cwd()` raising `FileNotFoundError` gives `GitError`
- [ ] Tests in `src/tests/test_iteration.py`: a log file object whose `write` raises `OSError` makes the write helpers raise `LogFileError`
- [ ] In `src/ralphlib/giter.py`, add `git.GitCommandNotFound` to the handlers in `is_working_tree_clean`, `has_unpushed_commits` (fetch and `iter_commits`), handle the missing `origin` (`AttributeError` from `repo.remotes.origin`), and move `pathlib.Path.cwd()` in `discover_repo_path` inside its `try`
- [ ] In `src/ralphlib/iteration.py`, route every log-file `write`/`flush` (`write_progress`, `write_progress_lines`, `write_progress_eol`, `write_error`, `write_error_eol`, `write_stdout`, `write_stderr`) through one helper that raises `LogFileError` naming the log; add `OSError` to the `process_line` handler's write path only if the helper does not already cover it
- [ ] Add a scoped accept marker to the broad handler in `bin/install-claude.py` `main`, giving the reason (it runs under the system Python, before the project environment, and has no domain errors)

**Acceptance Criteria:**

- [ ] No call named in review-3 A1 under `giter.py` or `iteration.py` lets a third-party or `OSError` exception escape
- [ ] The `verifier.py` cases review-3 A1 lists as documented stay as they are

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_giter.py` and `src/tests/test_iteration.py`
- [ ] `uv run pytest src/tests/test_giter.py src/tests/test_iteration.py src/tests/test_install_claude.py` passes

**Notes:**

- Key files: `src/ralphlib/giter.py`, `src/ralphlib/iteration.py`, `bin/install-claude.py`
- A write failure on a reader thread must still end the iteration as an error, not hang it; check the reader threads' handling in `process`

---

## Task 6: Prompts render in the sandbox

**Status:** todo
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding 9

**User Story:** As someone running ralpher on a repository I do not fully trust, I want its prompt file rendered in the same sandbox as hooks, so that a template in it cannot run code inside ralpher.

**Subtasks:**

- [ ] Add a test to `src/tests/test_templater.py` that a prompt using an attribute the sandbox blocks (for example `{{ ''.__class__.__mro__ }}`) raises a ralpher error rather than rendering; confirm it fails first
- [ ] In `templater.render`, render with `jinja2.sandbox.SandboxedEnvironment` (the environment `hooks.py` uses), and translate `jinja2.exceptions.SecurityError` and `TemplateSyntaxError` to a new or existing `RalpherError` subclass naming the prompt file
- [ ] Add a warning to `docs/guide/hooks.md` beside the `sh -c` advice: a value spliced into an `sh -c` string, including the agent-supplied `task_title` and `prompt`, becomes shell code
- [ ] Add a line to `docs/guide/prompts.md` that prompts render in Jinja's sandbox

**Acceptance Criteria:**

- [ ] Every existing prompt test still passes
- [ ] The sandbox test passes

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_templater.py`
- [ ] `uv run pytest src/tests/test_templater.py src/tests/test_looper.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Key files: `src/ralphlib/templater.py` (`render`), `src/ralphlib/hooks.py` (its sandboxed environment)

---

## Task 7: Worktree options in `--args` are refused, and the unblock prompt is accurate

**Status:** todo
**Priority:** medium
**Complexity:** medium
**Source Reference:** Finding 7

**User Story:** As someone running ralpher with worktrees, I want one place that says whether a worktree is used and which base ref it has, so that the git checks, the verifier, the hooks and the agent all agree.

**Subtasks:**

- [ ] Tests in `src/tests/test_options.py`: `--args` containing `--worktree`, `-w` or `--settings` raises `InvalidArgsError` naming the ralpher option to use instead (`--worktree`; for `--settings`, ralpher's settings files); confirm they fail first
- [ ] Raise it in `RalpherOptions.__post_init__`, replacing the warning that `args_override_warnings` gives for these flags; remove the branches in `iteration.add_worktree_arg` and `giter.worktree_base_ref` that read them from `--args`
- [ ] Drop the `iteration` parameter of `iteration.summary` and use `context.iteration`
- [ ] Test and fix `hooks.unblock_prompt`: when the worktree lookup fails, the prompt says the worktree tasks file could not be found and names the main tasks file as such
- [ ] Update `docs/reference/cli.md` and `docs/guide/worktrees.md` for the refused flags

**Acceptance Criteria:**

- [ ] `--args '... --worktree x'` stops before the first iteration with an `Error:` line
- [ ] No reader of `options.worktree` can disagree with the agent's command line

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_options.py` and `src/tests/test_hooks.py`
- [ ] `uv run pytest src/tests/test_options.py src/tests/test_iteration.py src/tests/test_giter.py src/tests/test_hooks.py src/tests/test_verifier.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Task 2 (`InvalidArgsError`)
- Key files: `src/ralphlib/options.py` (`__post_init__`, `args_override_warnings`), `src/ralphlib/iteration.py` (`add_worktree_arg`, `summary`, `run`), `src/ralphlib/giter.py` (`worktree_base_ref`), `src/ralphlib/hooks.py` (`unblock_prompt`)
- The review recommends refusing only these flags; if another `--args` flag turns out to conflict the same way, stop for the user

---

## Task 8: At least one iteration, and tool inputs summarised

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Finding 10

**Technical Goal:** Stop a zero-iteration run from reporting success, and keep raw tool input out of the state file and the summary.

**Subtasks:**

- [ ] Test in `src/tests/test_options.py`: `--iterations 0` and a negative value raise a ralpher error; confirm it fails first. Raise it in `RalpherOptions.__post_init__` and state the minimum in `docs/reference/cli.md`
- [ ] Test in `src/tests/test_iteration.py`: a tool input with no recognised field records the tool name and the input's size in the state and summary, not the raw input; change the fallback in the tool-use summary path (`iteration.py`, near line 288)

**Acceptance Criteria:**

- [ ] `--iterations 0` stops with an `Error:` line and status 1
- [ ] No raw tool input reaches `state.json` or the summary

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_options.py` and `src/tests/test_iteration.py`
- [ ] `uv run pytest src/tests/test_options.py src/tests/test_iteration.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Key files: `src/ralphlib/options.py`, `src/ralphlib/iteration.py`

---

## Task 9: Hook events and polls stop repeating fixed work

**Status:** todo
**Priority:** low
**Complexity:** medium
**Source Reference:** Finding 8

**Technical Goal:** Compute what does not change during a run once, and stop the per-poll and per-event work review-3 A14, A21, P2 and P3 list.

**Subtasks:**

- [ ] In `src/ralphlib/hooks.py`, compute the run-fixed part of the hook context (time zone, resolved `cwd` and tasks-file paths, `ralpher_root`, the icon and sound checks) once per run, and cache compiled templates in one `SandboxedEnvironment`; keep `last_commit_summary` per event (HEAD can change) but reuse the repository path found once
- [ ] In `src/ralphlib/verifier.py`, guard `worktree_task_file`'s cache with a lock
- [ ] In the poll loop of `iteration.process`, re-read the tasks file only when its modification time or size has changed
- [ ] Add tests: the template cache compiles each template once across two events (`src/tests/test_hooks.py`); the poll does not re-read an unchanged tasks file (`src/tests/test_iteration.py`); two threads calling `worktree_task_file` run `git worktree list` once once the worktree exists (`src/tests/test_verifier.py`)

**Acceptance Criteria:**

- [ ] Hook output for every existing hook test is unchanged
- [ ] The new tests pass

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_hooks.py`, `src/tests/test_iteration.py` and `src/tests/test_verifier.py`
- [ ] `uv run pytest src/tests/test_hooks.py src/tests/test_iteration.py src/tests/test_verifier.py src/tests/test_process_termination.py` passes

**Notes:**

- Key files: `src/ralphlib/hooks.py` (`make_context`, `render_hook_args`, `event`), `src/ralphlib/verifier.py`, `src/ralphlib/iteration.py` (`process`)
- Moving hooks off the stdout reader thread (P2) is not recommended by the review; leave it

---

## Task 10: Accurate `Raises` sections, fewer late mutations and pure-named I/O

**Status:** todo
**Priority:** low
**Complexity:** medium
**Source Reference:** Findings 11 and 12

**Technical Goal:** Clear the A4, A8, A9 and A15 hits review-3 lists, except `current_iteration`, which stays by the review-2 answer of 2026-11-02.

**Subtasks:**

- [ ] Add `GitError` to the `Raises:` sections of `hooks.make_context`, `iteration.process` and `verifier.agent_task_file`
- [ ] Resolve `cwd` and `task_file` in `options.parse_options` (renamed `load_options` below) (or one helper it calls) before the options reach `loop`, and remove the reassignments in `looper.loop`
- [ ] Build `verifier.TaskStatus` with its status in `parse_tasks`
- [ ] Rename the functions whose pure-sounding names hide I/O, and update every caller and test: `giter.get_origin` to `read_origin`, `get_current_branch` to `read_current_branch`, `get_upstream_branch` to `read_upstream_branch`, `is_working_tree_clean` to `working_tree_is_clean`, `is_git_repo` to `opens_as_repo`, `has_unpushed_commits` to `fetch_unpushed_state`, `options.parse_options` to `load_options`, `verifier.check_stop` to `verify_stop`, and `find_dangling_symlinks` in `bin/install-claude.py` to `report_dangling_symlinks`
- [ ] Build the `ERROR` and `END` event contexts and the iteration-end time fields in one helper in `looper.py`
- [ ] Leave `iteration_count`, `settings`, `worktree_task_path`, `in_progress_tasks`, `complete` and `error` as run-time state, and add a one-line docstring to each field in `RalpherOptions` and `IterationContext` that says it is set at run time

**Acceptance Criteria:**

- [ ] `uv run pytest` over the test files below passes with the renamed functions
- [ ] No caller of a renamed function remains under its old name (`rg`)

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_giter.py src/tests/test_looper.py src/tests/test_options.py src/tests/test_verifier.py src/tests/test_hooks.py src/tests/test_iteration.py` passes

**Notes:**

- Depends on Tasks 4, 5 and 7 (they change `giter.py` and `options.py`)
- Key files: `src/ralphlib/giter.py`, `src/ralphlib/options.py`, `src/ralphlib/looper.py`, `src/ralphlib/verifier.py`

---

## Task 11: The user docs match the code

**Status:** todo
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding 4

**User Story:** As someone reading the ralpher guide, I want every page to describe what ralpher does, so that I can rely on it.

**Subtasks:**

- [ ] Test in `src/tests/test_looper.py`: for a one-part `--task-file` (`TASKS.md`), `print_cleanup_cmds` and a run name the same worktree; confirm it fails first, then make `--cleanup` resolve `--task-file` the way `loop` does (Task 10 moves that resolution into `load_options`, which may already fix it)
- [ ] `docs/reference/variables.md`: a `--vars` key that names a built-in is rejected
- [ ] `docs/guide/worktrees.md`: correct the `TASKS.md` row and the `--cleanup` sentence; describe the "cannot tell whether there are unpushed commits" question (default no, exits on no)
- [ ] `docs/reference/exit-statuses.md`: the divergence check exits when you answer yes
- [ ] `docs/reference/scripts.md`: `rcl.sh` also needs `RALPHER_PATH`
- [ ] Read every page under `docs/` once more against the code changed by Tasks 1-10, and correct anything those tasks left behind

**Acceptance Criteria:**

- [ ] Each Doc5 hit in review-3 is fixed

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists `src/tests/test_looper.py`
- [ ] `uv run pytest src/tests/test_looper.py src/tests/test_templater.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Tasks 1-10
- Key files: `docs/reference/variables.md`, `docs/guide/worktrees.md`, `docs/reference/exit-statuses.md`, `docs/reference/scripts.md`, `bin/ralpher.py`, `src/ralphlib/looper.py` (`print_cleanup_cmds`, `cleanup_cmds`)

---

## Task 12: Test gaps

**Status:** todo
**Priority:** low
**Complexity:** medium
**Source Reference:** Finding 13

**Technical Goal:** Cover the functions review-3 T1, T2 and T3 list.

**Subtasks:**

- [ ] `src/tests/test_looper.py`: a `loop` end-to-end test with the fake agent (`src/tests/fixtures/fake_agent.py`) and a real `iteration.run`, asserting the exit status, the hooks fired and the state written
- [ ] `src/tests/test_ralpher.py` (new, for `bin/ralpher.py`): the `--cleanup` exit, a `RalpherError` exit printing `Error: ...`, and the exit statuses 0 and 1
- [ ] `src/tests/test_install_claude.py`: `install_claude` (dotfiles skipped, directories and files linked) and `main`'s error exit
- [ ] `src/tests/test_giter.py`: `last_commit_summary` in a real repository, and `confirm_git_state` with `YNConfirm.ask` patched: not a repository, a dirty tree, divergence
- [ ] Property tests (`@hypothesis.settings(max_examples=20, deadline=10000)`) for `giter.redact_url`, `verifier.verify_stop`, `iteration.add_worktree_arg`, `giter.claude_worktree_base_ref`, `settings.load_settings`, `options.RalpherOptions.__post_init__`, `iteration.process_user`, `iteration.process_assistant`, `iteration.get_run_in_background` and `iteration.process_result`; where one does not fit, say why in the test module and add an example test

**Acceptance Criteria:**

- [ ] Every function in review-3 T1 and T2 has a test, or the module says why a property test does not fit

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `git show --stat HEAD` lists every test file named above
- [ ] `uv run pytest src/tests/test_looper.py src/tests/test_ralpher.py src/tests/test_install_claude.py src/tests/test_giter.py src/tests/test_verifier.py src/tests/test_iteration.py src/tests/test_settings.py src/tests/test_options.py` passes

**Notes:**

- Depends on Tasks 1-11 (they change these functions)
- Use the names Task 10 gives the renamed functions (`verify_stop`, `load_options`, ...)

---

## Task 13: Standards

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Finding 16

**Technical Goal:** Clear the S2, S3 and S4 hits review-3 lists.

**Subtasks:**

- [ ] Rename the lower_snake module constants in `src/ralphlib/iteration.py` and `src/ralphlib/types.py` to UPPER_SNAKE and update every reader
- [ ] Move the `TYPE_CHECKING` block in `src/ralphlib/printer.py` directly after the imports
- [ ] Delete the obvious comments and the commented-out code review-3 S4 lists, and the task-number section banners in `src/tests/test_iteration.py`
- [ ] Sort the literals review-3 S4 lists; where the order carries meaning, keep it and add a scoped `non-alphabetical-literal` accept marker giving the reason
- [ ] Replace `.format()` in `src/tests/test_iteration.py` with an f-string; make `LoopRun` in `src/tests/test_looper.py` a dataclass
- [ ] Move the tests in `src/tests/test_shlex.py` into `src/tests/test_hooks.py`, those in `src/tests/test_process_termination.py` into `src/tests/test_iteration.py`, and the `make_context` test in `src/tests/test_verifier.py` into `src/tests/test_iteration.py`; delete the emptied files

**Acceptance Criteria:**

- [ ] Each S2, S3 and S4 hit in review-3 is fixed or carries a scoped marker with a reason
- [ ] The number of collected tests is unchanged by the moves (`uv run pytest --collect-only -q` before and after)

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_iteration.py src/tests/test_hooks.py src/tests/test_looper.py src/tests/test_verifier.py src/tests/test_printer.py src/tests/test_giter.py src/tests/test_settings.py` passes

**Notes:**

- Depends on Task 12 (it adds tests to the files this task reorganises)

---

## Task 14: AGENTS.md and the specs match the repository, then the whole-tree gates

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Findings 14 and 15

**Technical Goal:** Bring `AGENTS.md` and both specs up to date with the code this list leaves, then run the whole-tree checks before the branch merges.

**Subtasks:**

- [ ] `AGENTS.md` project structure: add `test_install_claude.py` and `test_ralpher.py`, remove `test_shlex.py` and `test_process_termination.py`, add the top-level project files and `.github/`, and show `claude/commands/rrq.md`
- [ ] `AGENTS.md` tools list: add shellcheck and the shared repository's `no-project-names` hook
- [ ] `agents/specs/verified-stop/spec.md`: bring the API section and `READ_ERRORS` up to date, and trim it to about 200 lines and eight top-level sections
- [ ] `agents/specs/auditme-adoption/spec.md`: correct the fetch-handling rows, remove the stale `int(...)` row and the marker that does not exist, and restate the parts of the shared `project-setup` skill the spec relies on
- [ ] Run `pre-commit run --all-files` and `pre-commit run --hook-stage pre-push auditme-all --all-files`
- [ ] Run every test file that imports a module this list changed: every file in `src/tests/` that imports `ralphlib` or loads `bin/`
- [ ] After the list's last commit, update `agents/audit-reviews/summary.md`: move the findings this list resolved to Recently resolved (auditme step 8b)

**Acceptance Criteria:**

- [ ] Each Doc1, Doc2, Doc4 and spec-review hit in review-3 is fixed

**Definition of Done:**

- [ ] `pre-commit run --all-files` passes
- [ ] `pre-commit run --hook-stage pre-push auditme-all --all-files` passes
- [ ] `uv run pytest src/tests/test_giter.py src/tests/test_hooks.py src/tests/test_install_claude.py src/tests/test_iteration.py src/tests/test_logger.py src/tests/test_looper.py src/tests/test_options.py src/tests/test_printer.py src/tests/test_ralpher.py src/tests/test_settings.py src/tests/test_signals.py src/tests/test_state.py src/tests/test_templater.py src/tests/test_verifier.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Tasks 1-13
