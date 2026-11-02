# Audit Review 2

**Date:** 2026-11-02
**Scope:** full (`agents/specs/`, `src/`, `bin/`, `docs/`, `AGENTS.md`, `README.md`)
**Script output:** /tmp/audit-ralpher.jsonl (12 hits, 12 accepted, 0 unaccepted)
**Convergence note:** first audit run with the scripted checker; review-1 (2026-03-30) predates it, so there is no earlier script baseline. Checker digest `ccecce19de80b8adc9b53eb38a4dfa3d3128047a1ae3affb940cf9f3d6120c2b`.

## Summary

The mechanical sweep is clean: every hit (`except-interpolation`, `mutable-module-level-exported`, `non-alphabetical-literal`, `stdlib-logging`) carries a scoped accept marker. Phase B ran every question in every category with per-question fan-out. It finds two high-severity defects:

- an exception during an iteration ends the loop with exit status 0 and the reason "completed all iterations";
- an unreadable state file is silently replaced by a new one.

A re-verified finding from review-1 is now a third: a state-lock timeout is swallowed, so the retry around it never runs. The rest are medium and low findings: error handling, documentation drift and test gaps.

## Mechanical findings (from checks/audit.py)

None unaccepted. The accepted hits, dismissed by their markers:

| Rule | Accepted |
|------|----------|
| `except-interpolation` | 6 |
| `mutable-module-level-exported` | 3 |
| `non-alphabetical-literal` | 2 |
| `stdlib-logging` | 1 |

## Phase B per-question results

Every question covered the 17 non-test files under `src/ralphlib/` and `bin/`. S1, S2, S3 and S4 also covered `src/tests/`. Sec1 and Sec3 also covered `bin/*.sh`.

### A1: External call envelope

- `src/ralphlib/giter.py:77` - `git.Repo(...)` catches only `InvalidGitRepositoryError`; `NoSuchPathError` and other `OSError` escape
- `src/ralphlib/giter.py:117` - `repo.is_dirty()` (git subprocess), no envelope
- `src/ralphlib/giter.py:145` - `repo.iter_commits()` (`git rev-list`), no envelope
- `src/ralphlib/giter.py:150` - `head.is_detached`, `active_branch` and `tracking_branch()` read refs with no envelope
- `src/ralphlib/giter.py:197` - `head.is_detached` and `active_branch.name`, no envelope
- `src/ralphlib/hooks.py:104` - `tzlocal.get_localzone()`, no envelope
- `src/ralphlib/verifier.py:99` - `repo.git.worktree('list', ...)` lets `GitCommandError` escape. That is documented, but the caller at `hooks.py:44` does not catch it, including on the stdout reader thread
- `src/ralphlib/verifier.py:121` - `read_text()` untranslated. Callers catch `READ_ERRORS`
- `src/ralphlib/logger.py:16` - `logdir.mkdir`, no envelope
- `src/ralphlib/looper.py:32` - `os.chdir(options.cwd)`, no envelope
- `src/ralphlib/looper.py:43` - `open(options.prompt)` and `read()`, no envelope
- `src/ralphlib/looper.py:63` - `open(task_path)` and `read()`, no envelope
- `src/ralphlib/printer.py:23` - `path.open('a')` and `write`, no envelope
- `src/ralphlib/settings.py:46` - `path.open()` and `json.load`, no envelope
- `src/ralphlib/state.py:46` - `path.open('w')` and `json.dump`. `add_to_state` re-raises untranslated
- `src/ralphlib/state.py:89` - `lock.acquire` catches only `Timeout`. `OSError` from creating the lock file escapes
- `src/ralphlib/iteration.py:211` - the log-file opens (211, 214, 217 and 220) bare-`raise` untranslated
- `src/ralphlib/iteration.py:443` - `subprocess.Popen` has no envelope. `run` re-raises untranslated
- `src/ralphlib/iteration.py:351` - log-fd `write`/`flush` calls (351, 358, 365, 371, 377, 384 and 390) have no envelope, some of them on reader threads
- `src/ralphlib/iteration.py:539` - `pipe.readline` (and `:566`) has no envelope. `OSError` kills the reader thread
- `bin/install-claude.py:17` - filesystem calls (lines 17-33, 39-40, 64 and 87) reach only the catch-all in `main`

### A2: Except tuple coverage

