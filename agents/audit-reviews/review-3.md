# Audit Review 3

**Date:** 2026-11-02
**Review page:** https://claude.ai/artifact/37jqLburDyf1BbNKvQ5ogG
**Scope:** full (`agents/specs/`, `src/`, `bin/`, `docs/`, `AGENTS.md`, `README.md`)
**Script output:** /tmp/audit-ralpher.jsonl (13 hits, 13 accepted, 0 unaccepted)
**Convergence note:** clean - script unchanged since review-2 (checker digest `ccecce19de80b8adc9b53eb38a4dfa3d3128047a1ae3affb940cf9f3d6120c2b` both times). The code changed a great deal between the two reviews (the review-2 task list, merged in `8d320ce`, touched every module), so most Phase B hits below are in code that did not exist at review-2. Where a hit is on a line review-2's per-question list did not name, and the line is unchanged since, it is marked **judgement drift** (failure mode 2 in the auditme skill): the S2 naming hits and some S4 hits are of this kind.

## Summary

The mechanical sweep is clean: the one new hit since review-2 is an accepted `except-interpolation` marker at `src/ralphlib/state.py:69`. Phase B ran every question in every category with per-question fan-out, eleven reviewers in all. It finds no high-severity defect. Sixteen findings follow, four of them about how ralpher fails: a state-lock timeout and a bad settings file end in a raw traceback, hook settings of the wrong shape run the wrong commands, and the user docs contradict the code in several places. The rest are untranslated I/O errors, repeated work per hook event and per poll, documentation and spec drift, test gaps and standards.

## Mechanical findings (from checks/audit.py)

None unaccepted. The accepted hits, dismissed by their markers:

| Rule | Accepted |
|------|----------|
| `except-interpolation` | 6 |
| `mutable-module-level-exported` | 3 |
| `non-alphabetical-literal` | 3 |
| `stdlib-logging` | 1 |

## Phase B per-question results

Every question covered the non-test files under `src/ralphlib/` and `bin/*.py`. S1-S4 also covered `src/tests/`; Sec1-Sec3 also covered `bin/*.sh`; T1-T3 read `src/tests/` as the source of tests.

### A1: External call envelope

- `src/ralphlib/giter.py:73` - `pathlib.Path.cwd()` runs before the `try` at line 77; its `FileNotFoundError` escapes
- `src/ralphlib/giter.py:132` - `repo.is_dirty()`: `git.GitCommandNotFound` (a `CommandError`, not `GitCommandError` or `OSError`) gets past the handler
- `src/ralphlib/giter.py:152` - `repo.remotes.origin` raises `AttributeError` when there is no origin; the handler catches `ValueError, OSError`
- `src/ralphlib/giter.py:158` - `origin.fetch()`: `git.GitCommandNotFound` escapes
- `src/ralphlib/giter.py:172` - `repo.iter_commits()`: `git.GitCommandNotFound` escapes
- `src/ralphlib/iteration.py:381`, `:388`, `:394`, `:401`, `:407`, `:414`, `:420` - the log-file `write`/`flush` calls in `write_progress`, `write_progress_lines`, `write_progress_eol`, `write_error`, `write_error_eol`, `write_stdout` and `write_stderr` let `OSError` escape
- `src/ralphlib/state.py:91` - `filelock.Timeout` is re-raised at line 93 and, after tenacity's last attempt, leaves `add_to_state` untranslated; no caller catches it (`looper.py:107`, `:132`, `:171`, `:252`, `:301`) and `bin/ralpher.py:17` catches only `RalpherError`
- `src/ralphlib/state.py:97` - the lock release when `with acquired:` exits does file-system I/O outside any `try`
- `src/ralphlib/verifier.py:103` - `repo.git.worktree('list', ...)` lets `GitCommandError` and `GitCommandNotFound` escape (documented as intended)
- `src/ralphlib/verifier.py:127` - `read_tasks` lets `OSError` and `UnicodeDecodeError` escape (documented as intended)
- `bin/install-claude.py:19`, `:27`, `:33`, `:39`, `:64`, `:87` - `unlink`, `rename`, `symlink_to`, `mkdir`/`iterdir`, `walk`, `iterdir` have no domain translation; only the broad handler in `main` catches them

### A2: Except tuple coverage

- `src/ralphlib/iteration.py:661` - `(orjson.JSONDecodeError, KeyError, TypeError, AttributeError)` has no `OSError`, but the body writes to the errors log at line 659
- `bin/ralpher.py:17` - `except RalpherError` has no `OSError` though `loop` touches disk (transitive: the body is one call)

### A3: Domain-error layering

- `src/ralphlib/state.py:93` - a bare `raise` re-raises `filelock.Timeout` (a `TimeoutError`), which escapes `add_to_state`

### A4: Docstring `Raises` accuracy

