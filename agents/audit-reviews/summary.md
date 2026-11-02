# Audit Summary

**Last updated:** 2026-11-02
**Last review:** review-3
**Total reviews conducted:** 3
**Last script run hit count:** 13 (13 accepted)
**Script version:** `ccecce19de80b8adc9b53eb38a4dfa3d3128047a1ae3affb940cf9f3d6120c2b`

## Unresolved findings

None. Every review-3 finding was resolved by tasks-3 (Decision 1, answered on 2026-11-02, kept the `except Exception` in `loop` with a scoped accept marker).

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

- AGENTS.md project structure falls behind the tree (review-1, review-2, review-3)
- Broad `except` that logs and carries on (review-1 `state.py`, review-2, review-3)
- User docs fall behind behaviour changes (review-2, review-3)
- A task-list fix closes the review's recommendation but leaves other sites the same question named (review-3 on review-2 Findings 8, 9, 14, 15)

## Checker changes since the last review

- None since review-2. The D2 carve-out for plugins and themes (2026-11-02) is Phase B text only, and cleared review-2 Finding 19 as expected.
