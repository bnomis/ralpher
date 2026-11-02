# Audit Summary

**Last updated:** 2026-11-02
**Last review:** review-3
**Total reviews conducted:** 3
**Last script run hit count:** 13 (13 accepted)
**Script version:** `ccecce19de80b8adc9b53eb38a4dfa3d3128047a1ae3affb940cf9f3d6120c2b`

## Unresolved findings

Each finding has its full location list in [review-3.md](review-3.md). Review-3 Decision 1 was answered on 2026-11-02: the `except Exception` in `loop` stays, with a scoped accept marker.

### A state-lock timeout ends the run in a raw traceback

- **Rule or category:** A1, A3
- **Severity:** medium
- **Location:** `src/ralphlib/state.py:93`
- **First raised:** review-3 (2026-11-02), Finding 1
- **Description:** after its retries, `filelock.Timeout` leaves `add_to_state` untranslated and ends ralpher in a traceback.
- **Recommendation:** translate it to `StateFileError`; add a held-lock test.

### A bad settings file or `--args` value ends in a raw traceback

- **Rule or category:** Sec2, Doc5
- **Severity:** medium
- **Location:** `bin/ralpher.py:10`, `src/ralphlib/options.py:141`, `src/ralphlib/settings.py:53`
- **First raised:** review-3 (2026-11-02), Finding 2
- **Description:** `parse_options` runs outside `main`'s `try`; `shlex` and non-object settings errors are untranslated.
- **Recommendation:** move `parse_options` inside the `try` and raise domain errors.

### Hook settings of the wrong shape run the wrong commands

- **Rule or category:** Sec2
- **Severity:** medium
- **Location:** `src/ralphlib/hooks.py:76`, `:70`
- **First raised:** review-3 (2026-11-02), Finding 3
- **Description:** a string hook entry runs each character as a command; `hook_templates: "false"` is truthy.
- **Recommendation:** validate settings shapes when they load.

### The user docs contradict the code

- **Rule or category:** Doc5
- **Severity:** medium
- **Location:** `docs/reference/variables.md:17`, `docs/guide/worktrees.md`, `docs/reference/exit-statuses.md`, `docs/reference/scripts.md`
- **First raised:** review-3 (2026-11-02), Finding 4
- **Description:** `--vars` built-ins, the one-part worktree name, the fetch-failure question, the divergence exit, expected-error exits and `rcl.sh`.
- **Recommendation:** correct each page; make `--cleanup` resolve `--task-file` as `loop` does.

### Untranslated I/O errors

- **Rule or category:** A1, A2
- **Severity:** medium
- **Location:** `src/ralphlib/giter.py`, `src/ralphlib/iteration.py:381-420`, `:661`, `bin/install-claude.py`
- **First raised:** review-2 (2026-11-02), narrowed in review-3 Finding 5
- **Description:** `git.GitCommandNotFound`, a missing origin and log-file write errors escape untranslated.
- **Recommendation:** widen the giter handlers; wrap the log writes in one helper.

### Broad handlers that the coding standard does not allow

- **Rule or category:** A19, S4
- **Severity:** medium
- **Location:** `src/ralphlib/giter.py:43`, `src/ralphlib/looper.py:142`
- **First raised:** review-3 (2026-11-02), Finding 6
- **Description:** `suppress(BaseException)` swallows everything; `loop` catches every iteration failure.
- **Recommendation:** narrow `last_commit_summary`; keep the `loop` handler with a scoped accept marker (review-3 Decision 1).

### The prompt file is rendered outside the sandbox

- **Rule or category:** Sec3
- **Severity:** medium
- **Location:** `src/ralphlib/templater.py:85`, `docs/guide/hooks.md:45`
- **First raised:** review-3 (2026-11-02), Finding 9
- **Description:** prompts use a plain `jinja2.Template`; the hooks guide recommends `sh -c` without a warning.
- **Recommendation:** render prompts in the sandboxed environment; add the warning.

### Worktree precedence and the unblock prompt

- **Rule or category:** A5, A22
- **Severity:** low
- **Location:** `src/ralphlib/iteration.py:184`, `src/ralphlib/giter.py:239`, `src/ralphlib/hooks.py:89`
- **First raised:** review-2 (2026-11-02), Finding 8; remainder in review-3 Finding 7
- **Description:** `--worktree`/`--settings` in `--args` still diverge from what ralpher reads; `unblock_prompt` names the wrong file on a lookup failure.
- **Recommendation:** reject those flags in `--args`; fix the prompt text.

### Repeated work per hook event and per poll

- **Rule or category:** A14, A21, P2, P3
- **Severity:** low
- **Location:** `src/ralphlib/hooks.py`, `src/ralphlib/verifier.py:93-106`, `src/ralphlib/iteration.py:827`, `:867`
- **First raised:** review-2 (2026-11-02), Finding 9; remainder in review-3 Finding 8
- **Description:** per-event repository opens and template compiles, per-poll tasks-file reads, an unlocked worktree cache.
- **Recommendation:** compute the run-fixed context once, cache templates, read the tasks file on change, lock the cache.

### Small input checks

- **Rule or category:** Sec2, Sec5
- **Severity:** low
- **Location:** `src/ralphlib/options.py:26`, `src/ralphlib/iteration.py:288`
- **First raised:** review-3 (2026-11-02), Finding 10
- **Description:** `--iterations 0` exits 0; an unrecognised tool input is stored whole.
- **Recommendation:** require at least one iteration; store the tool name and size.

### Raises sections omit `GitError`

