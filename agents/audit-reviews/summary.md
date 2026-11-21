# Audit Summary

**Last updated:** 2026-11-21
**Last review:** review-4
**Total reviews conducted:** 4
**Last script run hit count:** 15 (15 accepted)
**Script version:** `e924b332c5c6809821c1635aa7a1d3714064120de0317c733f7f09dfa6b50537`

## Unresolved findings

All raised in review-4 (2026-11-21); each entry's location and recommendation are in [review-4.md](review-4.md).

### Order-file I/O errors escape `rro` as raw tracebacks

- **Rule or category:** A1, A2
- **Severity:** medium
- **Location:** `src/ralphlib/order.py` `check_test_log`, `read_order`, `set_setting`, `set_status`
- **First raised:** review-4 (2026-11-21)
- **Description:** order-file and test-log reads and writes are untranslated; `bin/rro.py` catches only `RalpherError`.
- **Recommendation:** one pair of translating read/write helpers raising `OrderFormatError`.

### The user docs contradict the code

- **Rule or category:** Doc5
- **Severity:** medium
- **Location:** `docs/concepts.md:59`, `docs/guide/logs.md:76`, `docs/getting-started.md:85`, `docs/guide/worktrees.md:82`, `docs/run-order.md:47`
- **First raised:** review-4 (2026-11-21)
- **Description:** the exception stop and its exit reason are missing; the cleanup output examples differ from what is printed; the example order file is called "the same file".
- **Recommendation:** review-4 Finding 14.

### Error handling and input checks (remainder)

- **Rule or category:** A1, A2, A4, A19, Sec2, Sec4
- **Severity:** low
- **Location:** review-4 Findings 2-6, 8, 9
- **First raised:** review-4 (2026-11-21)
- **Description:** git handlers without `OSError`; `Popen` handlers without `SubprocessError`; fail-soft sites to dismiss in the ledger; `logger.exception` in the reader threads; `process` omits `LogFileError`; `rro set-status` accepts line breaks; the test-log path is not contained (Decision 3).
- **Recommendation:** as review-4 Findings 2-6, 8, 9.

### Late mutation, pure-named I/O and the f-string rule (remainder)

- **Rule or category:** A8, A9, S4
- **Severity:** low
- **Location:** `src/ralphlib/iteration.py:64`, `src/ralphlib/order.py:125`, `:304`, `bin/rro.py:83`, `src/tests/test_order.py:175`
- **First raised:** review-4 (2026-11-21)
- **Recommendation:** review-4 Findings 7 and 10.

### Test gaps

- **Rule or category:** T1, T2
- **Severity:** low
- **Location:** review-4 T1 and T2 lists
- **First raised:** review-4 (2026-11-21)
- **Recommendation:** review-4 Finding 11.

### AGENTS.md and spec drift

- **Rule or category:** Doc1, Doc2, Doc4, spec review
- **Severity:** low
- **Location:** `AGENTS.md`, `agents/specs/auditme-adoption/spec.md`, `agents/specs/verified-stop/spec.md`, `agents/specs/run-order/spec.md`
- **First raised:** review-4 (2026-11-21)
- **Recommendation:** review-4 Findings 12 and 13, Decisions 1 and 2.

## Recently resolved


| Finding | Severity | Raised in | Resolved in |
|---------|----------|-----------|-------------|
| A state-lock timeout ends the run in a raw traceback | medium | review-3 | tasks-3 Task 1 |
| A bad settings file or `--args` value ends in a raw traceback | medium | review-3 | tasks-3 Task 2 |
| Hook settings of the wrong shape run the wrong commands | medium | review-3 | tasks-3 Task 3 |
| The user docs contradict the code | medium | review-3 | tasks-3 Task 11 |
| Untranslated I/O errors (remainder) | medium | review-3 | tasks-3 Task 5 |
| Broad handlers that the coding standard does not allow | medium | review-3 | tasks-3 Task 4 |
| The prompt file is rendered outside the sandbox | medium | review-3 | tasks-3 Task 6 |
| Worktree precedence and the unblock prompt (remainder) | low | review-3 | tasks-3 Task 7 |
| Repeated work per hook event and per poll (remainder) | low | review-3 | tasks-3 Task 9 |
| Small input checks | low | review-3 | tasks-3 Task 8 |
| Raises sections omit `GitError` | low | review-3 | tasks-3 Task 10 |
| Late mutation, pure-named I/O and duplicated event contexts (remainder) | low | review-3 | tasks-3 Task 10 |
| Test gaps | low | review-3 | tasks-3 Task 12 |
| AGENTS.md drift | low | review-1 | tasks-3 Task 14 |
| Spec drift | low | review-3 | tasks-3 Task 14 |
| Standards (S2, S3, S4) | low | review-3 | tasks-3 Task 13 |
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

- AGENTS.md project structure falls behind the tree (review-1, review-2, review-3, review-4)
- Broad `except` that logs and carries on (review-1 `state.py`, review-2, review-3)
- User docs fall behind behaviour changes (review-2, review-3, review-4)
- Untranslated file I/O in a newly added module (review-2, review-3, review-4 `order.py`)
- A task-list fix closes the review's recommendation but leaves other sites the same question named (review-3 on review-2 Findings 8, 9, 14, 15)

## Checker changes since the last review

- (none since review-4)

### Before review-4

- None since review-2. The D2 carve-out for plugins and themes (2026-11-02) is Phase B text only, and cleared review-2 Finding 19 as expected.
- **2026-11-21: the audit hooks moved from `bnomis/agents` (`5912515`) to `bnomis/auditor` (`6a65d14`).** The pin spans every checker change since: `ruff-version-drift`, the widened `raises-section-drift`, the listed Phase B questions and their briefs. The one new hit, `ruff-version-drift` (the ruff hook pinned `v0.17.4`, the lock `0.17.2`), was fixed by lowering the hook to `v0.17.2`. At the new pin the sweep reports 18 hits, **0 unaccepted**, digest `0c9d1583c62118f3d14eb947b980b9dc9ce2b3306e100426a0237e3552278748`.
- **2026-11-21: the names hook moved from `bnomis/agents` to `bnomis/auditor`, and the pin from `6a65d14` to `6747c4e`.** The checker changes in between are the no-root project check and the Stop hook's missing-checker block. At the new pin the sweep reports 15 hits, **0 unaccepted**, digest `e924b332c5c6809821c1635aa7a1d3714064120de0317c733f7f09dfa6b50537`. CI no longer needs the agents deploy key.