- `src/ralphlib/giter.py:76` - `(InvalidGitRepositoryError)` lacks `OSError`
- `src/ralphlib/giter.py:125` - `(ValueError)` around `repo.remotes.origin` lacks `OSError`
- `src/ralphlib/giter.py:131` - `(GitCommandError)` around `origin.fetch()` lacks `OSError` and `UnicodeDecodeError` (GitPython decodes `FETCH_HEAD`)
- `src/ralphlib/giter.py:186` - `(AttributeError, TypeError)` around the ref read lacks `OSError`
- `src/ralphlib/state.py:88` - `(filelock.Timeout)` around the lock, `load_state` and `save_state` lacks `OSError`

### A3: Domain-error layering

- `src/ralphlib/logger.py:21` - `raise ValueError('logdir is not set')`
- `src/ralphlib/verifier.py:115` - `raise LookupError(...)`

### A4: Docstring `Raises` accuracy

No hits. No docstring has a `Raises:` section. `verifier.py:88`, `:108` and `:120` give raised types in prose.

### A5: Two sources of truth

- `src/ralphlib/iteration.py:187` - `add_worktree_arg` lets a `--worktree`/`-w` in `--args` win silently over `options.worktree`, which the verifier, cleanup, git checks and templater still read
- `src/ralphlib/hooks.py:44` - `event` uses the worktree tasks file whenever one exists. `verifier.agent_task_file` (`verifier.py:111`) uses it only when `options.worktree` is set
- `src/ralphlib/giter.py:204` - `worktree_base_ref` ignores the `--settings` JSON passed in `--args` and reads Claude's settings files instead

### A6: Stage method dual-path

No hits. Three classes inspected.

### A7: Constructor purity

No hits. `signals.py:51` is the only explicit `__init__`; it registers signal handlers, which is outside the predicate.

### A8: Late dataclass mutation

- `src/ralphlib/iteration.py:210` - `make_context` sets eight log-file fields after constructing `IterationContext` (lines 210-220)
- `src/ralphlib/iteration.py:440` - `process` sets `context.in_progress_tasks`
- `src/ralphlib/verifier.py:67` - `parse_tasks` sets `current.status` after constructing `TaskStatus`
- `src/ralphlib/settings.py:30` - `load_settings` sets `options.settings` (and updates it at `:48`)
- `src/ralphlib/looper.py:31` - `options.cwd` reassigned
- `src/ralphlib/looper.py:67` - `options.task_file` reassigned
- `src/ralphlib/looper.py:108` - `options.current_iteration` set every iteration
- `src/ralphlib/looper.py:145` - `options.iteration_count` set every iteration

### A9: Pure-named function side effects

- `src/ralphlib/giter.py:50` - `check_git` prompts on stdin and calls `sys.exit`
- `src/ralphlib/giter.py:82` - `is_git_repo` opens a repository on disk
- `src/ralphlib/giter.py:86` - `check_repo_clean` runs git, fetches from the network, prompts and exits
- `src/ralphlib/giter.py:111` - `is_working_tree_clean` runs a git subprocess
- `src/ralphlib/giter.py:120` - `has_unpushed_commits` fetches from the network, runs `rev-list` and prints
- `src/ralphlib/giter.py:149` - `get_upstream_branch` reads refs and prints
- `src/ralphlib/giter.py:162` - `check_divergence` reads settings files, prompts and exits
- `src/ralphlib/giter.py:184` - `get_origin` reads refs
- `src/ralphlib/giter.py:196` - `get_current_branch` reads `HEAD`
- `src/ralphlib/verifier.py:124` - `check_stop` reads the tasks file and runs `git worktree list`
- `src/ralphlib/options.py:141` - `parse_options` reads up to three settings files
- `bin/install-claude.py:61` - `find_dangling_symlinks` walks the filesystem and prints

### A10: Predicate semantics

- `src/ralphlib/giter.py:120` - `has_unpushed_commits` returns `False` for "no origin", "fetch failed", "detached HEAD" and "no upstream", so "cannot tell" reads as "nothing to push"

### A11: Exhaustion via assert_never

No hits. There are no if/elif chains over an enum or `Literal`.

### A12: assert misuse

No hits. There is no `assert` outside tests.

### A13: Same value to multiple structural slots

- `src/ralphlib/hooks.py:218` - `Popen(stdout=DEVNULL, stderr=DEVNULL)`, no docstring
- `src/ralphlib/iteration.py:429` - `Popen` kwargs give `PIPE` to both `stdout` and `stderr`, no docstring

### A14: Repeated computation per request

- `src/ralphlib/verifier.py:83` - `worktree_task_file` runs `git worktree list` on every hook event, every 3 s poll and in `check_stop`
- `src/ralphlib/giter.py:39` - `last_commit_summary` is recomputed in every `hooks.make_context`
- `src/ralphlib/options.py:134` - `passed_worktree_base_ref` re-splits `args` at `giter.py:87`, at `:163` and once per iteration at `iteration.py:178`
- `src/ralphlib/logger.py:65` - `state_file` and `state_lock_file` (`:75`) are recomputed three times per `add_to_state`
- `src/ralphlib/templater.py:20` - `task_file_slug` is recomputed per iteration and per `worktree_task_file` call