- `src/ralphlib/hooks.py:109` - `make_context` declares `RalpherError`; `GitError` also reaches the caller through `giter.last_commit_summary` (`giter.py:82`), unnamed
- `src/ralphlib/iteration.py:459` - `process` declares `RalpherError`; `GitError` reaches it through `hooks.event`, unnamed
- `src/ralphlib/verifier.py:113` - `agent_task_file` declares `TasksFileError`, `git.GitCommandError` and `ValueError`; `GitError` from `giter.discover_repo_path` also reaches the caller and is not a subclass of any of them

### A5: Two sources of truth

- `src/ralphlib/iteration.py:184` - `add_worktree_arg` lets `--worktree`/`-w` in `--args` win; the warning at `options.py:149` documents it, but `verifier.agent_task_file` (`verifier.py:117`), `templater.render` (`:78`), `looper.cleanup_cmds` (`:323`), `giter.confirm_git_state` (`:61`) and `hooks.unblock_prompt` (`:93`) still read `options.worktree`
- `src/ralphlib/giter.py:239` - with `--settings` in `--args`, `worktree_base_ref` reads Claude's settings files, not the JSON the agent receives
- `src/ralphlib/iteration.py:273` - `summary` takes an `iteration` parameter and also has `context.iteration`; they agree only because `run` passes the same value to both

### A6: Stage method dual-path

No hits. Three files have classes with methods; none both returns and mutates `self`.

### A7: Constructor purity

No hits. `signals.py:51` registers signal handlers and stores `options`; `options.py:140` `__post_init__` only calls `shlex.split`.

### A8: Late dataclass mutation

- `src/ralphlib/looper.py:119` - `options.current_iteration` set every iteration (kept by the review-2 answer of 2026-11-02)
- `src/ralphlib/looper.py:155` - `options.iteration_count` set every iteration
- `src/ralphlib/looper.py:32` - `options.cwd` reassigned to the resolved path
- `src/ralphlib/looper.py:72` - `options.task_file` reassigned to the resolved path
- `src/ralphlib/settings.py:32` - `load_settings` assigns `options.settings` (updated in place at `:53`)
- `src/ralphlib/iteration.py:195` - `make_context` clears `options.worktree_task_path`
- `src/ralphlib/verifier.py:105` - `worktree_task_file` sets `options.worktree_task_path`
- `src/ralphlib/verifier.py:68` - `parse_tasks` sets `current.status` after constructing `TaskStatus`
- `src/ralphlib/iteration.py:475` - `process` assigns `context.in_progress_tasks`
- `src/ralphlib/iteration.py:98` - `set_complete` assigns `context.complete`
- `src/ralphlib/iteration.py:110` - `set_error` assigns `context.error`

### A9: Pure-named function side effects

- `src/ralphlib/giter.py:85` - `is_git_repo` opens a repository on disk
- `src/ralphlib/giter.py:122` - `is_working_tree_clean` runs `git status`
- `src/ralphlib/giter.py:142` - `has_unpushed_commits` fetches, runs `rev-list` and prints
- `src/ralphlib/giter.py:178` - `get_upstream_branch` reads refs and prints
- `src/ralphlib/giter.py:216` - `get_origin` reads refs
- `src/ralphlib/giter.py:228` - `get_current_branch` reads `HEAD`
- `src/ralphlib/options.py:156` - `parse_options` reads up to three settings files
- `src/ralphlib/verifier.py:130` - `check_stop` reads the tasks file and runs `git worktree list`
- `bin/install-claude.py:61` - `find_dangling_symlinks` walks the filesystem and prints

### A10: Predicate semantics

No hits. `has_unpushed_commits` now returns `bool | None` and documents `None`.

### A11: Exhaustion via assert_never

No hits.

### A12: assert misuse

No hits. No `assert` outside tests.

### A13: Same value to multiple structural slots

No hits. The `Popen` callers (`hooks.py:226`, `iteration.py:463`) are explained by docstrings; `verifier.unverified` is the factory for `StopCheck`.

### A14: Repeated computation per request

- `src/ralphlib/verifier.py:95` - until the worktree exists, every 3-second poll runs `discover_repo_path` (a new `git.Repo`) and `git worktree list`
- `src/ralphlib/giter.py:38` - `last_commit_summary` opens a new `git.Repo` on every hook event (through `hooks.py:143`, `:186`)
- `src/ralphlib/hooks.py:121` - `make_context` resolves `options.cwd` and `options.task_file` again on every event (`:121`, `:125`), though `looper.py:32`, `:72` already resolved them

### A15: Duplicate constructor / serialisation logic

- `src/ralphlib/looper.py:258` - the `ERROR` and `END` event contexts (`:258`, `:270`) are the same dict built twice
- `src/ralphlib/looper.py:176` - the `ITERATION_END` context repeats the time fields of the state payload at `:166`

### A16: CLI entry envelope

No hits. There is no `cli/*.py` and no `run_*` entry function.

