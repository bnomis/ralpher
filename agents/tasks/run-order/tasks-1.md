# Tasks: Run order

**Spec:** `agents/specs/run-order/spec.md`
**Created:** 2026-11-04
**Version:** 1

The project has no type checker and no affected-tests tool. Each task's
Definition of Done names the test files it writes and the changed modules' own
test files; `order.py` and `bin/rro.py` are new, so nothing else imports them.
The last task runs those files, `test_install_claude.py` (the command is
installed by `bin/install-claude.py`), the whole-tree hooks, the pre-push audit
and the docs build.

---

## Task 1: Check the starting point

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** Module location; API

**Technical Goal:** The work starts from a tree that has none of it yet, so no
earlier attempt is overwritten.

**Subtasks:**

- [x] Check that the new names do not exist in the package: `grep -rnwE 'read_order|next_step|check_test_log|set_status|decisions_since|OrderSettings|ListRow|CheckpointRow|OrderFormatError|WaitsForUnmetError|LogVerdict' src/ralphlib` prints nothing; if it prints a line, stop as `operator`, naming it
- [x] Check that `src/ralphlib/order.py`, `bin/rro.py`, `claude/commands/rro.md` and `docs/run-order.md` do not exist; if one does, stop as `operator`, naming it
- [x] Check that `bin/install-claude.py` links every file in `claude/commands/` (it calls `symlink_dir` on that directory), so `rro.md` needs no installer change; if it links named files only, stop as `operator`, quoting the call

**Acceptance Criteria:**

- [x] None of the names or files exists, and the installer links the whole commands directory

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)

**Notes:**

- On 2026-11-04, when this list was written, every check above passed

---

## Task 2: Read an order file

**Status:** done
**Priority:** high
**Complexity:** medium
**Spec Reference:** The order file; Settings; API (`OrderSettings`, `ListRow`, `CheckpointRow`, `Order`, `read_order`); Error handling (`OrderFormatError`)

**Technical Goal:** One function turns an order file into typed rows and
settings, and refuses a malformed file before anything runs.

**Subtasks:**

- [x] Add `OrderFormatError` and `WaitsForUnmetError` to `src/ralphlib/exceptions.py`, subclassing `RalpherError`
- [x] Write `src/ralphlib/order.py` with the frozen dataclasses `OrderSettings`, `ListRow` (with `spec` and `index` properties parsed from `<spec>/tasks-<index>.md`), `CheckpointRow` and `Order`, as the spec's API gives them
- [x] Implement `read_order(path)`: find the settings table (first table whose header is `Setting | Value`) and the order table (header `# | Task list | Waits for | Stops for you | Status`); keep free text untouched; strip backticks from values; apply the defaults in the spec's Settings table; split `always wait for` on commas
- [x] Raise `OrderFormatError`, naming the line number, for: no settings table, a missing required setting (`checkpoint command`, `test pass line`), an unknown setting, a non-integer or non-positive `checkpoint every`, a duplicate label, a label with spaces, a task list path not of the form `<spec>/tasks-<index>.md` or not existing under `agents/tasks/` beside the order file's project root, a `Waits for` label not in the table
- [x] Read `**Checkpoint**` and `**Final checkpoint**` rows as `CheckpointRow` (`final` true for the second)
- [x] Write `src/tests/test_order.py` covering each valid shape (explicit checkpoints, none, a `3a` label, free text before, between and after the tables) and each `OrderFormatError` case above

**Acceptance Criteria:**

- [x] Every valid shape in the spec parses to the expected rows and settings, defaults included
- [x] Each malformed case raises `OrderFormatError` with its line number in the message

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_order.py` passes

**Notes:**

- Depends on Task 1
- The project root is the directory holding `agents/tasks/`; resolve it from the order file's path, not the working directory
- Fixtures write order files into `tmp_path` with the task list files they name

---

## Task 3: Choose the next step

**Status:** done
**Priority:** high
**Complexity:** medium
**Spec Reference:** API (`next_step`, `Step`); Error handling (`WaitsForUnmetError`); Implementation 1, 6

**Technical Goal:** The order file alone says what runs next, so a new session
resumes an order without remembering anything.

**Subtasks:**

- [x] Add the step types `RunList(row)`, `RunCheckpoint(position, final)`, `Resume(row)` and `Finished()` to `order.py`, and `Step` as their union
- [x] Implement `next_step(order)`: walk the rows in order; a list or checkpoint whose status is `running` or starts with `waiting:` is `Resume`; the first list not `merged ...` is `RunList`, unless its `waits_for` names a label not merged, which raises `WaitsForUnmetError` naming both labels; an explicit checkpoint row not `passed ...` is `RunCheckpoint` once every list above it is merged; a checkpoint with status `failed ...` is `Resume`
- [x] With no checkpoint rows in the table, return `RunCheckpoint` after every `checkpoint_every` merged lists counted since the last passed implicit checkpoint, and after the last list; record implicit checkpoints as their own lines below the table (`Checkpoint after <label>: <status>`), and read them back
- [x] Return `Finished` when every list is merged and the final checkpoint (explicit or implicit) has passed
- [x] Add tests to `src/tests/test_order.py`: each step for each state, an implicit checkpoint after the third merge, a resume of a running list and of a waiting list, a failed checkpoint, a `WaitsForUnmetError`, and `Finished`

**Acceptance Criteria:**

- [x] For every state in the tests, `next_step` returns the step the spec's Implementation section names
- [x] A row is never skipped: an unmet `Waits for` raises rather than moving on

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_order.py` passes

