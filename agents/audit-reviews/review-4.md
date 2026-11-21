# Audit Review 4

**Date:** 2026-11-21
**Review page:** https://claude.ai/artifact/Ep3HajQguSm8qzdyckhxGC
**Scope:** full (`agents/specs/`, `src/`, `bin/`, `docs/`, `AGENTS.md`, `README.md`)
**Commit:** `e41c205`
**Script output:** /tmp/audit-ralpher.jsonl (15 hits, 15 accepted, 0 unaccepted)
**Convergence note:** script extended since review-3: the checker digest moved from `ccecce19...` to `e924b332c5c6809821c1635aa7a1d3714064120de0317c733f7f09dfa6b50537` when the audit hooks moved to `bnomis/auditor` on 2026-11-21 (`ruff-version-drift`, the widened `raises-section-drift`, the no-root project check, and the listed Phase B questions with their briefs). The mechanical delta was drained on 2026-11-21, before this audit, so the sweep is again clean. This is the first audit after A1, A4, A11, A17, A19, T1, T2, Doc1, Doc2, Doc4 and Doc5 were listed: every candidate of those questions was judged as new, and their findings in unchanged code are catch-up, not regressions. Review-3 recorded no `**Commit:**`, so every sampled question ran on the whole tree.

## Summary

The mechanical sweep has no unaccepted hit. Phase B ran every question in every category: the listed questions batch by batch through `phaseb.py` (22 batches, every batch checked and merged into `agents/audit-reviews/ledger/`), the sampled ones in seven per-category bundles over the whole tree. No high-severity defect. The most consequential findings are that the order-file reads and writes in `src/ralphlib/order.py` let raw `OSError` and `UnicodeDecodeError` escape `bin/rro.py`'s `RalpherError` envelope, and that five places in the user docs contradict what the code prints or writes. The rest are a missing `SubprocessError`, logger levels, a `Raises` gap, input checks on `rro set-status` and the test-log path, test gaps, and documentation and spec drift.

## Mechanical findings (from checks/audit.py)

None unaccepted. The accepted hits, dismissed by their markers:

| Rule | Accepted |
|------|----------|
| `except-interpolation` | 7 |
| `non-alphabetical-literal` | 4 |
| `mutable-module-level-exported` | 3 |
| `legacy-formatting-percent` | 1 |

## Phase B per-question results

Scope for every question: the non-test files under `src/ralphlib/` and `bin/*.py`; S1-S4 also read `src/tests/`; P and Sec also read `bin/*.sh`; T questions read `src/tests/` as the source of tests.

### Listed questions

Every candidate of every listed question has a current verdict in the ledger; none is unjudged.

| Question | Candidates judged | Open findings |
|----------|-------------------|---------------|
| A1 External call envelope | 16 | 13 |
| A4 Docstring `Raises` accuracy | 15 | 1 |
| A11 Exhaustion via `assert_never` | 5 | 0 |
| A17 Public-surface drift | 2 | 0 |
| A19 Logger level for broad except | 6 | 3 |
| T1 Coverage of branchy logic | 106 | 33 |
| T2 Property-based tests | 6 | 3 |
| Doc1 AGENTS.md project structure | 9 | 1 |
| Doc2 AGENTS.md tools list | 17 | 1 |
| Doc4 Specs match implementation | 133 | 3 |
| Doc5 User docs match implementation | 82 | 5 |

#### A1

- `src/ralphlib/order.py` `check_test_log` - `path.read_text` has no `try`
- `src/ralphlib/order.py` `read_order` - `path.read_text` has no `try`; the docstring promises `OrderFormatError`
- `src/ralphlib/order.py` `set_setting` - `path.read_bytes` and both `path.write_bytes` have no `try`; the second write is the restore inside `except OrderFormatError`, so its failure would mask the original error
- `src/ralphlib/order.py` `set_status` - `path.read_bytes` and both `path.write_bytes` have no `try`
- `src/ralphlib/iteration.py` `process` - the handler around `subprocess.Popen` translates `OSError` to `RalpherError` but not `subprocess.SubprocessError`
- `src/ralphlib/hooks.py` `run_hook` - `subprocess.Popen` failure is logged as a warning and the run carries on (fail-soft by design)
- `src/ralphlib/giter.py` `claude_worktree_base_ref` - `contextlib.suppress(OSError, ValueError)` falls back to `'fresh'` (fail-soft by design)
- `src/ralphlib/verifier.py` `verify_stop` - a read error returns an unverified stop check (fail-soft by design, verified-stop spec)
- `src/ralphlib/verifier.py` `read_tasks` - passes `READ_ERRORS` to its callers by design; every caller catches them
- Not hits: `logger.init` (`LogFileError`), `looper.loop` prompt read (`RalpherError`) and tasks-file read (`TasksFileError`)