### A17: Public-surface drift

No hits.

### A18: Hot-path setup

No hits. No callback methods.

### A19: Wrong logger level for broad-except

- `src/ralphlib/looper.py:142` - `except Exception` logs with `logger.exception`, sets `error` and the exit reason and breaks, so the run ends as an error with hooks and state written. It also catches expected `RalpherError` failures inside `iteration.run` and logs them with a traceback
- `src/ralphlib/giter.py:43` - `contextlib.suppress(BaseException)` swallows every failure, `KeyboardInterrupt` and `SystemExit` included, and returns `''`

### A20: Mutable module-level singleton

- `src/ralphlib/hooks.py:30`, `:32`, `src/ralphlib/logger.py:12` - accepted by marker: "process-lifetime cache, mutated at run time; tests reset it"

### A21: Lazy init race

- `src/ralphlib/verifier.py:93` - `worktree_task_file` caches `options.worktree_task_path` with no lock; the poll loop and the stdout reader thread (through `hooks.unblock_prompt`) can both run `git worktree list` and assign it

### A22: Fall-through after partial handling

- `src/ralphlib/hooks.py:89` - when `agent_task_file` raises, `unblock_prompt` falls back to `options.task_file` and still says "worktree task file", naming the main checkout's copy

### A23: Discarded multi-return

No hits.

### A24: Identity of subprocess / shell-out calls

No hits. The worktree lookup is cached once found; HEAD can change between hook events.

### A25: Shallow immutable wrapper

No hits. `types.message_type_to_str`, `types.ralpher_event_type_to_str`, `verifier.READ_ERRORS` and `templater.BUILTIN_VARS` hold only immutable members.

### S1: Type annotations on every signature

No hits in non-test source. `src/tests/`: 0 missing parameter annotations, 0 missing return annotations, 0 modules affected, every module fully annotated.

### S2: Naming

Judgement drift: review-2 reported no S2 hits on these unchanged lines.

- `src/ralphlib/iteration.py:32` - module constant `task_progress_re` is lower_snake
- `src/ralphlib/iteration.py:78` - `tool_id_regex`
- `src/ralphlib/iteration.py:80` - `background_tools_list`
- `src/ralphlib/iteration.py:82` - `background_task_tool_name`
- `src/ralphlib/iteration.py:84` - `newline_types`
- `src/ralphlib/types.py:19` - `message_type_to_str`
- `src/ralphlib/types.py:48` - `ralpher_event_type_to_str`

### S3: TYPE_CHECKING block placement

- `src/ralphlib/printer.py:12` - the `TYPE_CHECKING` block follows the module-level consoles; elsewhere it follows the imports

### S4: Project-specific rules (AGENTS.md coding standards)

Unexpected exceptions not propagated:

- `src/ralphlib/giter.py:43` - `contextlib.suppress(BaseException)` (also A19)
- `src/ralphlib/looper.py:142` - `except Exception` (also A19)

Obvious comments and commented-out code:

- `src/ralphlib/settings.py:33`, `:35`, `:39`
- `src/ralphlib/giter.py:170`
- `src/ralphlib/hooks.py:44`, `:63`, `:66`, `:69`, `:75`, `:79`
- `src/ralphlib/iteration.py:183`, `:494`, `:515`, `:534`, `:950`; commented-out code at `:477`
- `src/ralphlib/looper.py:355`
- `src/tests/test_giter.py:46`, `:88`, `:90`, `:102`, `:105`, `:126`
- `src/tests/test_iteration.py:250`, `:527`, `:645`, `:891`, `:930` - section banners naming task numbers from a task list

Lists not in alphabetical order:

- `src/ralphlib/iteration.py:681` - the `skip` list (`hook_started` before `hook_response`)
- `src/ralphlib/iteration.py:967` - `['message_start', 'message_stop', 'message_delta']`
- `src/ralphlib/iteration.py:428` - `[CONTENT_START, CONTENT_DELTA]`
- `src/ralphlib/iteration.py:462` - `Popen` keyword dict
- `src/ralphlib/iteration.py:830` - the `llm_task_progress` event context
- `src/ralphlib/looper.py:100`, `:240` - `new_state` dicts
- `src/ralphlib/looper.py:258`, `:270` - `ERROR` and `END` event contexts
- `src/ralphlib/verifier.py:18` - `READ_ERRORS`
- `src/tests/test_iteration.py:158`, `:530` - parametrize lists

Other:

- `src/tests/test_iteration.py:1086` - `.format()` instead of an f-string
- `src/tests/test_looper.py:100` - `LoopRun` is a plain class that only assigns fields; a dataclass
- `src/tests/test_shlex.py:1`, `src/tests/test_process_termination.py:1` - test modules that mirror no source module
- `src/tests/test_verifier.py:224` - a test of `iteration.make_context` in the verifier tests
- `src/tests/test_giter.py:305` - `redact_url` has only parametrised examples (also T2)