**Notes:**

- Depends on Task 2

---

## Task 4: Check a test log and write a status

**Status:** todo
**Priority:** high
**Complexity:** small
**Spec Reference:** API (`check_test_log`, `LogVerdict`, `set_status`); Settings (`test log`, `test pass line`, `test fail pattern`); Error handling (test gate failure)

**Technical Goal:** The merge gate and the order's record are each one
function, so the command never parses a log or edits a table by hand.

**Subtasks:**

- [ ] Add the frozen dataclass `LogVerdict(passed: bool, path: pathlib.Path, fail_lines: tuple[str, ...], has_pass_line: bool)`
- [ ] Implement `check_test_log(order, row, root)`: fill `{spec}` and `{index}` in `test_log`, resolve against `root`; a missing file is `passed=False` with no lines; strip ANSI colour codes before matching; `passed` only when the pass line is present and no line matches `fail_pattern`; `fail_lines` holds every matching line
- [ ] Implement `set_status(path, label, status)`: rewrite only the Status cell of the row with that label (or of the implicit checkpoint line for that label), keeping every other byte of the file, line endings included; raise `OrderFormatError` if the label is not found
- [ ] Add tests: pass, missing log, no pass line, a fail match, a log with colour codes, and `set_status` changing one cell and no other byte (compare the file before and after with that cell masked)

**Acceptance Criteria:**

- [ ] A log passes only with its pass line and no fail match
- [ ] `set_status` changes exactly one cell

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_order.py` passes

**Notes:**

- Depends on Task 2

---

## Task 5: List the decided stops since a commit

**Status:** todo
**Priority:** medium
**Complexity:** small
**Spec Reference:** API (`decisions_since`); Implementation 4

**Technical Goal:** A checkpoint's batch review is built from the commits that
carry a `Queue-decision:` trailer, found by code rather than by a remembered
list.

**Subtasks:**

- [ ] Add the frozen dataclass `Decision(commit: str, date: str, subject: str, body: str, task: str)`, where `task` is the trailer's value
- [ ] Implement `decisions_since(root, ref)`: the commits reachable from the default branch and not from `ref` whose message has a `Queue-decision:` trailer, oldest first, through `ralphlib.giter` or `gitpython` as the package already does; raise `GitError` if `ref` does not resolve
- [ ] Add tests in a temporary repository: commits with and without the trailer, a trailer in a merged branch, and an unknown `ref`

**Acceptance Criteria:**

- [ ] Only trailer-carrying commits after `ref` are returned, oldest first, with the trailer value parsed

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_order.py` passes

**Notes:**

- Depends on Task 2
- The default branch is `main` when `origin/HEAD` is unset

---

## Task 6: The `bin/rro.py` front end

**Status:** todo
**Priority:** high
**Complexity:** small
**Spec Reference:** API (`bin/rro.py` subcommands)

**Technical Goal:** The command calls one script whose output is one line of
JSON per call, so the routine reads results without parsing prose.

**Subtasks:**

- [ ] Write `bin/rro.py` with the subcommands `next <order>`, `check-log <order> <label>`, `set-status <order> <label> <status>` and `decisions <order> --since <ref>`, using `cappa` as the project's other entry points do
- [ ] Print one line of JSON per call (`orjson`): the step's kind and row for `next`, the `LogVerdict` fields for `check-log`, `{"ok": true}` for `set-status`, a list of decisions for `decisions`; on a `RalpherError` print `{"error": "<class>", "message": "..."}` to stdout and exit 2
- [ ] Write `src/tests/test_rro.py`, loading the script as `test_install_claude.py` loads its script, covering each subcommand's JSON on a fixture order and the error line for a malformed one

**Acceptance Criteria:**