### A15: Duplicate constructor / serialisation logic

- `src/ralphlib/printer.py:8`, `src/ralphlib/iteration.py:74` - `Console(highlight=False)` is built twice
- `src/ralphlib/giter.py:20`, `src/ralphlib/state.py:17`, `src/ralphlib/iteration.py:75` - `Console(stderr=True, highlight=False)` is built three times
- `src/ralphlib/verifier.py:138`, `:142` - `StopCheck` is built in two places. `unverified()` covers only one

### A16: CLI entry envelope

No hits. There is no `cli/` package. `bin/ralpher.py:8` and `looper.loop` contain no `raise`.

### A17: Public-surface drift

No hits. Both `__init__.py` files are empty, and every consumer imports public module paths.

### A18: Hot-path setup

No hits. No callback methods.

### A19: Wrong logger level for broad-except

Each of these is a broad handler that logs and degrades gracefully. Under the no-winner ruling, remove the handler or narrow it:

- `src/ralphlib/hooks.py:222` - `run_hook` logs and returns after any hook failure
- `src/ralphlib/iteration.py:233` - `flush_and_close_fd` swallows the error
- `src/ralphlib/iteration.py:609` - `process_line` returns `(ERROR, line)` and reading continues
- `src/ralphlib/iteration.py:769` - `process_task_progress` falls through to `(NONE, line)`
- `src/ralphlib/looper.py:134` - `except Exception` around `iteration.run` breaks out of the loop. See the high-severity finding below
- `src/ralphlib/state.py:32` - `load_state` returns `{}`. See the high-severity finding below

### A20: Mutable module-level singleton

No hits. `hooks.processed_hooks`, `hooks.seen_task_ids` and `logger.log_file_cache` are accepted by scoped markers. The rest are wrapped.

### A21: Lazy init race

No hits.

### A22: Fall-through after partial handling

- `src/ralphlib/state.py:28` - a read or parse failure inside `if path.exists(): return json.load(fp)` falls through to the `return {}` meant for a missing file

### A23: Discarded multi-return

No hits.

### A24: Identity of subprocess / shell-out calls

- `src/ralphlib/hooks.py:44` - `git worktree list` on every hook event, before the duplicate check, even without `--worktree`
- `src/ralphlib/iteration.py:817` - `announce_started_tasks` re-runs `git worktree list` on every 3 s poll

### A25: Shallow immutable wrapper

No hits.

### S1: Type annotations on every signature

- `bin/install-claude.py:15` - `symlink_file(options)` unannotated
- `bin/install-claude.py:36` - `symlink_dir(options)` unannotated
- `bin/install-claude.py:61` - `find_dangling_symlinks(options)` unannotated
- `bin/install-claude.py:82` - `install_claude(options)` unannotated
- `bin/install-claude.py:101` - `parse_args(argv)` unannotated
- `bin/install-claude.py:109` - `main(argv)` unannotated
- Tests (count only): 7 missing parameter annotations and 13 missing return annotations, all in `src/tests/test_process_termination.py`. The other 15 test modules are fully annotated.

### S2: Naming

No hits.

### S3: TYPE_CHECKING block placement

No hits.

### S4: Project-specific rules (AGENTS.md coding standards)

Lists that are not in alphabetical order:

- `src/ralphlib/iteration.py:93` - the `newline_types` frozenset
- `src/ralphlib/iteration.py:627` - the `skip` subtype list: `hook_started` comes before `hook_progress`
- `src/ralphlib/hooks.py:136` - the context dict: `cwd` comes after `cwd_basename` and `cwd_dirname`
- `src/ralphlib/hooks.py:150` - the context dict: `task_file` comes after `task_file_suffix`
- `src/ralphlib/templater.py:31` - the render context dict

Obvious comments:

- `src/ralphlib/looper.py:34`, `:81`, `:88`, `:131` and `:349`. `# hook` repeats at 124, 164 and 247, and `# state json` at 117, 156 and 232
- `src/ralphlib/iteration.py:186`, `:456`, `:477`, `:496`, `:896` and `:902`
- `src/ralphlib/hooks.py:69`, `:72`, `:81` and `:85`
- `src/ralphlib/giter.py:144`
- `src/ralphlib/settings.py:31`, `:33` and `:37`
- `src/tests/test_giter.py:85`, `:87`, `:99` and `:102`