### P1: O(n^2) on real-size inputs

No hits.

### P2: Blocking I/O in hot paths

- `src/ralphlib/iteration.py:827` - each `<task>` block calls `hooks.event` on the stdout reader thread, so hook context building and each hook's `Popen` (`hooks.py:226`) block the thread that drains the agent's pipe
- `src/ralphlib/iteration.py:395` - `write_progress_eol` flushes the progress log for every completed line while holding `context.gil`
- `src/ralphlib/iteration.py:332` - every terminal write runs under `context.gil`, shared by both reader threads and the poll loop

### P3: Repeated expensive computation per request

- `src/ralphlib/hooks.py:202` - every event builds a new `SandboxedEnvironment` and compiles each hook template (also `:218`, `:158`, `:168`)
- `src/ralphlib/hooks.py:112` - `make_context` recomputes per event: `tzlocal.get_localzone()`, resolved paths, `ralpher_root().resolve()`, `is_file()` on the icon and sound
- `src/ralphlib/hooks.py:186` - `last_commit_summary` opens a `git.Repo` per event (also A14)
- `src/ralphlib/iteration.py:867` - every poll re-reads and re-parses the whole tasks file, changed or not
- `src/ralphlib/verifier.py:95` - the uncached worktree miss (also A14)
- `src/ralphlib/state.py:98` - each `add_to_state` locks, loads and rewrites the whole state file, several times per iteration

### Sec1: Secrets in source

No hits. Every secret-shaped match is a placeholder (`giter.py:138` docstring, `test_giter.py:313`, `:339`, `:340`) or in ignored run logs that echo those test values.

### Sec2: Input validation at system boundaries

- `src/ralphlib/settings.py:53` - settings JSON is merged with `dict.update` unchecked: a top-level value that is not an object raises an uncaught `TypeError`/`ValueError`, and a `theme` that is not an object crashes at `printer.py:50`
- `src/ralphlib/hooks.py:76` - a hook list written as a string (`"end": "notify"`) is iterated one character at a time, each character run as a command
- `src/ralphlib/hooks.py:70` - `hook_templates` is tested for truthiness, so the string `"false"` turns templating on
- `src/ralphlib/options.py:141` - `shlex.split(self.args)` raises `ValueError` on an unbalanced quote; uncaught, it ends in a traceback
- `src/ralphlib/options.py:26` - `--iterations` has no lower bound; `0` or a negative number runs nothing and exits 0 with "completed all iterations"

### Sec3: Command injection

- `src/ralphlib/templater.py:85` - the prompt file is rendered with a plain `jinja2.Template`, not the sandbox the hooks use, so template code in a prompt file runs in ralpher's process. The docs state a trust model for `.ralpher/settings.json` only
- `docs/guide/hooks.md:45` - the guide points to `sh -c '...'` for pipes and redirection without warning that a value spliced into that string (some come from the agent: `task_title`, `prompt`) becomes shell code

### Sec4: Path traversal

No hits. `logger.py:74` rejects absolute and `..` state paths; `rrq.sh:34` and `rcl.sh:34` reject `/` and `..`.

### Sec5: PII in logs

- `src/ralphlib/iteration.py:288` - a tool input with no recognised field is written whole to `state.json`, added to the console summary (`:293`) and to the progress log

### T1: Test coverage of branchy logic

- `bin/ralpher.py:9` - `main` (the `--cleanup` exit, the `RalpherError` exit, the exit codes)
- `bin/install-claude.py:82` - `install_claude`
- `bin/install-claude.py:109` - `main`
- `src/ralphlib/giter.py:37` - `last_commit_summary` is always stubbed (`test_hooks.py:283`)
- `src/ralphlib/giter.py:48` - `confirm_git_state`: only the `skip_git_check` return runs

### T2: Property-based tests