- [ ] Each subcommand prints exactly one line of valid JSON, and an expected error exits 2 with its class named

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_rro.py` passes

**Notes:**

- Depends on Tasks 3, 4 and 5

---

## Task 7: The `/rro` command

**Status:** todo
**Priority:** high
**Complexity:** medium
**Spec Reference:** Implementation 1-7; Error handling; External dependencies

**User Story:** As an operator, I want one command that runs a whole order of
task lists, so that a session runs it unattended the same way in any project.

**Subtasks:**

- [ ] Write `claude/commands/rro.md` in the voice of `rrq.md`, invoked as `/rro <order file>`, with a section for each of the spec's Implementation steps: Start, A list, Merge, A checkpoint, Progress page, Resume, Finish
- [ ] In "A list", run the list exactly as `/rrq --decide` does by pointing at `rrq.md`'s steps rather than copying them, and say that a stop named in the row's `Stops for you` cell or in an `always wait for` rule file waits for the operator (`set-status ... "waiting: <stop>"`)
- [ ] In "Merge", name each check in order: every task `done`; `bin/rro.py check-log`; on a failure, the serial rerun of the directories the log names, then `waiting: test gate`; `git merge --no-ff`; `pre-commit run --all-files --hook-stage pre-push`; push; remove the worktree and branch; `set-status ... "merged <hash>"`; commit and push the order file. Never force, never `--no-verify`
- [ ] In "A checkpoint", say: one test run on the machine at a time as the project's own rules say; the command in the background from the main checkout; `passed <counts>` or `failed <counts>`; on a failure, list the lists merged since the last passing checkpoint, newest first, and stop; on a pass, `bin/rro.py decisions --since <previous checkpoint commit>`, the review document `agents/reviews/queue-decisions-<n>.md` with a recommendation per item, and its page as the shared reviews rule requires (approve or flag, accept-all, answers saved to the artifact database), then the next list without waiting
- [ ] In "Progress page", say the page's data is rebuilt from the order file at every list start, stop, merge and checkpoint, and its URL is written to the `progress page` setting on first publish
- [ ] Say what is reported to the operator at each event, in the relay format of `rrq.md`, and that state claims carry the time of the check they come from
- [ ] Add a worked example order file at `agents/tasks/run-order/example-order.md` that `read_order` accepts, and a test in `src/tests/test_order.py` that reads it

**Acceptance Criteria:**

- [ ] `rro.md` covers every Implementation step and every Error handling case of the spec
- [ ] The example order file parses

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run pytest src/tests/test_order.py` passes

**Notes:**

- Depends on Task 6
- The command names no project; examples use neutral names (`parser`, `lexicon`, `report`)

---

## Task 8: User guide

**Status:** todo
**Priority:** medium
**Complexity:** small
**Spec Reference:** Module location (`docs/run-order.md`); The order file; Settings

**User Story:** As an operator in a new project, I want a guide page that
shows an order file and the settings, so that I can write my first order
without reading the spec.

**Subtasks:**

- [ ] Write `docs/run-order.md`: what an order is and why (one paragraph), a working example order file first, every setting with its default and trade-off, what `/rro` does at each step, what stops for the operator, how to resume, and the convention that a list's last task saves its final test log at the `test log` path
- [ ] Add it to `mkdocs.yml` under User guide, and link it from `docs/guide/claude-code.md` beside `/rrq`
- [ ] Add `claude/commands/rro.md`, `bin/rro.py`, `src/ralphlib/order.py` and their tests to the project structure in `AGENTS.md`

**Acceptance Criteria:**

- [ ] The guide's example order file is the one Task 7 tests, or matches it

**Definition of Done:**

- [ ] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Task 7

---

## Task 9: Whole-tree checks and close the spec

**Status:** todo
**Priority:** high
**Complexity:** small
**Spec Reference:** Tests; the whole spec

**Technical Goal:** The branch passes every check before it merges, and the
spec says it is built.

**Subtasks:**

- [ ] Run the checks below and fix anything they find
- [ ] Set the spec's `**Status:**` to `implemented`

**Acceptance Criteria:**

- [ ] Every check below passes on the branch

**Definition of Done:**

- [ ] `pre-commit run --all-files` passes
- [ ] `pre-commit run --hook-stage pre-push auditme-all --all-files` passes
- [ ] `uv run pytest src/tests/test_order.py src/tests/test_rro.py src/tests/test_install_claude.py` passes
- [ ] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Task 8
- Prerequisite outside this repository: the shared taskdev skill should make a list's last task save its final test output at the order's `test log` path. Until it does, a task list written for an order names that path in its last task by hand; the guide says so (Task 8)
