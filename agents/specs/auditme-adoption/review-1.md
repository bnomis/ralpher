# Auditme adoption spec: review 1

**Review page:** https://claude.ai/artifact/SV4xDU7XgwLAayHiLScnsm
**Date:** 2026-10-31
**Spec:** `agents/specs/auditme-adoption/spec.md` (version 1.0, proposed)

## What is being reviewed and how

The spec `agents/specs/auditme-adoption/spec.md` (written 2026-10-31 from the
`TODO.md` item "The auditme checker is not adopted here, so its hits accumulate
unrecorded") clears every unaccepted hit the shared auditme checker reports,
then gates commits, pushes and CI on it. The four choices that were yours were
answered on 2026-10-31 and are recorded below as made, not reopened. Each item
below is a choice the spec makes that you have not yet seen: approve it, or
flag it with a comment saying what to change. The work does not start until
every item has an answer; then `/taskdev` breaks the spec into tasks.

## Automatic checks

| Check | Result |
|---|---|
| Every specdev template section present (Module location, API, Error handling, Implementation, External dependencies; Settings omitted, as nothing is configurable) | pass |
| API holds type-annotated signatures with docstrings | pass |
| Module location names paths under `src/` | pass |
| Every rule the checker reported on 2026-10-31 has a row in the Implementation table | pass (each rule in the checker's output appears) |
| Plain ASCII punctuation | pass |
| `pre-commit run --files` on the spec, the index and `TODO.md` | pass |
| `TODO.md` item bodies preserved (`verify_bodies.py`) | pass |

## Choices already made (2026-10-31)

- `.pre-commit-config.yaml` may be changed for this work.
- Every `from X import Y` is converted to a full import path.
- The runtime caches `processed_hooks`, `seen_task_ids` and `log_file_cache`
  are accepted with scoped markers.
- A CI workflow with the audit deploy key is added in this spec.

## The items

1. **`default_settings` becomes a function** (`api-default-settings`). The
   module-level dict is replaced by `default_settings()` returning a fresh
   copy. Cause: the rule flags an exported mutable dict, and the existing
   shallow `.copy()` shares the nested `theme` dict between callers;
   `MappingProxyType` would freeze only the outer level and cannot be
   deep-copied. Tests that patch or copy it change to the function.
2. **Type-name maps wrapped in `MappingProxyType`** (`api-type-maps`).
   `message_type_to_str` and `ralpher_event_type_to_str` are read-only maps
   of strings, so the wrapper changes nothing for readers.
3. **Duplicate `slugify` and `task_file_slug` removed from `iteration.py`**
   (`api-slug-dupes`). `templater.py` has identical bodies and the other
   callers already use it; their tests move to `test_templater.py`.
4. **Clean-check shims removed** (`api-shims`). `is_clean_strict` and
   `is_clean_no_untracked` only call `is_working_tree_clean` with a flag;
   `giter.py` and its tests call that directly.
5. **How the from-imports are rewritten** (`from-import`). `import typing` and
   `typing.TYPE_CHECKING`; TYPE_CHECKING-only `import ralphlib.options` with
   annotations naming `ralphlib.options.RalpherOptions`; `unittest.mock.patch`;
   `hypothesis.given`. Python 3.14's lazy annotations keep this working.
6. **Exception messages: drop or accept** (`except-interpolation`). Where the
   message goes to `loguru.logger.exception`, the `{e}` is dropped because
   the traceback carries it. Where it reaches a person with no traceback (the
   console, the session error log, a stop-check reason, the installer's exit
   message) it is accepted.
7. **Shared test helper module** (`test-helpers`). Identical `make_options`
   bodies in the test modules become one function in `src/tests/helpers.py`;
   a module whose body differs keeps its own.
8. **Repeated test literals named as constants** (`literal-duplication`).
9. **Bare `dict` annotations become `dict[str, typing.Any]`**
   (`bare-dict`).
10. **Explicit JSON `null` in the agent's stream treated as empty**
    (`get-or-empty`). `d.get(k, {})` becomes `d.get(k) or {}` at the four
    stream-parsing sites. This is a behaviour change: today such a `null`
    raises `AttributeError` inside `process_line`. A failing test per site
    comes first.
11. **Leading underscores removed** (`underscores`). `looper.py` stops binding
    the `GracefulTerminator` (the signal module holds its handler, so it stays
    alive, and ruff's unused-variable check exempts only underscore names);
    the test parameters and the `_fast_poll` fixture are renamed.
12. **Broad excepts narrowed** (`narrow-excepts`). The remote fetch catches
    `git.GitCommandError` only and logs a warning as well as printing; the
    task-file number parse catches `ValueError` only. Any other exception now
    propagates, as `AGENTS.md` asks.
13. **Test record copies its inputs** (`store-copy`). `LoopRun` stores
    `list(calls)` and `dict(state)`.
14. **Three hits accepted as checker misses or by design** (`other-accepts`):
    the status list in `test_verifier.py` is ordered by progression; the
    `verifier.py` handler does catch `OSError` through `READ_ERRORS`; the
    installer uses stdlib logging because it runs before the project's
    environment exists.
15. **Hook adoption** (`hooks`). The agents repo is added to
    `.pre-commit-config.yaml` pinned by commit, with `auditme-changed` on
    commit and `auditme-all` on push, only after the hit count is zero.
16. **CI workflow and deploy key** (`ci`). A new `.github/workflows/ci.yml`
    from the shared template runs the tests, pre-commit and the whole-tree
    audit, with every action pinned by SHA; the deploy key and secret are
    made with each GitHub step confirmed when it runs.
17. **`AGENTS.md` note on the gates** (`agents-md`). Says what runs on commit,
    push and CI, and that a hit is fixed or accepted with a scoped marker.
18. **Left out of the spec** (`out-of-scope`). The checker's
    `filesystem-envelope-gap` miss is filed in the shared repository's auditme
    `requests.md` (another repository, so not in this spec), and the stale
    status of the verified-stop spec is fixed separately.

## Decisions

None open: the four that were yours are under "Choices already made".

## Answers

Answered on the review page on 2026-10-31: every item (1 to 18) approved,
with no comments and no flags. The spec stands as written.