### P1: O(n^2) on real-size inputs

No hits.

### P2: Blocking I/O in hot paths

- `src/ralphlib/hooks.py:44` - a git subprocess on every event, including `LLM_TASK_PROGRESS` on the stdout reader thread
- `src/ralphlib/hooks.py:142` - `giter.last_commit_summary()` opens the repository on the same path
- `src/ralphlib/iteration.py:484` - the poll loop re-discovers the repository, runs `git worktree list` and re-reads and re-parses the tasks file on every tick

### P3: Repeated expensive computation per request

- `src/ralphlib/hooks.py:44` - the git call runs before the duplicate-event check
- `src/ralphlib/verifier.py:91` - `worktree_task_file` rebuilds the repository and re-runs git on every call

### Sec1: Secrets in source

No hits.

### Sec2: Input validation at system boundaries

- `src/ralphlib/templater.py:56` - `--vars` keys can silently override built-in template variables (`iteration`, `task_file`, ...)
- `bin/rrq.sh:31` - `TASKS-SPEC` and `TASKS-INDEX` are not checked before they are put into paths (`/`, `..`)
- `bin/rcl.sh:31` - the same

### Sec3: Command injection

- `src/ralphlib/settings.py:34` - `<cwd>/.ralpher/settings.json` in the target repository can define `hooks`, which run as commands (`hooks.py:216`). Running ralpher in an untrusted clone runs that repository's commands without a prompt

### Sec4: Path traversal

- `src/ralphlib/logger.py:68` - `--state` is joined to `logdir` with no containment check
- `src/ralphlib/logger.py:78` - the same for the lock file

### Sec5: PII in logs

- `src/ralphlib/iteration.py:723` - the raw agent JSON line is logged at WARNING
- `src/ralphlib/iteration.py:739` - the same
- `src/ralphlib/iteration.py:747` - the same
- `src/ralphlib/giter.py:135` - `origin.url` is logged at WARNING, and it can embed credentials

### T1: Test coverage of branchy logic

- `src/ralphlib/giter.py:24` - `YNConfirm.make_prompt`
- `src/ralphlib/giter.py:50` - `check_git`: only the skip path is tested
- `src/ralphlib/giter.py:184` - `get_origin`: the no-origin/HEAD branch is untested
- `src/ralphlib/giter.py:196` - `get_current_branch`: the detached-HEAD branch is untested
- `src/ralphlib/iteration.py:133` - `add_unknown_tool`
- `src/ralphlib/iteration.py:164` - `run`
- `src/ralphlib/iteration.py:197` - `make_context`
- `src/ralphlib/iteration.py:228` - `flush_and_close_fd`
- `src/ralphlib/iteration.py:237` - `unmake_context`
- `src/ralphlib/iteration.py:248` - `summary`
- `src/ralphlib/iteration.py:290` - `print_progress_lines`
- `src/ralphlib/iteration.py:354` - `write_progress_lines`
- `src/ralphlib/iteration.py:381` - `write_stdout`
- `src/ralphlib/iteration.py:387` - `write_stderr`
- `src/ralphlib/iteration.py:534` - `process_stdout`: the per-line branches never run
- `src/ralphlib/iteration.py:561` - `process_stderr`: the per-line branches never run
- `src/ralphlib/state.py:88` - `add_to_state_work`: the lock-timeout path is untested (from the prior-finding re-check)
- `bin/install-claude.py:15` - `symlink_file`
- `bin/install-claude.py:61` - `find_dangling_symlinks`
- `bin/install-claude.py:82` - `install_claude`
- `bin/install-claude.py:109` - `main`
- `bin/ralpher.py:8` - `main`: the `--cleanup` and error exits

### T2: Property-based tests

Hypothesis covers only `timedelta_to_readable`, `slugify` and `parse_tasks`. No property tests for:

- `src/ralphlib/verifier.py:71` - `parse_worktrees` (no tests at all)
- `src/ralphlib/hooks.py:196` - `render_hook_args`: shlex round-trip of arbitrary values
- `src/ralphlib/iteration.py:575` - `process_line`
- `src/ralphlib/iteration.py:910` - `process_stream_event`
- `src/ralphlib/iteration.py:754` - `process_task_progress`
- `src/ralphlib/iteration.py:854` - `input_field_to_content`
- `src/ralphlib/iteration.py:831` - `indent_lines`
- `src/ralphlib/iteration.py:676` - `is_stop`
- `src/ralphlib/iteration.py:403` - `agent_environment`
- `src/ralphlib/templater.py:20` - `task_file_slug`
- `src/ralphlib/templater.py:30` - `render`
- `src/ralphlib/logger.py:25` - `iteration_to_str`
- `src/ralphlib/logger.py:37` - `log_file`
- `src/ralphlib/state.py:50` - `add_to_state` (the `key1`/`key2` merge)
- `src/ralphlib/looper.py:315` - `cleanup_cmds`