#### A4

- `src/ralphlib/iteration.py` `process` - `Raises:` omits `LogFileError`, which reaches it from `log_msg` and `announce_started_tasks` through `write_log`; the declared base `RalpherError` does not count for the subclass

#### A11

No hits. The two `match` statements in `bin/rro.py` match class patterns over dataclasses; the `if` chains in `order.read_order`, `fake_agent.main` and `test_settings` are over plain `str`.

#### A17

No hits. Neither `__init__.py` has `__all__`, and every reader outside the package imports the owning submodule.

#### A19

- `src/ralphlib/iteration.py` `process_stdout` and `process_stderr` - a narrow `(OSError, LogFileError)` handler that degrades (sets the error flag, the reader thread ends) logs with `logger.exception`
- `src/ralphlib/looper.py` `loop` - the broad `except Exception` that ends the run; kept by review-3 Decision 1 (2026-11-02) with a scoped `accept[logger-exception-graceful-degradation]` marker
- Not hits: `iteration.make_context`, `iteration.run`, `state.add_to_state` (log and re-raise)

#### T1

Public functions with branches and no direct test (each is reached only through a caller's tests):

- `bin/rro.py`: `check_log`, `run`, `step_json` (its finished case is never exercised)
- `src/ralphlib/hooks.py`: `fixed_context`, `last_commit_summary`, `local_timezone` (error path untested)
- `src/ralphlib/iteration.py`: `get_tool_input`, `kill_agent`, `last_message_type`, `mark_started`, `open_log_file`, `print_error`, `print_error_eol`, `print_progress`, `print_progress_eol`, `print_progress_lines`, `process_system`, `read_stdout`, `read_task_statuses`, `signal_agent`, `summary`, `unmake_context`, `write_log`
- `src/ralphlib/logger.py`: `state_path`
- `src/ralphlib/looper.py`: `print_cleanup_cmds`, `print_stopping_prompt`, `reject_unverified_stop`
- `src/ralphlib/order.py`: `build_settings`, `default_branch`, `find_root`
- `src/ralphlib/settings.py`: `validate_settings`
- `src/ralphlib/signals.py`: `GracefulTerminator.perform_shutdown`
- `src/ralphlib/state.py`: `add_to_state_work`

#### T2

- `src/ralphlib/hooks.py` `fixed_context` - basename = stem + suffix; `cwd` joined with the relative path gives back the task file
- `src/ralphlib/order.py` `replace_cell` - the replaced cell reads back as the new text, every other cell unchanged
- `src/ralphlib/order.py` `split_cells` - round trip of a row built from cells, escaped bars included

#### Doc1

- `AGENTS.md` Project structure - omits the tracked `claude/templates/` (holding `order-progress.html`) and the tracked `.claude/` (holding only `settings.local.json`)

#### Doc2

- `AGENTS.md` Development tools and libraries - names the `no-project-names` hook but not the `auditme-changed` and `auditme-all` hooks in `.pre-commit-config.yaml`

#### Doc4

- `agents/specs/auditme-adoption/spec.md:56`, `:57`, `:80` - API names `message_type_to_str`, `ralpher_event_type_to_str` and `is_working_tree_clean`; the code has `MESSAGE_TYPE_TO_STR`, `RALPHER_EVENT_TYPE_TO_STR` (`src/ralphlib/types.py:19`, `:48`) and `working_tree_is_clean` (`src/ralphlib/giter.py:119`)
- `agents/specs/auditme-adoption/spec.md:37` - Module location names `bin/install-claude.py`, replaced by `bin/install-claude.sh` on 2026-11-21
- `agents/specs/verified-stop/spec.md:180` - says a missing worktree gives a reason naming `options.task_file` and the error; `verify_stop` returns the `TasksFileError` text `worktree for <slug> not found` (`src/ralphlib/verifier.py:130`, `:144`), as the spec's own line 173 says

#### Doc5

- `docs/concepts.md:59` - the stop conditions (complete, error, termination) read as complete; the loop also stops on an exception in an iteration (`exception during iteration <i>`, exit status 1, `src/ralphlib/looper.py:137-146`), and an I/O failure on the output reader threads also sets the error flag
- `docs/guide/logs.md:76` - the `exit_reason` values omit `exception during iteration <i>`
- `docs/getting-started.md:85-93` - the cleanup example for an `rrq.sh` run omits the leading `cd <repository root> && \` that `--cwd` produces (`bin/rrq.sh:44`, `src/ralphlib/looper.py:306-307`)
- `docs/guide/worktrees.md:82` - the cleanup block omits the `Probable cleanup commands...` header, the two-space indent and, with `--cwd`, the `cd` line
- `docs/run-order.md:47` - calls `agents/tasks/run-order/example-order.md` "the same file" as the example shown; the file has an extra paragraph after its heading (the tables are identical)

### A2 (sampled): Except tuple coverage

- **Mode:** full
- `src/ralphlib/giter.py:44` - reads `repo.head.commit.summary` from `.git` on disk; the tuple `(GitCommandError, GitCommandNotFound, ValueError)` has no `OSError`
- `src/ralphlib/order.py:428` - `read_order(path)` reads the file; the handler catches only `OrderFormatError` (no `OSError`, `UnicodeDecodeError`)
- `src/ralphlib/order.py:446` - `repo.git.symbolic_ref(...)`; the handler catches only `GitCommandError`
- `src/ralphlib/order.py:462` - `git.Repo(root)`; the handler catches only `git.GitError`
- 18 files inspected

### A3 (sampled): Domain-error layering

- **Mode:** full. No hits: every `raise` raises a `RalpherError` subclass or re-raises. 18 files.

### A5 (sampled): Two sources of truth

- **Mode:** full
- `src/ralphlib/looper.py:114` - `options.current_iteration` beside the `iteration` parameter. Settled: kept by the review-2 answer of 2026-11-02; not a finding.
- 18 files inspected

### A6, A7 (sampled)

- **Mode:** full. No hits. 18 files.

### A8 (sampled): Late dataclass mutation

- **Mode:** full
- `src/ralphlib/iteration.py:875` - `context.tasks_signature` set at run time; unlike the other run-time fields its docstring (`src/ralphlib/iteration.py:64`) does not say so
- Settled, not findings: `options.cwd` and `options.task_file` in `options.resolve_paths` (`src/ralphlib/options.py:167`, `:169`), `options.settings` (`src/ralphlib/settings.py:32`), `options.iteration_count` (`src/ralphlib/looper.py:152`), `options.worktree_task_path` (`src/ralphlib/iteration.py:195`, `src/ralphlib/verifier.py:113`) and `context.in_progress_tasks` (`src/ralphlib/iteration.py:476`). Tasks-3 Task 10 (done) chose to resolve the paths in `load_options` and to keep the others as run-time state, each documented as such.
- 18 files inspected

### A9 (sampled): Pure-named function side effects

- **Mode:** full
- `src/ralphlib/order.py:125` - `find_root` tests `is_dir()` on each ancestor
- `src/ralphlib/order.py:304` - `check_test_log` tests `is_file()` and reads the log
- `bin/rro.py:83` - `check_log` reads the order file and the test log
- Not a hit: `src/ralphlib/options.py:173` `load_options` reads the settings files it loads into the options (the `load_` carve-out)
- 18 files inspected

### A10, A12, A13, A14, A15, A16, A18, A20, A21, A22, A23, A24, A25 (sampled)

- **Mode:** full. No hits. A16 was applied to `main` in `bin/ralpher.py` and `bin/rro.py`, as there is no `cli/` package. A20: the three module-level containers read elsewhere (`hooks.processed_hooks`, `hooks.seen_task_ids`, `logger.log_file_cache`) carry accept markers. 18 files each (A16: 2).

### S1-S4 (sampled)

- **Mode:** full
- S1: no hits. `src/tests/`: 0 missing parameter annotations, 0 missing return annotations, 0 modules affected, 20 modules fully annotated.
- S2, S3: no hits.
- S4: `src/tests/test_order.py:175-180` - row templates `L1`-`L4`, `CP`, `FINAL` are filled with `str.format()` throughout the module, against AGENTS.md's f-string rule (`src/ralphlib/order.py:306` formats a user-supplied template and is not a hit)
- 38 files inspected

### P1-P3 (sampled)

- **Mode:** full. No hits. 25 files.

### Sec1-Sec5 (sampled)

- **Mode:** full
- Sec2: `src/ralphlib/order.py:332` - `set_status`, reached from `rro set-status`, writes the status text with only `|` escaped; a line break can break the order table or forge a `Checkpoint after X: passed` line, and unlike `set_setting` it does not re-parse and roll back
- Sec4: `src/ralphlib/order.py:306` - the order file's `test log` setting is joined to the repository root with no containment; an absolute or `..` path makes `rro check-log` read and echo matching lines from a file outside the repository
- Sec1, Sec3, Sec5: no hits. Hook commands from repository settings are a documented trust decision (`docs/guide/hooks.md:22`, `docs/reference/settings.md:16`), considered and not a finding.
- 25 files inspected

### T3 (sampled)

- **Mode:** full. No hits: `TestLoopEndToEnd` (`src/tests/test_looper.py:320`), the fake-agent runs in `src/tests/test_iteration.py`, and `bin/rro.sh` run as a subprocess in `src/tests/test_rro.py:164`.

### D1-D3 (sampled)

- **Mode:** full. No hits. Every import is declared; every declared dependency is imported, run (`pytest`, `ruff`, `mkdocs`) or loaded (`pytest11` entry points of the three pytest plugins, `mkdocs.themes: material`); no lockfile hit.

### Doc3 (sampled)

- **Mode:** full. No hits.

### Coverage (sampled)

New sites found by sampled questions, coverage and not drift: A2 `src/ralphlib/order.py:428`, `:446`, `:462`, `src/ralphlib/giter.py:44`; A8 `src/ralphlib/iteration.py:875`; A9 `src/ralphlib/order.py:125`, `:304`, `bin/rro.py:83`; S4 `src/tests/test_order.py:175`; Sec2 `src/ralphlib/order.py:332`; Sec4 `src/ralphlib/order.py:306`.

## Spec review

Checked against the specdev skill's template and validation criteria:

- `agents/specs/run-order/spec.md` - 357 lines and 9 top-level sections, over the skill's limits of about 200 lines and 8 sections; the API returns `LogVerdict` (line 211) and `list[Decision]` (line 233) without defining either type
- `agents/specs/verified-stop/spec.md` - no "External dependencies" section (GitPython and `re` are named only in the API, line 36); `TasksFileError` is used (line 55) but not declared in the API; 215 lines
- `agents/specs/auditme-adoption/spec.md`, `agents/specs/index.md` - no gaps

## Phase B findings (consolidated)

### Finding 1: Order-file I/O errors escape `rro` as raw tracebacks

- **Category:** A
- **Question:** A1, A2
- **Severity:** medium
- **Location:** `src/ralphlib/order.py` `check_test_log`, `read_order`, `set_setting`, `set_status`; `:428`
- **Description:** every read and write of the order file and the test log runs outside a translating `try`, and the one handler near them (`:428`) catches only `OrderFormatError`. `bin/rro.py` `main` catches only `RalpherError`, so an unreadable or undecodable order file ends `rro` in a traceback instead of its `{error, message}` line and exit 2. The restore write in `set_setting`'s handler would also hide the original error.
- **Recommendation:** read and write the order file through one pair of helpers in `order.py` that translate `OSError` and `UnicodeDecodeError` to `OrderFormatError` naming the path; chain the restore failure to the original error.

### Finding 2: Git handlers without `OSError`

- **Category:** A
- **Question:** A2
- **Severity:** low
- **Location:** `src/ralphlib/giter.py:44`, `src/ralphlib/order.py:446`, `:462`
- **Description:** these handlers catch GitPython's errors but not the `OSError` that reading `.git` from disk can raise.
- **Recommendation:** add `OSError` to each tuple and raise `GitError` from it.

### Finding 3: The agent `Popen` handler misses `SubprocessError`

- **Category:** A
- **Question:** A1
- **Severity:** low
- **Location:** `src/ralphlib/iteration.py` `process`
- **Recommendation:** catch `(OSError, subprocess.SubprocessError)` and raise `RalpherError`.

### Finding 4: Fail-soft I/O sites that A1 flags by its letter

- **Category:** A
- **Question:** A1
- **Severity:** low
- **Location:** `src/ralphlib/hooks.py` `run_hook`, `src/ralphlib/giter.py` `claude_worktree_base_ref`, `src/ralphlib/verifier.py` `verify_stop` and `read_tasks`
- **Description:** each lets no exception escape by design: a failed hook must not stop a run, an unreadable Claude settings file falls back to `fresh`, an unreadable tasks file leaves the stop unverified (verified-stop spec), and `read_tasks` hands `READ_ERRORS` to callers that all catch them.
- **Recommendation:** dismiss each in the ledger (`phaseb.py dismiss`) with that reason. Separately, `run_hook` should also catch `subprocess.SubprocessError`, so the fail-soft path covers every `Popen` failure.

### Finding 5: Logger levels in the reader threads

- **Category:** A
- **Question:** A19
- **Severity:** low
- **Location:** `src/ralphlib/iteration.py` `process_stdout`, `process_stderr`
- **Description:** a narrow, expected I/O failure that sets the error flag is logged with `logger.exception`.
- **Recommendation:** log with `logger.error`; the error flag already reports the failure. The `looper.loop` hit is settled by review-3 Decision 1 and is dismissed in the ledger with that reason.

### Finding 6: `process` omits `LogFileError` from `Raises`

- **Category:** A
- **Question:** A4
- **Severity:** low
- **Location:** `src/ralphlib/iteration.py` `process`
- **Recommendation:** add `LogFileError` to its `Raises:` section.

### Finding 7: Late mutation and pure-named I/O (remainder)

- **Category:** A
- **Question:** A8, A9
- **Severity:** low
- **Location:** `src/ralphlib/iteration.py:64`, `src/ralphlib/order.py:125`, `:304`, `bin/rro.py:83`
- **Description:** `tasks_signature` is run-time state without the "Set at run time" docstring the other such fields carry; `find_root`, `check_test_log` and `rro`'s `check_log` do file-system I/O under pure-sounding names.
- **Recommendation:** add the docstring; rename `find_root` to `discover_root` (as `giter.discover_repo_path`), `check_test_log` to `read_test_log_verdict` and `check_log` to `read_log_verdict`, updating callers and tests. The `rro check-log` subcommand name stays.

### Finding 8: `rro set-status` accepts line breaks

- **Category:** Sec
- **Question:** Sec2
- **Severity:** low
- **Location:** `src/ralphlib/order.py:332`
- **Recommendation:** refuse a status containing `\r` or `\n` with `OrderFormatError`, and re-parse after the write and restore on failure, as `set_setting` does.

### Finding 9: The test-log path is not contained

- **Category:** Sec
- **Question:** Sec4
- **Severity:** low
- **Location:** `src/ralphlib/order.py:306`
- **Description:** see Decision 3.

### Finding 10: f-string rule in `test_order.py`

- **Category:** S
- **Question:** S4
- **Severity:** low
- **Location:** `src/tests/test_order.py:175-180`
- **Recommendation:** replace the `.format()` templates with small functions returning f-strings (`l1(status)`).

### Finding 11: Test gaps

- **Category:** T
- **Question:** T1, T2
- **Severity:** low
- **Location:** the T1 and T2 lists above
- **Recommendation:** add direct tests first for the functions with error paths or real branches (`local_timezone`, `state_path`, `validate_settings`, `build_settings`, `find_root`, `default_branch`, `add_to_state_work`, `signal_agent`, `write_log`, `read_task_statuses`, `reject_unverified_stop`, `step_json` with its finished case); cover the `print_*` family with one parametrised quiet/not-quiet test; add the three property tests T2 names.

### Finding 12: AGENTS.md drift

- **Category:** Doc
- **Question:** Doc1, Doc2
- **Severity:** low
- **Location:** `AGENTS.md` Project structure and Development tools and libraries
- **Recommendation:** add `claude/templates/` to the tree and the `auditme-changed` and `auditme-all` hooks to the tools list; `.claude/` per Decision 1.

### Finding 13: Spec drift and structure

- **Category:** Doc
- **Question:** Doc4, spec review
- **Severity:** low
- **Location:** the Doc4 list and Spec review above
- **Recommendation:** update the three stale names and `bin/install-claude.py` in `agents/specs/auditme-adoption/spec.md`; make `agents/specs/verified-stop/spec.md:180` say what the code does; define `LogVerdict` and `Decision` in the run-order API; add an External dependencies section and declare `TasksFileError` in the verified-stop spec. Length per Decision 2.

### Finding 14: The user docs contradict the code

- **Category:** Doc
- **Question:** Doc5
- **Severity:** medium
- **Location:** the Doc5 list above
- **Recommendation:** add the exception stop to `docs/concepts.md` and `docs/guide/logs.md`; show the cleanup output exactly as printed for an `rrq.sh` run in `docs/getting-started.md` and `docs/guide/worktrees.md`; in `docs/run-order.md` say the file holds the same tables rather than that it is the same file.

## Decisions

### Decision 1: `.claude/settings.local.json` is tracked

- **What is being decided:** whether to stop tracking `.claude/settings.local.json` or list `.claude/` in the AGENTS.md tree.
- **Background:** Doc1 flags `.claude/` as a tracked directory missing from the tree. Its only file is `.claude/settings.local.json`, last committed on 2026-03-30 (`941d768`), which `~/.gitignore:24` now ignores. The security rule names this file as one not to commit. Its contents were not read in this audit.
- **What it affects:** `AGENTS.md` and the repository's tracked files; the local file stays on disk either way.
- **Options:**
  - **Untrack it (recommended):** `git rm --cached .claude/settings.local.json` in the fix commit; `.claude/` then needs no tree entry. It remains in history.
  - **Keep it tracked:** add `.claude/` to the AGENTS.md tree.

### Decision 2: Spec length

- **What is being decided:** whether to split `agents/specs/run-order/spec.md` (357 lines, 9 sections) and `agents/specs/verified-stop/spec.md` (215 lines), which exceed the specdev limits.
- **Background:** both specs are implemented and now serve as the record of their features; the limits exist to keep a spec reviewable before it is built.
- **What it affects:** the two spec files and anything linking into their sections.
- **Options:**
  - **Leave them whole (recommended):** fix only the gaps in Finding 13; splitting an implemented spec costs links and churn for little gain.
  - **Split them:** divide each into specs under the limits, and update links.

### Decision 3: The `test log` setting reaches outside the repository

- **What is being decided:** whether `check_test_log` refuses a test-log path that is absolute or contains `..`.
- **Background:** the order file is repository content, under the same trust as the repository's settings file; `logger.state_path` already refuses absolute and `..` paths with `LogFileError`. The default test-log path is under `ralpher-logs/`.
- **What it affects:** `src/ralphlib/order.py`, its tests and `docs/run-order.md`; an order file that names a log outside the repository would stop working.
- **Options:**
  - **Refuse them (recommended):** raise `OrderFormatError`, as `state_path` does for state paths.
  - **Allow them:** dismiss the finding and document that the path is trusted like the rest of the order file.

## Files reviewed (Phase B)

- `src/ralphlib/*.py` - A1-A25, S1-S4, P1-P3, Sec1-Sec5, D1, T1, T2 candidates
- `bin/ralpher.py`, `bin/rro.py` - A1-A25, S1-S4, P1-P3, Sec1-Sec5, T1
- `bin/*.sh` - Sec1-Sec5, Doc5
- `src/tests/*.py`, `src/tests/fixtures/fake_agent.py` - S1-S4, T1-T3, A11
- `agents/specs/*/spec.md`, `agents/specs/index.md` - Doc4, spec review
- `docs/**/*.md`, `README.md` - Doc3, Doc5
- `AGENTS.md` - Doc1, Doc2, Doc3
- `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `.github/workflows/*.yml`, `mkdocs.yml` - D1-D3, Doc2

## Prior findings re-verified

`summary.md` listed no unresolved finding, and no task file under `agents/tasks/audit-reviews/` has an open item. The review-3 Finding 12 sites still standing (`resolve_paths`, `settings`, `iteration_count`, `worktree_task_path`, `in_progress_tasks`) are the ones tasks-3 Task 10 chose to keep, and are reported above as settled.

## Recommendations

1. Finding 1 and Finding 14 (medium).
2. Findings 2, 3, 4, 8 and 9: the remaining error and input handling.
3. Findings 5, 6, 7, 10, 12 and 13.
4. Finding 11, the test gaps.

## Answers

Answered on the review page on 2026-11-21:

- Findings 1-14: approved, each to be fixed as its recommendation says.
- Decision 1: untrack `.claude/settings.local.json`.
- Decision 2: leave the run-order and verified-stop specs whole; fix only the gaps in Finding 13.
- Decision 3: refuse an absolute or `..` test-log path with `OrderFormatError`.
- No comments were left.
