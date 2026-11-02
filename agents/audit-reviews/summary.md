# Audit Summary

**Last updated:** 2026-11-02
**Last review:** review-2
**Total reviews conducted:** 2
**Last script run hit count:** 12 (12 accepted)
**Script version:** `ccecce19de80b8adc9b53eb38a4dfa3d3128047a1ae3affb940cf9f3d6120c2b`

## Unresolved findings

Each finding has its full location list in [review-2.md](review-2.md). The
other review-2 findings were fixed by
[tasks-2.md](../tasks/audit-reviews/tasks-2.md), merged on 2026-11-02 in
`8d320ce`, and are listed under Recently resolved.

### Property-test gaps

- **Rule or category:** T2
- **Severity:** low
- **Location:** `iteration.py` (`process_line`, `process_stream_event`, `input_field_to_content`, `agent_environment`), `templater.py` (`render`), `logger.py` (`log_file`), `state.py` (`add_to_state`)
- **First raised:** review-2 (2026-11-02), Finding 18
- **Description:** tasks-2 Task 14 added hypothesis tests for some of the listed parsers and formatters; these functions still have example tests only.
- **Recommendation:** add a hypothesis test for each, or say in the test module why one does not fit. Filed in `TODO.md`.

### Plugin dependencies flagged by D2

- **Rule or category:** D2
- **Severity:** low
- **Location:** `pyproject.toml` (`pytest-icdiff`, `pytest-instafail`, `pytest-randomly`, `mkdocs-material`)
- **First raised:** review-2 (2026-11-02), Finding 19
- **Description:** these dependencies are loaded by pytest or mkdocs as plugins or a theme, not imported.
- **Recommendation:** no code change. The checker change noted below should stop the next audit raising them; close this finding then.

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
| Worktree and tasks-file precedence is undocumented | medium | review-2 | tasks-2 Task 8 |
| Repeated git subprocesses per poll and per event | medium | review-2 | tasks-2 Task 8 |
| No end-to-end test of the iteration runner | medium | review-2 | tasks-2 Task 9 |
| Documentation drift | medium | review-1 | tasks-2 Tasks 10 and 11 |
| Logged agent output and remote URLs | low | review-2 | tasks-2 Task 12 |
| Unchecked paths from user input | low | review-2 | tasks-2 Task 12 |
| Pure-named functions with side effects | low | review-2 | tasks-2 Task 13 |
| Late dataclass mutation (`RalpherOptions.current_iteration` stays, by the review-2 answer of 2026-11-02) | low | review-2 | tasks-2 Task 13 |
| Duplicated console construction and other A13/A15 hits | low | review-2 | tasks-2 Task 13 |
| Standards (S1, S4) | low | review-2 | tasks-2 Task 13 |
| `signals.py` calls `console_print` without `options` | high | review-1 | review-2 |
| `check_repo_clean` calls `lines_to_text` without `options` | high | review-1 | review-2 |
| `check_repo_clean` `options` annotation | medium | review-1 | review-2 |
| `YNConfirm.make_prompt` annotations | low | review-1 | review-2 |
| Hook template injection surface | medium | review-1 | review-2 |

## Recurring patterns

- AGENTS.md project structure falls behind the tree (review-1, review-2)
- Broad `except` that logs and carries on (review-1 `state.py`, review-2)

## Checker changes since the last review

- review-1 predates the scripted checker. This review is the baseline, so the next audit on unchanged code should show zero mechanical delta.
- The unused-dependency check (D2 in the auditme checklist) now skips a dependency a declared host tool loads as a plugin or theme, shown by its entry point (shipped in agents on 2026-11-02, Phase B text only). The four D2 hits in review-2 (`pytest-icdiff`, `pytest-instafail`, `pytest-randomly` and `mkdocs-material`) each register such an entry point, so the next audit should not raise them.