### T3: Integration vs unit balance

- `src/ralphlib/iteration.py:164` - no end-to-end test of `run`: no test drives a child process that emits stream-JSON through `process_line` to the `(complete, error)` result. `looper.loop` passes, because `run_loop` drives it end to end

### D1: Declared in pyproject

No hits.

### D2: Unused declarations

- `pyproject.toml:22` - `pytest-icdiff`
- `pyproject.toml:23` - `pytest-instafail`
- `pyproject.toml:24` - `pytest-randomly`
- `pyproject.toml:29` - `mkdocs-material`

All four are loaded by a host tool: the pytest plugins through pytest's plugin entry points, and the theme by `mkdocs.yml` (`theme: name: material`). The predicate as written flags them. A carve-out has been requested in the skill's `requests.md`, and the D2 finding below explains what that means here.

### D3: Lockfile coherence

No hits. `uv lock --check` is clean.

### Doc1: AGENTS.md project structure

- `AGENTS.md:35` - the tests tree omits `conftest.py` and `test_shlex.py`
- `AGENTS.md:50` - the `bin/` tree omits `install-claude.py` and `rcl.sh`
- `AGENTS.md:58` - says `logs/` holds "Application log output", but nothing writes there. `bin/rrq.sh:38` writes to `ralpher-logs/`, which is not listed
- `AGENTS.md:17` - `agents/`, `claude/`, `img/`, `TODO.md`, `DONE.md` and `NOTES.md` are missing from the tree

### Doc2: AGENTS.md tools and libraries

- `AGENTS.md:73` - says Python 3.14 and links the 3.14.2 docs. `pyproject.toml` requires `>=3.14.5`
- `AGENTS.md:78` - lists Docker, but the repository has no Docker files
- `AGENTS.md:72` - the runtime dependencies `filelock`, `gitpython`, `jinja2`, `orjson`, `rich`, `tenacity` and `tzlocal` are not listed. Nor are the dev tools `pytest-*`, `mkdocs`, `mkdocs-material` and `pre-commit`

### Doc3: README.md and AGENTS.md consistent

- `README.md:3` vs `AGENTS.md:5` - the README describes verified stops, worktree queues and hooks. AGENTS.md "Goals" names none of them

### Doc4: Specs match implementation

- `agents/specs/verified-stop/spec.md:32` - says `README.md` documents the flag. It is now in `docs/guide/tasks.md` and `docs/reference/cli.md`
- `agents/specs/verified-stop/spec.md:167` - says the read errors are caught "in `check_stop` only". `iteration.py:806` catches `READ_ERRORS` too
- `agents/specs/verified-stop/spec.md:165` - says the reason names the path that failed. `verifier.py:133` names `options.task_file`, not the worktree path that was read
- `agents/specs/verified-stop/spec.md:72` - `worktree_task_file` also returns None when there is no repository or no task file
- `agents/specs/auditme-adoption/spec.md:115` - says to pin actions by commit SHA. They are pinned by release tag since `e0d8cb0`, the commit that pinned the CI actions to release tags as the security rule requires
- `agents/specs/auditme-adoption/spec.md:105` - omits the `no-project-names` hook that is in `.pre-commit-config.yaml`
- `agents/specs/auditme-adoption/spec.md:158` - calls the verified-stop spec "stale `proposed`". It now reads `implemented`

### Doc5: User docs match implementation

- `docs/reference/exit-statuses.md:11` - says an invalid `--vars` stops ralpher before the first iteration. `templater.py:58` raises inside iteration 1, after the `start` hook, outside the `try`, with a traceback
- `docs/reference/exit-statuses.md:3` and `docs/guide/stopping.md:39` - no row for an exception during an iteration. See the high-severity finding below
- `docs/guide/stopping.md:35` and `docs/concepts.md:50` - say any `result` with `is_error` is an error. `iteration.py:897` counts it only when `subtype == 'success'`
- `docs/guide/terminal.md:13` - says stderr uses the theme's `error` style. `iteration.py:324` hard-codes `red`
- `docs/reference/variables.md:30` - says `current_iteration` is "the iteration running, or 0". It is never reset, so `end` and `error` hooks see the last iteration
- `docs/reference/variables.md:44` - the `task_file_number` rule differs from `hooks.py:120-130` (text before the first `.`, and `0` becomes empty)
- `docs/reference/scripts.md:3` - `ralpherun.sh` needs `RALPHER_PATH` too, and `install-claude.py` does not activate `.venv`
- `docs/install.md:59` - says an existing destination is renamed `.orig`. `install-claude.py:18` unlinks an existing symlink
- `mkdocs build --strict` passes. `agent_process_end` and `--worktree-base-ref` match the code.

