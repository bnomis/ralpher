# Audit Summary

**Last updated:** 2026-11-02
**Last review:** review-2
**Total reviews conducted:** 2
**Last script run hit count:** 12 (12 accepted)
**Script version:** `ccecce19de80b8adc9b53eb38a4dfa3d3128047a1ae3affb940cf9f3d6120c2b`

## Unresolved findings

Each finding has its full location list in [review-2.md](review-2.md).

### An exception during an iteration exits 0 as "completed all iterations"

- **Rule or category:** A19
- **Severity:** high
- **Location:** `src/ralphlib/looper.py:134`
- **First raised:** review-2 (2026-11-02)
- **Description:** `except Exception` breaks out of the loop with `error` False and the exit reason unchanged, so the process exits 0 and the `error` hook does not fire.
- **Recommendation:** remove or narrow the handler, or set the error state and exit reason before breaking. Add a test.

### An unreadable state file is replaced by an empty one

- **Rule or category:** A22, A19
- **Severity:** high
- **Location:** `src/ralphlib/state.py:28`
- **First raised:** review-2 (2026-11-02)
- **Description:** a read or parse failure returns `{}`, and the next save overwrites the file.
- **Recommendation:** return `{}` only for a missing file, and let read failures propagate.

### The state-lock timeout is swallowed, so the retry never runs

- **Rule or category:** A1 (re-verified review-1 Finding 10)
- **Severity:** high
- **Location:** `src/ralphlib/state.py:110`
- **First raised:** review-1 (2026-03-30), changed in review-2
- **Description:** `add_to_state_work` catches `filelock.Timeout` and only logs it, so the `tenacity` retry on `Timeout` never fires, and the update is silently lost.
- **Recommendation:** remove the inner handler. Add a test with a held lock.

### Agent errors with a non-`success` subtype are ignored

- **Rule or category:** Doc5
- **Severity:** medium
- **Location:** `src/ralphlib/iteration.py:897`
- **First raised:** review-2 (2026-11-02)
- **Description:** `is_error` counts only when `subtype == 'success'`.
- **Recommendation:** count `is_error` whatever the subtype, or document the rule.

### Repository-local settings can run commands without consent

- **Rule or category:** Sec3
- **Severity:** medium
- **Location:** `src/ralphlib/settings.py:34`
- **First raised:** review-2 (2026-11-02)
- **Description:** hooks in `<cwd>/.ralpher/settings.json` run as commands.
- **Recommendation:** decide on and document the trust model, or stop loading hooks from that file.

### Invalid `--vars` fails mid-iteration with a traceback

- **Rule or category:** Doc5, Sec2
- **Severity:** medium
- **Location:** `src/ralphlib/templater.py:58`
- **First raised:** review-2 (2026-11-02)
- **Description:** the docs say ralpher stops before the first iteration, but it raises inside iteration 1, and a `--vars` key can override a built-in variable.
- **Recommendation:** validate `--vars` before the loop starts.

### Untranslated I/O errors

- **Rule or category:** A1, A2, A3
- **Severity:** medium
- **Location:** `giter.py`, `looper.py`, `state.py`, `iteration.py`, `settings.py`, `logger.py`, `printer.py`, `verifier.py`, `hooks.py`, `bin/install-claude.py`
- **First raised:** review-2 (2026-11-02)
- **Description:** third-party and `OSError` exceptions escape untranslated, some of them on reader threads. Two `raise` statements use stdlib types.
- **Recommendation:** add domain errors and wrap the listed calls.

### Broad graceful-degradation handlers

- **Rule or category:** A19
- **Severity:** medium
- **Location:** `hooks.py:222`, `iteration.py:233`, `:609`, `:769`
- **First raised:** review-2 (2026-11-02)
- **Description:** each catches `Exception`, logs it and carries on.
- **Recommendation:** narrow each one or remove it, following the no-winner ruling.

### Worktree and tasks-file precedence is undocumented

- **Rule or category:** A5
- **Severity:** medium
- **Location:** `iteration.py:187`, `hooks.py:44`, `giter.py:204`
- **First raised:** review-2 (2026-11-02)
- **Description:** `--args` silently overrides `--worktree` and the base ref, and the hooks and the verifier choose the tasks file by different rules.
- **Recommendation:** have one resolver, used everywhere, with the precedence documented.

### Repeated git subprocesses per poll and per event

- **Rule or category:** A14, A24, P2, P3
- **Severity:** medium
- **Location:** `verifier.py:83`, `hooks.py:44`, `hooks.py:142`, `iteration.py:484`, `:817`
- **First raised:** review-2 (2026-11-02)
- **Description:** `git worktree list` runs on every poll and every hook event.
- **Recommendation:** resolve the worktree path once per iteration, and run the duplicate check first.

### No end-to-end test of the iteration runner

- **Rule or category:** T1, T3
- **Severity:** medium
- **Location:** `src/ralphlib/iteration.py:164`
- **First raised:** review-2 (2026-11-02)
- **Description:** `run`, `make_context`, `unmake_context`, `summary` and the per-line stream branches are untested.
- **Recommendation:** add a test with a child process that emits canned stream-JSON.

### Documentation drift

- **Rule or category:** Doc1-Doc5, spec review
- **Severity:** medium
- **Location:** `AGENTS.md`, `README.md`, `docs/`, `agents/specs/`
- **First raised:** review-1 (2026-03-30, AGENTS.md structure), widened in review-2
- **Description:** the structure tree, the tools list, both specs and several user-doc pages differ from the code.
- **Recommendation:** update each passage listed in review-2.

### Low-severity findings

- **Rule or category:** Sec2, Sec4, Sec5, A8, A9, A10, A13, A15, S1, S4, T2, D2
- **Severity:** low
- **Location:** see review-2 Findings 12-19
- **First raised:** review-2 (2026-11-02). The `looper.py` `open()` calls and the unused `options` parameters in `iteration.py` date from review-1 (2026-03-30)
- **Description:** logged agent output, unchecked paths, impure names, late mutation, duplicated consoles, annotations, ordering, obvious comments, property-test gaps, and plugin dependencies flagged by D2.
- **Recommendation:** as listed in review-2.

## Recently resolved

| Finding | Severity | Raised in | Resolved in |
|---------|----------|-----------|-------------|
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