- **Rule or category:** A4
- **Severity:** low
- **Location:** `src/ralphlib/hooks.py:109`, `src/ralphlib/iteration.py:459`, `src/ralphlib/verifier.py:113`
- **First raised:** review-3 (2026-11-02), Finding 11
- **Description:** `GitError` reaches each caller undeclared.
- **Recommendation:** declare it.

### Late mutation, pure-named I/O and duplicated event contexts

- **Rule or category:** A8, A9, A15
- **Severity:** low
- **Location:** see review-3 A8, A9, A15
- **First raised:** review-2 (2026-11-02), Findings 14 and 15; remainder in review-3 Finding 12
- **Description:** run-time state on `RalpherOptions` besides `current_iteration`; `get_*`/`is_*` git helpers do I/O; end-of-run contexts built twice.
- **Recommendation:** as listed in review-3 Finding 12.

### Test gaps

- **Rule or category:** T1, T2, T3
- **Severity:** low
- **Location:** see review-3 T1, T2, T3
- **First raised:** review-3 (2026-11-02), Finding 13
- **Description:** `bin/ralpher.py` `main`, `confirm_git_state` and a `loop` end-to-end run are untested; ten functions lack property tests.
- **Recommendation:** as listed in review-3 Finding 13.

### AGENTS.md drift

- **Rule or category:** Doc1, Doc2
- **Severity:** low
- **Location:** `AGENTS.md:40-106`
- **First raised:** review-1 (2026-03-30), recurring; review-3 Finding 14
- **Description:** the tree and the tools list differ from the repository.
- **Recommendation:** update both sections.

### Spec drift

- **Rule or category:** Doc4, spec review
- **Severity:** low
- **Location:** `agents/specs/verified-stop/spec.md`, `agents/specs/auditme-adoption/spec.md`
- **First raised:** review-3 (2026-11-02), Finding 15
- **Description:** API, `READ_ERRORS` and fetch rows the code has moved past; verified-stop over the size guideline.
- **Recommendation:** update both specs.

### Standards

- **Rule or category:** S2, S3, S4
- **Severity:** low
- **Location:** see review-3 S2, S3, S4
- **First raised:** review-3 (2026-11-02), Finding 16
- **Description:** lower_snake constants, comments, unsorted literals, test modules that mirror no source module.
- **Recommendation:** as listed in review-3 Finding 16.

## Recently resolved

| Finding | Severity | Raised in | Resolved in |
|---------|----------|-----------|-------------|
| An exception during an iteration exits 0 as "completed all iterations" | high | review-2 | tasks-2 Task 1 |
| An unreadable state file is replaced by an empty one | high | review-2 | tasks-2 Task 2 |
| The state-lock timeout is swallowed, so the retry never runs | high | review-1 | tasks-2 Task 3 |
| Agent errors with a non-`success` subtype are ignored | medium | review-2 | tasks-2 Task 4 |
| Repository-local settings can run commands without consent (trust model documented) | medium | review-2 | tasks-2 Task 10 |
| Invalid `--vars` fails mid-iteration with a traceback | medium | review-2 | tasks-2 Task 5, tests in `2c14229` |
| Untranslated I/O errors | medium | review-2 | tasks-2 Task 6 |
| Broad graceful-degradation handlers | medium | review-2 | tasks-2 Task 7 |
| Worktree and tasks-file precedence: one resolver for hooks and verifier (the rest is review-3 Finding 7) | medium | review-2 | tasks-2 Task 8 |
| Repeated git subprocesses: the worktree path cached once found (the rest is review-3 Finding 8) | medium | review-2 | tasks-2 Task 8 |
| No end-to-end test of the iteration runner | medium | review-2 | tasks-2 Task 9 |
| Documentation drift | medium | review-1 | tasks-2 Tasks 10 and 11 |
| Logged agent output and remote URLs | low | review-2 | tasks-2 Task 12 |
| Unchecked paths from user input | low | review-2 | tasks-2 Task 12 |
| Pure-named functions with side effects: the interactive `check_*` functions and `has_unpushed_commits` (the rest are review-3 Finding 12) | low | review-2 | tasks-2 Task 13 |
| Late dataclass mutation: `IterationContext` (the remaining sites are review-3 Finding 12) | low | review-2 | tasks-2 Task 13 |
| Duplicated console construction and other A13/A15 hits | low | review-2 | tasks-2 Task 13 |
| Standards (S1, S4) | low | review-2 | tasks-2 Task 13 |
| Property-test gaps | low | review-2 | tasks-2 Task 14, then property tests in `src/tests/` on 2026-11-02 |
| `signals.py` calls `console_print` without `options` | high | review-1 | review-2 |
| `check_repo_clean` calls `lines_to_text` without `options` | high | review-1 | review-2 |
| `check_repo_clean` `options` annotation | medium | review-1 | review-2 |
| `YNConfirm.make_prompt` annotations | low | review-1 | review-2 |
| Hook template injection surface | medium | review-1 | review-2 |
| Plugin dependencies flagged by D2 | low | review-2 | review-3 (checker carve-out of 2026-11-02) |

## Recurring patterns

- AGENTS.md project structure falls behind the tree (review-1, review-2, review-3)
- Broad `except` that logs and carries on (review-1 `state.py`, review-2, review-3)
- User docs fall behind behaviour changes (review-2, review-3)
- A task-list fix closes the review's recommendation but leaves other sites the same question named (review-3 on review-2 Findings 8, 9, 14, 15)

## Checker changes since the last review

- None since review-2. The D2 carve-out for plugins and themes (2026-11-02) is Phase B text only, and cleared review-2 Finding 19 as expected.