## Spec review

- **verified-stop:** every template section is present. Gaps: it is 230 lines with 9 top-level sections, over the specdev size guide; and it points to `README.md` for the documentation (Doc4).
- **auditme-adoption:** gaps: `load_state` and `save_state` (lines 61-62) have no docstrings; line 158 mentions the verified-stop spec without a link; it relies on the `project-setup` skill, the auditme checker and a deploy key in the shared tooling repository without restating what it depends on.

## Phase B findings (consolidated)

### Finding 1: An exception during an iteration exits 0 as "completed all iterations"

- **Category:** A
- **Question:** A19
- **Severity:** high
- **Location:** `src/ralphlib/looper.py:134`
- **Description:** `except Exception` logs and `break`s with `error` still `False` and `exit_reason` still `'completed all iterations'` (lines 100-101). `loop` returns `False` (`:278`), so `bin/ralpher.py` exits 0. The `iteration_end` and `error` hooks do not fire, and queue scripts treat the run as a success.
- **Recommendation:** remove the broad handler, or set `error = True` and an exit reason naming the exception before breaking, and fire the `error` hook. Add a row to `docs/reference/exit-statuses.md`. Add a test that makes `iteration.run` raise.

### Finding 2: An unreadable state file is replaced by an empty one

- **Category:** A
- **Question:** A22, A19
- **Severity:** high
- **Location:** `src/ralphlib/state.py:28`
- **Description:** a JSON or OS error reading an existing state file is logged and falls through to `return {}`. `add_to_state_work` then writes the update over the file, losing every earlier iteration's record.
- **Recommendation:** return `{}` only when the file does not exist. Let a read failure propagate, or translate it to a domain error, so the file is never overwritten.

### Finding 3: Agent errors with a non-`success` subtype are ignored

- **Category:** Doc
- **Question:** Doc5
- **Severity:** medium
- **Location:** `src/ralphlib/iteration.py:897`
- **Description:** a `result` with `is_error: true` counts as an error only when `subtype == 'success'`. An `error_*` subtype (for example the agent hitting its turn limit) does not stop the loop as an error, contrary to `docs/guide/stopping.md:35`.
- **Recommendation:** treat `is_error` as an error whatever the subtype, or document the exact rule. Add a test for each subtype.

### Finding 4: Repository-local settings can run commands without consent

- **Category:** Sec
- **Question:** Sec3
- **Severity:** medium
- **Location:** `src/ralphlib/settings.py:34`
- **Description:** hooks from `<cwd>/.ralpher/settings.json` in the target repository run as commands. Running ralpher in an untrusted clone runs that repository's commands.
- **Recommendation:** decide whether repository-local hooks are a feature. If they are, document the trust model in `docs/reference/settings.md`. If not, take hooks only from the home and `--settings` files, or ask before running hooks from a repository file.

### Finding 5: Invalid `--vars` fails mid-iteration with a traceback

- **Category:** Doc
- **Question:** Doc5, Sec2
- **Severity:** medium
- **Location:** `src/ralphlib/templater.py:58`
- **Description:** the documentation says ralpher stops before the first iteration. In fact `render` raises `InvalidVarFormat` inside iteration 1, outside any handler, after the `start` hook and the first state write. A `--vars` key can also silently override a built-in variable.
- **Recommendation:** validate `--vars` once, before the loop starts, rejecting a bad format and reserved keys, with a clear message and a non-zero exit.

### Finding 6: Untranslated I/O errors (A1, A2, A3)

- **Category:** A
- **Severity:** medium
- **Location:** the A1, A2 and A3 lists above
- **Description:** git, filesystem, lock and subprocess calls let third-party and `OSError` exceptions escape, some of them on reader threads, where they end the thread silently. Two `raise` statements use stdlib types.
- **Recommendation:** add domain errors (`GitError`, `StateError`, `LogError`, ...) to `exceptions.py`, wrap the listed calls, and widen the A2 tuples to include `OSError`. Rename the existing classes to end in `Error`.

### Finding 7: Broad graceful-degradation handlers (A19)