- `src/ralphlib/giter.py:137` - `redact_url`
- `src/ralphlib/giter.py:242` - `claude_worktree_base_ref`
- `src/ralphlib/settings.py:31` - `load_settings` / `load_settings_from_file`
- `src/ralphlib/options.py:140` - `__post_init__` and `args_override_warnings`
- `src/ralphlib/iteration.py:182` - `add_worktree_arg`
- `src/ralphlib/iteration.py:698` - `process_user` (the `process_line` property test's payloads almost never have type `user`)
- `src/ralphlib/iteration.py:742` - `process_assistant` (the same)
- `src/ralphlib/iteration.py:887` - `get_run_in_background`
- `src/ralphlib/iteration.py:936` - `process_result`
- `src/ralphlib/verifier.py:130` - `check_stop`

### T3: Integration vs unit balance

- `src/ralphlib/looper.py:27` - `loop` has no end-to-end test: every loop test stubs `iteration.run` and `hooks.event`. `iteration.run` itself has one (`test_iteration.py:1348`, with the fake agent)

### D1: Declared in pyproject

No hits.

### D2: Unused declarations

No hits. `pytest-icdiff`, `pytest-instafail` and `pytest-randomly` register `pytest11` entry points and nothing disables them; `mkdocs-material` registers the `material` theme that `mkdocs.yml:6` names; `ruff` and `mkdocs` are run as commands.

### D3: Lockfile coherence

No hits. `uv lock --check` exits 0.

### Doc1: AGENTS.md project structure

- `AGENTS.md:40-58` - `src/tests/test_install_claude.py` is missing from the tests list
- `AGENTS.md:67-75` - the top-level `README.md`, `AGENTS.md`, `CLAUDE.md`, `pyproject.toml`, `uv.lock`, `setup.cfg` and the `.github/` directory are not in the tree
- `AGENTS.md:68` - `claude/` is shown holding `rrq.md`; the file is at `claude/commands/rrq.md`

### Doc2: AGENTS.md tools and libraries

- `AGENTS.md:86-106` - shellcheck runs as a pre-commit hook but is not listed
- `AGENTS.md:86-106` - the shared repository's `no-project-names` hook is not named (the auditme hooks are, under Gates)

### Doc3: README.md and AGENTS.md consistent

No hits.

### Doc4: Specs match implementation

- `agents/specs/verified-stop/spec.md:170` - `READ_ERRORS` is described as `OSError` and `UnicodeDecodeError`; `verifier.py:18` also has `TasksFileError`, `ValueError` and `git.GitCommandError`
- `agents/specs/verified-stop/spec.md:34-83` - the API section omits `agent_task_file`, `read_tasks`, `parse_worktrees`, `READ_ERRORS` and `options.worktree_task_path`
- `agents/specs/auditme-adoption/spec.md:101` - "catch `git.GitCommandError` only" around the fetch; `giter.py:159` catches `(git.GitCommandError, OSError, UnicodeDecodeError)`
- `agents/specs/auditme-adoption/spec.md:146-147` - a failed fetch "still returns `False`"; `giter.py:164` returns `None` and the user is asked
- `agents/specs/auditme-adoption/spec.md:101` - the `except ValueError:` row for `int(...)` in `hooks.py` is stale since `task_file_number` is kept as written
- `agents/specs/auditme-adoption/spec.md:104` - an `accept[filesystem-envelope-gap]` marker at `verifier.py:129` that does not exist

### Doc5: User docs match implementation

- `docs/reference/variables.md:17` - a `--vars` key "replaces a built-in of the same name"; `templater.py:51` rejects such a key, and `docs/guide/prompts.md:45-48` says so
- `docs/guide/worktrees.md:37` - `TASKS.md` is said to give worktree `tasks`; `looper.py:72` makes the path absolute first, so `task_file_slug` gives `<repo-dir>-tasks`. `--cleanup` skips that step and gives `tasks`, so `worktrees.md:97` ("prints the same commands") is false for a one-part `--task-file`
- `docs/guide/worktrees.md:16-17` - a failed fetch is "not treated as unpushed"; ralpher asks "cannot tell ... Continue?" with default no and exits on no (`giter.py:104-119`)
- `docs/reference/exit-statuses.md:12` - status 1 after a check "you answered 'no' to"; the divergence check exits on **yes** (`giter.py:210-213`)
- `docs/reference/exit-statuses.md:3-12` - no row for expected errors before the loop (`Error: ...` from `bin/ralpher.py:17-19`); a settings error is raised in `parse_options`, outside that `try`, and exits 1 with a traceback
- `docs/reference/scripts.md:4-5` - only `ralpherun.sh` and `rrq.sh` are said to need `RALPHER_PATH`; `rcl.sh` needs it too (`rcl.sh:26-29`)

## Spec review

- `agents/specs/verified-stop/spec.md` - 233 lines and nine top-level sections, over the specdev guideline of about 200 lines and eight sections
- `agents/specs/verified-stop/spec.md:34-83` - the API section does not describe the public surface (see Doc4)
- `agents/specs/auditme-adoption/spec.md:107-128` - steps 1 and 3 point to the shared `project-setup` skill's adopt mode and CI template in another repository without restating them

## Phase B findings (consolidated)

### Finding 1: A state-lock timeout ends the run in a raw traceback

- **Category:** A
- **Question:** A1, A3
- **Severity:** medium
- **Location:** `src/ralphlib/state.py:93`; callers `looper.py:107`, `:132`, `:171`, `:252`, `:301`; `bin/ralpher.py:17`
- **Description:** after tenacity's last attempt, `filelock.Timeout` leaves `add_to_state` untranslated. No caller catches it, and `bin/ralpher.py` catches only `RalpherError`, so a busy state lock ends ralpher with a Python traceback and no `error` or `end` hook.
- **Recommendation:** translate the final `Timeout` to `StateFileError` in `add_to_state` (tenacity's `reraise=True` keeps the retry), and add a test that a held lock surfaces as `StateFileError`.

### Finding 2: A bad settings file or `--args` value ends in a raw traceback

- **Category:** Sec, Doc
- **Question:** Sec2, Doc5
- **Severity:** medium
- **Location:** `bin/ralpher.py:10`, `src/ralphlib/options.py:141`, `src/ralphlib/settings.py:53`
- **Description:** `parse_options` runs outside `main`'s `try`, so a `SettingsError` (invalid JSON) prints a traceback rather than `Error: ...`. `shlex.split` on an unbalanced quote in `--args` raises `ValueError`, and a settings file whose top level is not an object raises `TypeError`/`ValueError` from `dict.update`; neither is translated.
- **Recommendation:** move `parse_options` inside the `try`; raise `SettingsError` for a top level that is not an object and an `InvalidArgsError` (or similar) for `shlex` failures. Add the expected-error row to `docs/reference/exit-statuses.md`.

### Finding 3: Hook settings of the wrong shape run the wrong commands

- **Category:** Sec
- **Question:** Sec2
- **Severity:** medium
- **Location:** `src/ralphlib/hooks.py:76`, `:70`; `src/ralphlib/printer.py:50`
- **Description:** a hook entry written as a string is iterated one character at a time and each character run as a command; `hook_templates: "false"` turns templating on; a `theme` that is not an object crashes later.
- **Recommendation:** validate the shapes when settings load (`hooks` an object of lists of strings, `hook_templates` a bool, `theme` an object) and raise `SettingsError` naming the key and file.

### Finding 4: The user docs contradict the code

- **Category:** Doc
- **Question:** Doc5
- **Severity:** medium
- **Location:** `docs/reference/variables.md:17`; `docs/guide/worktrees.md:16-17`, `:37`, `:97`; `docs/reference/exit-statuses.md:3-12`; `docs/reference/scripts.md:4-5`
- **Description:** see the Doc5 list: a `--vars` key does not replace a built-in, the worktree name for a one-part `--task-file` differs between a run and `--cleanup`, a failed fetch asks a question the docs do not mention, the divergence exit is on yes, expected errors have no row, and `rcl.sh` needs `RALPHER_PATH`.
- **Recommendation:** correct each page. For the worktree name, make `--cleanup` resolve `--task-file` the way `loop` does (so both print the same name) and fix the table row, with a test that the two agree.

### Finding 5: Untranslated I/O errors

- **Category:** A
- **Question:** A1, A2
- **Severity:** medium
- **Location:** `src/ralphlib/giter.py:73`, `:132`, `:152`, `:158`, `:172`; `src/ralphlib/iteration.py:381-420`, `:661`; `src/ralphlib/state.py:97`; `bin/install-claude.py`
- **Description:** `git.GitCommandNotFound` and a missing origin (`AttributeError`) get past the giter handlers; the log-file writes in `iteration.py` let `OSError` escape, including from the reader threads; `Path.cwd()` runs before its envelope.
- **Recommendation:** add `git.GitCommandNotFound` (or `git.CommandError`) and the no-origin case to the giter handlers; wrap the log writes once (a `LogFileError` from one helper); move `Path.cwd()` inside the `try`. `bin/install-claude.py` runs under the system Python and has no domain errors; accept its broad `main` handler with a scoped marker.

### Finding 6: Broad handlers that the coding standard does not allow

- **Category:** A, S
- **Question:** A19, S4
- **Severity:** medium
- **Location:** `src/ralphlib/giter.py:43`, `src/ralphlib/looper.py:142`
- **Description:** `contextlib.suppress(BaseException)` in `last_commit_summary` swallows everything, `KeyboardInterrupt` included. The `except Exception` in `loop` turns any failure in an iteration into an error exit with hooks and state written (the fix for review-2 Finding 1), and also logs expected `RalpherError` failures with a traceback.
- **Recommendation:** narrow `last_commit_summary` to `ValueError` (a repository with no commits) and the git errors. For `loop`, see the decision below.

### Finding 7: Worktree precedence and the unblock prompt

- **Category:** A
- **Question:** A5, A22
- **Severity:** low
- **Location:** `src/ralphlib/iteration.py:184`, `:273`; `src/ralphlib/giter.py:239`; `src/ralphlib/hooks.py:89`
- **Description:** `--worktree` in `--args` wins over `options.worktree`, which five readers still use; `--settings` in `--args` is not read for the base ref; `summary` has two sources for the iteration; `unblock_prompt` names the main checkout's tasks file when the worktree lookup fails.
- **Recommendation:** reject `--worktree`/`-w` and `--settings` in `--args` with an error naming the ralpher option to use instead; drop `summary`'s `iteration` parameter; make `unblock_prompt` say the worktree tasks file could not be found.

### Finding 8: Repeated work per hook event and per poll

- **Category:** A, P
- **Question:** A14, A21, P2, P3
- **Severity:** low
- **Location:** `src/ralphlib/verifier.py:93-106`; `src/ralphlib/giter.py:38`; `src/ralphlib/hooks.py:112`, `:121`, `:186`, `:202`; `src/ralphlib/iteration.py:332`, `:395`, `:827`, `:867`; `src/ralphlib/state.py:98`
- **Description:** each hook event opens a `git.Repo`, recompiles templates and recomputes values fixed for the run; hooks run on the stdout reader thread; each poll re-reads the tasks file and, until the worktree exists, runs `git worktree list` with an unlocked cache.
- **Recommendation:** compute the run-fixed hook context once per run, cache compiled templates, re-read the tasks file only when its mtime or size changes, and guard the worktree cache with a lock.

### Finding 9: The prompt file is rendered outside the sandbox

- **Category:** Sec
- **Question:** Sec3
- **Severity:** medium
- **Location:** `src/ralphlib/templater.py:85`; `docs/guide/hooks.md:45`
- **Description:** hooks render in a `SandboxedEnvironment`, but the prompt file uses a plain `jinja2.Template`, so a prompt taken from an untrusted repository runs template code in ralpher. The hooks guide recommends `sh -c` without warning that spliced values become shell code.
- **Recommendation:** render prompts in the same sandboxed environment (a prompt needs only variable substitution), and add a warning about `sh -c` with agent-supplied values to the hooks guide.

### Finding 10: Small input checks

- **Category:** Sec, Doc
- **Question:** Sec2, Sec5
- **Severity:** low
- **Location:** `src/ralphlib/options.py:26`; `src/ralphlib/iteration.py:288`
- **Description:** `--iterations 0` exits 0 with "completed all iterations"; an unrecognised tool input is written whole to the state file and the console summary.
- **Recommendation:** require `--iterations` of at least 1; record the tool name and input size, not the raw input.

### Finding 11: Raises sections omit `GitError`

- **Category:** A
- **Question:** A4
- **Severity:** low
- **Location:** `src/ralphlib/hooks.py:109`, `src/ralphlib/iteration.py:459`, `src/ralphlib/verifier.py:113`
- **Description:** `GitError` reaches each caller and is not declared.
- **Recommendation:** add it to each `Raises:` section.

### Finding 12: Late mutation, pure-named I/O and duplicated event contexts

- **Category:** A
- **Question:** A8, A9, A15
- **Severity:** low
- **Location:** the A8, A9 and A15 lists above
- **Description:** `RalpherOptions` carries run-time state (`iteration_count`, the resolved `cwd`/`task_file`, `settings`, `worktree_task_path`) besides the `current_iteration` kept by decision; `TaskStatus` and `IterationContext` are mutated after construction; `get_*`/`is_*` git helpers do I/O; the `ERROR`/`END` contexts and the iteration-end fields are built twice.
- **Recommendation:** resolve `cwd` and `task_file` before constructing options (in `parse_options`); build `TaskStatus` with its status; rename the git readers (`read_origin`, `read_current_branch`, ...); build the end-of-run context in one helper.

### Finding 13: Test gaps

- **Category:** T
- **Question:** T1, T2, T3
- **Severity:** low
- **Location:** the T1, T2 and T3 lists above
- **Description:** `bin/ralpher.py` `main`, `install_claude`, `last_commit_summary` and most of `confirm_git_state` are untested; `loop` has no end-to-end test with a real iteration; ten functions with well-defined domains have only examples.
- **Recommendation:** add a `loop` end-to-end test with the fake agent, tests for `bin/ralpher.py` exit paths and `confirm_git_state` (with the prompt patched), and property tests starting with `redact_url`, `check_stop` and `add_worktree_arg`.

### Finding 14: AGENTS.md drift

- **Category:** Doc
- **Question:** Doc1, Doc2
- **Severity:** low
- **Location:** `AGENTS.md:40-106`
- **Description:** the tree omits `test_install_claude.py`, the top-level project files and `.github/`, and shows `claude/rrq.md` for `claude/commands/rrq.md`; the tools list omits shellcheck and the `no-project-names` hook.
- **Recommendation:** update both sections.

### Finding 15: Spec drift

- **Category:** Doc
- **Question:** Doc4, spec review
- **Severity:** low
- **Location:** `agents/specs/verified-stop/spec.md`, `agents/specs/auditme-adoption/spec.md`
- **Description:** see the Doc4 and spec review lists.
- **Recommendation:** bring the verified-stop API and `READ_ERRORS` up to date and trim it under the size guideline; correct the auditme-adoption rows that the code has moved past.

### Finding 16: Standards

- **Category:** S
- **Question:** S2, S3, S4
- **Severity:** low
- **Location:** the S2, S3 and S4 lists above
- **Description:** lower_snake module constants, one misplaced `TYPE_CHECKING` block, obvious comments and commented-out code, unsorted literals, and test modules that do not mirror a source module.
- **Recommendation:** rename the constants to UPPER_SNAKE, move the block, delete the comments, sort the literals (keeping meaningful orders with an accept marker), and fold `test_shlex.py` into `test_hooks.py` and `test_process_termination.py` into `test_iteration.py`.

## Decisions

### Decision 1: what happens to an exception inside an iteration

- **What is being decided:** whether `loop` keeps its `except Exception` around `iteration.run` (`src/ralphlib/looper.py:142`).
- **Background:** review-2 (2026-11-02) found that an exception during an iteration exited 0 as "completed all iterations". The review-2 task list fixed it by setting the error state and exit reason in that handler, so the run now ends with exit status 1, the `error` and `end` hooks fire and the state file records the reason. The auditme no-winner ruling (A19) says a broad handler that lets the run carry on should be removed or narrowed, unless the user decides it stays, in which case it is accepted with a scoped marker giving the reason.
- **What it affects:** `src/ralphlib/looper.py`, `test_looper.py:200`, `docs/reference/exit-statuses.md` (the "exception inside ralpher" row).
- **Options:**
  - **Keep it and accept it (recommended):** add `# auditme: accept[...]` naming this decision, and narrow nothing. Every failure in an iteration still ends the run cleanly with hooks and state. Expected `RalpherError` failures keep their traceback in the log.
  - **Narrow it to `RalpherError`:** expected failures end the run as now; an unexpected exception propagates with a traceback, the `error`/`end` hooks do not fire and the state file has no end record. The docs row changes.
  - **Remove it:** every failure propagates; `bin/ralpher.py` prints `Error: ...` for a `RalpherError` and a traceback otherwise; no `error`/`end` hooks after a failed iteration.

## Files reviewed (Phase B)

- `src/ralphlib/__init__.py`, `exceptions.py`, `giter.py`, `hooks.py`, `iteration.py`, `logger.py`, `looper.py`, `options.py`, `printer.py`, `settings.py`, `signals.py`, `state.py`, `templater.py`, `types.py`, `verifier.py` - A1-A25, S1-S4, P1-P3, Sec1-Sec5, T1-T3
- `bin/ralpher.py`, `bin/install-claude.py` - the same questions
- `bin/*.sh` - Sec1-Sec3, Doc5
- `src/tests/**/*.py` - S1 (count), S2, S3, S4, and the T questions as the source of tests
- `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `mkdocs.yml`, `.github/workflows/*.yml` - D1-D3, Doc2
- `AGENTS.md`, `README.md`, `docs/**/*.md`, `agents/specs/*/spec.md` - Doc1-Doc5 and the spec review

## Prior findings re-verified

From `summary.md`'s unresolved list:

- Plugin dependencies flagged by D2 (review-2 Finding 19) - resolved: the D2 carve-out of 2026-11-02 clears each by its entry point (D2 above).

From `summary.md`'s Recently resolved list, re-checked because this review's per-question hits fall on the same predicates:

- Late dataclass mutation (review-2 Finding 15) - partly resolved: `IterationContext` is now built with its file handles, but every other site in review-2's A8 list is still present (A8 above, Finding 12).
- Pure-named functions with side effects (review-2 Finding 14) - partly resolved: the interactive `check_*` functions were renamed `confirm_*` and `has_unpushed_commits` returns `bool | None`, but the `is_*`/`get_*` sites in review-2's A9 list remain (A9 above, Finding 12).
- Worktree and tasks-file precedence (review-2 Finding 8) - partly resolved: the hooks and the verifier now share `agent_task_file`, but the `--args` precedence and the `--settings` base-ref hits remain (A5 above, Finding 7).
- Repeated git subprocesses per poll and per event (review-2 Finding 9) - partly resolved: the worktree path is cached once found, but not on a miss, and each hook event still opens a repository (Finding 8).
- Obvious comments and unsorted lists (review-2 Finding 17) - partly resolved: the review-2 sites were fixed, and new ones are listed under S4.

No task in `agents/tasks/audit-reviews/` is incomplete.

## Recommendations

1. Medium: Findings 1, 2 and 3 (how ralpher fails on a busy lock and bad settings), Finding 4 (user docs), Finding 5 (untranslated I/O), Finding 6 (broad handlers, with Decision 1) and Finding 9 (prompt sandbox).
2. Low: Findings 7, 8 and 10 to 16.

## Answers

Answered 2026-11-02 on the review page (https://claude.ai/artifact/37jqLburDyf1BbNKvQ5ogG), no comments:

- **Findings 1-16:** approved.
- **Decision 1 (the `except Exception` in `loop`):** keep it and accept it with a scoped marker naming this decision. Every failure in an iteration still ends the run cleanly, with the `error` and `end` hooks and the state record.