- **Category:** A
- **Severity:** medium
- **Location:** `hooks.py:222`, `iteration.py:233`, `iteration.py:609`, `iteration.py:769`
- **Description:** each catches `Exception`, logs it and carries on.
- **Recommendation:** narrow each handler to the expected exceptions and log those with `warning`, or remove it. Follow the no-winner ruling; do not change the log level.

### Finding 8: Worktree and tasks-file precedence is undocumented (A5)

- **Category:** A
- **Severity:** medium
- **Location:** `iteration.py:187`, `hooks.py:44`, `giter.py:204`
- **Description:** `--args` can override `--worktree` and `--worktree-base-ref` silently, and `hooks.event` chooses the worktree tasks file by a different rule from the verifier.
- **Recommendation:** have one function decide the tasks-file path and the base ref, use it everywhere, and document the precedence.

### Finding 9: Repeated git subprocesses per poll and per event (A14, A24, P2, P3)

- **Category:** P
- **Severity:** medium
- **Location:** `verifier.py:83`, `hooks.py:44`, `hooks.py:142`, `iteration.py:484`, `iteration.py:817`
- **Description:** `git worktree list` and repository discovery run on every 3 s poll and every hook event, including on the stdout reader thread.
- **Recommendation:** resolve the worktree path once per iteration (after the agent has created the worktree) and pass it down. Move the duplicate check in `hooks.event` before the git call.

### Finding 10: No end-to-end test of the iteration runner (T1, T3)

- **Category:** T
- **Severity:** medium
- **Location:** `src/ralphlib/iteration.py:164`
- **Description:** `run`, `make_context`, `unmake_context`, `summary` and the per-line branches of `process_stdout` and `process_stderr` are never exercised.
- **Recommendation:** add a test whose child process prints canned stream-JSON on stdout and text on stderr, and assert the log files, the summary and the `(complete, error)` result.

### Finding 11: Documentation drift (Doc1-Doc5)

- **Category:** Doc
- **Severity:** medium
- **Location:** the Doc1-Doc5 lists above
- **Description:** the AGENTS.md structure tree and tools list, the specs and the user docs differ from the code in the listed places.
- **Recommendation:** update each listed passage. For `current_iteration` and `task_file_number`, decide whether the code or the docs are right.

### Finding 12: Logged agent output and remote URLs (Sec5)

- **Category:** Sec
- **Severity:** low
- **Location:** `iteration.py:723`, `:739`, `:747`; `giter.py:135`
- **Description:** raw agent JSON lines and the origin URL are logged at WARNING.
- **Recommendation:** log the payload type and size at WARNING and the raw line at DEBUG. Strip credentials from the URL before logging it.

### Finding 13: Unchecked paths from user input (Sec2, Sec4)

- **Category:** Sec
- **Severity:** low
- **Location:** `logger.py:68`, `:78`; `bin/rrq.sh:31`; `bin/rcl.sh:31`
- **Description:** the `--state` path and the queue-script arguments are put into paths without checking them.
- **Recommendation:** reject `/` and `..` in those arguments, or resolve the path and check it stays inside `logdir`.

### Finding 14: Pure-named functions with side effects (A9, A10)

- **Category:** A
- **Severity:** low
- **Location:** the A9 and A10 lists above
- **Description:** `check_*`, `is_*`, `get_*` and `find_*` functions prompt, exit, fetch or run git. `has_unpushed_commits` conflates "cannot tell" with "no".
- **Recommendation:** rename the interactive ones (`confirm_git_state`, `confirm_repo_clean`, ...). Make `has_unpushed_commits` return `bool | None`, or raise when it cannot tell.

### Finding 15: Late dataclass mutation (A8)

- **Category:** A
- **Severity:** low
- **Location:** the A8 list above
- **Description:** `IterationContext`, `TaskStatus` and `RalpherOptions` are mutated after construction.
- **Recommendation:** build `IterationContext` with its file handles in a single constructor call. Keep run-time counters such as `current_iteration` out of `RalpherOptions`.

### Finding 16: Duplicated console construction and other A13/A15 hits

- **Category:** A
- **Severity:** low
- **Location:** the A13 and A15 lists above
- **Description:** the rich consoles are built in four modules with the same arguments. `StopCheck` is built in two places. `Popen` gets the same value for both `stdout` and `stderr` with no comment.
- **Recommendation:** move the two consoles to `printer.py`, add a `verified()` helper beside `unverified()`, and add a one-line docstring to the two `Popen` callers.

### Finding 17: Standards (S1, S4)

- **Category:** S
- **Severity:** low
- **Location:** the S1 and S4 lists above
- **Description:** `bin/install-claude.py` has unannotated parameters, five literals are not in alphabetical order, and some comments only restate the code.
- **Recommendation:** annotate the parameters, sort the literals, and delete the obvious comments.

### Finding 18: Property-test gaps (T2) and remaining T1 functions

- **Category:** T
- **Severity:** low
- **Location:** the T1 and T2 lists above
- **Description:** parsers and formatters have only example tests, and `parse_worktrees` and `install-claude.py` have no tests at all.
- **Recommendation:** add hypothesis tests, starting with `render_hook_args` (shlex round-trip), `parse_worktrees` and `process_task_progress`.

### Finding 19: Plugin dependencies flagged by D2

- **Category:** D
- **Severity:** low
- **Location:** `pyproject.toml:22-24`, `:29`
- **Description:** these dependencies are loaded by pytest or mkdocs, not imported.
- **Recommendation:** no code change. They are used, and a carve-out for them has been requested in the skill's `requests.md`. Until it ships, these hits will recur in each audit.

## Files reviewed (Phase B)

- `src/ralphlib/exceptions.py`, `giter.py`, `hooks.py`, `iteration.py`, `logger.py`, `looper.py`, `options.py`, `printer.py`, `settings.py`, `signals.py`, `state.py`, `templater.py`, `types.py`, `verifier.py`, `__init__.py` - questions A1-A25, S1-S4, P1-P3, Sec1-Sec5, T1-T3
- `bin/ralpher.py`, `bin/install-claude.py` - the same questions
- `bin/*.sh` - Sec1, Sec2 and Sec3
- `src/tests/*.py` - S1 (count), S2, S3, S4, and the T questions as the source of tests
- `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `.github/workflows/*.yml` - D1-D3
- `AGENTS.md`, `README.md`, `docs/**/*.md`, `agents/specs/*/spec.md` - Doc1-Doc5 and the spec review

## Prior findings re-verified

From review-1 (2026-03-30). There was no `summary.md`, so the findings were read from review-1 itself:

- Finding 1, `signals.py` calls `console_print` without `options` - resolved (`signals.py:60-89` passes `self.options`)
- Finding 2, `check_repo_clean` calls `lines_to_text` without `options` - resolved (`giter.py:97`)
- Finding 3, `check_repo_clean` missing the `options` annotation - resolved (`giter.py:86`)
- Finding 4, `YNConfirm.make_prompt` annotations - resolved (`giter.py:24`)
- Finding 5, AGENTS.md project structure out of date - still present, in a new form (Doc1)
- Finding 6, AGENTS.md tests listing - mostly resolved: the tree lists the tests, but omits `conftest.py` and `test_shlex.py` (Doc1)
- Finding 7, hook template injection surface - resolved: the hooks use a sandboxed environment, with injection tests in `test_hooks.py:138-169`
- Finding 8, `looper.py` uses `open()` rather than `pathlib` - still present (`looper.py:43`, `:63`)
- Finding 9, unused `options` parameter in the `iteration.py` write functions - still present (`iteration.py:348-387`). Review-1 recommended no action
- Finding 10, double logging in `state.py` - changed, and now worse: `add_to_state_work` catches `filelock.Timeout` (`state.py:110`) and only logs it. The `tenacity` retry on `Timeout` never sees the exception, so a busy lock loses the update silently, without retrying. Severity: **high**. Recommendation: remove the inner `except filelock.Timeout` so the retry works, and let `add_to_state` report the last failure. Add a test with a held lock.

Every task in `agents/tasks/audit-reviews/tasks-1.md` is marked done, and the source confirms each one.

## Recommendations

1. High: Finding 1 (exit status after an iteration exception), Finding 2 (state file overwritten), and review-1 Finding 10 (the lock-timeout retry never runs).
2. Medium: Findings 3 and 5 (stop and `--vars` correctness), Finding 4 (the trust decision on repository-local hooks), Findings 6 and 7 (error handling), Finding 8 (precedence), Finding 9 (polling cost), Finding 10 (the end-to-end test), and Finding 11 (documentation).
3. Low: Findings 12 to 19.

## Answers

Answered 2026-11-02:

- **Finding 4 (hooks from the repository settings file):** keep the feature and document the trust model. No code change.
- **Finding 3 (`is_error`):** any result with `is_error: true` is an error, whatever its subtype. The code changes to match the docs.
- **Finding 11, `current_iteration`:** the docs follow the code. `end` and `error` hooks see the last iteration that ran, or 0 if none ran.
- **Finding 11, `task_file_number`:** the code follows the docs. The number is the digits after the last `-` in `pathlib.Path.stem`, kept as written (`tasks-3` gives `3`, `tasks-0.md` gives `0`).
- Task list: `agents/tasks/audit-reviews/tasks-2.md`.
