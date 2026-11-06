# Tasks: Run order

**Spec:** `agents/specs/run-order/spec.md`
**Created:** 2026-11-06
**Version:** 2

This list implements amendment 1.1 of the run-order spec (approved
2026-11-06, review document `agents/specs/run-order/review-1.1.md`). Version
1.0 was built by `tasks-1.md`. It closes the `TODO.md` item "The `/rro`
command's steps do not match `bin/rro.py`'s interface".

The project has no type checker and no affected-tests tool. Each task's
Definition of Done names the test files it writes and the changed modules'
own test files. Only `src/tests/test_order.py` imports `ralphlib.order`, and
`src/tests/test_rro.py` exercises `bin/rro.py`. The last task runs those
files, `test_install_claude.py` (the command is installed by
`bin/install-claude.py`), the whole-tree hooks, the pre-push audit and the
docs build.

---

## Task 1: Check the starting point

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** Amendment 1.1

**Technical Goal:** Confirm the amendment has not been started, so the list
does not build over work already done.

**Subtasks:**

- [x] Run `grep -rnwE 'set_setting|SetSetting|set-setting' src/ralphlib bin/rro.py`
      and confirm no match
- [x] Confirm `CheckpointRow` and `RunCheckpoint` in `src/ralphlib/order.py`
      have no `label` field
- [x] If either check finds the work already present, stop the task as
      `blocked` and name what was found

**Acceptance Criteria:**

- [x] Both checks ran, and their result is recorded in the task's commit
      message

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)

**Notes:**

- Key files: `src/ralphlib/order.py`, `bin/rro.py`

---

## Task 2: Carry the set-status label on every checkpoint

**Status:** done
**Priority:** high
**Complexity:** medium
**Spec Reference:** API (`CheckpointRow`, `RunCheckpoint`, `set_status`); Tests (label round trip)

**Technical Goal:** Every checkpoint row and `RunCheckpoint` step carries
the exact label `set_status` takes, so no caller builds one.

**Subtasks:**

- [x] Write the failing tests first in `src/tests/test_order.py`: for an
      explicit checkpoint, an explicit final checkpoint, an implicit
      checkpoint after the third merge, an implicit final checkpoint on a
      one-list order, and a `Resume` of an explicit and of an implicit
      checkpoint, pass the step's (or the resumed row's) `label` to
      `set_status` with a `passed ...` status, re-read the order, and check
      `next_step` moves past it
- [x] Add `label: str` as the first field of `CheckpointRow` and of
      `RunCheckpoint`, matching the spec's API block
- [x] In `read_order`, set each table checkpoint row's label to
      `checkpoint:<n>`, counting checkpoint rows from 1 in table order (the
      same count `set_status` uses)
- [x] In `next_step`, give an explicit checkpoint's `RunCheckpoint` its
      row's label, and an implicit one's `RunCheckpoint` and `Resume` row
      `Checkpoint after <label>`
- [x] Update the existing tests that construct `CheckpointRow` or
      `RunCheckpoint` for the new field
- [x] Update `RunCheckpoint`'s docstring to describe `label`

**Acceptance Criteria:**

- [x] On a one-list order with no checkpoint row and the list merged,
      `next_step` returns
      `RunCheckpoint(label='Checkpoint after 1', position=0, final=True, after='1')`
- [x] Every round-trip test passes; each fails on the code before this task

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_order.py` passes

**Notes:**

- Depends on Task 1
- Key files: `src/ralphlib/order.py`, `src/tests/test_order.py`
- `bin/rro.py`'s `step_json` and `row_json` use `dataclasses.asdict`, so the
  field reaches `next`'s JSON with no change there; Task 4 tests it

---

## Task 3: Add `set_setting`

**Status:** done
**Priority:** high
**Complexity:** medium
**Spec Reference:** API (`set_setting`); Error handling; Tests (`set_setting`)

**Technical Goal:** One function writes one setting's Value cell, so the
command never edits the settings table by hand.

**Subtasks:**

- [x] Write the failing tests first in `src/tests/test_order.py`:
  - writing the empty `progress page` cell changes that cell and no other
    byte (compare the file bytes before and after);
  - a known setting with no row is added as the last row of the settings
    table, and `read_order` then returns its value;
  - an unknown name raises `OrderFormatError`;
  - `checkpoint every` set to `x` raises `OrderFormatError` and leaves the
    file byte-identical;
  - a value holding `|` round-trips through `read_order`
- [x] Implement `set_setting(path, name, value)` in `src/ralphlib/order.py`
      beside `set_status`, reusing `replace_cell`, `split_cells`,
      `strip_ending` and `SETTINGS_HEADER`: refuse a name not in
      `KNOWN_SETTINGS`, rewrite the row's second cell, or insert a new
      `| <name> | <value> |` row after the settings table's last row with
      the file's line ending
- [x] After writing, call `read_order(path)`; if it raises, write the
      original bytes back and re-raise
- [x] Give it the docstring from the spec's API block

**Acceptance Criteria:**

- [x] Every test above passes, and each fails before the function exists
- [x] No byte outside the target cell (or the added row) changes

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_order.py` passes

**Notes:**

- Depends on Task 1
- Key files: `src/ralphlib/order.py`, `src/tests/test_order.py`

---

## Task 4: Expose `set-setting` and the label in `bin/rro.py`

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** API (subcommands, labels in `next`'s output); Tests (`test_rro.py`, `bin/rro.sh`)

**Technical Goal:** The command-line front end offers `set-setting` and
returns the label, and the wrapper is proved to work where `rro.py` alone
failed.

**Subtasks:**

- [x] Write the failing tests first in `src/tests/test_rro.py`:
  - `set-setting <order> "progress page" <url>` prints `{"ok":true}` and
    the order file then holds the URL;
  - `set-setting` with an unknown name prints the `OrderFormatError` JSON
    and exits 2;
  - `next` on a one-list order with the list merged prints a
    `run-checkpoint` with `"label":"Checkpoint after 1"`, and a `resume` of
    a checkpoint row carries its `label`;
  - `bin/rro.sh next <order>`, run with the working directory outside the
    repository and a `PATH` whose first `python` is a stub that cannot
    import `cappa`, exits 0 and prints the step JSON
- [x] Add a `SetSetting` cappa subcommand (`order`, `name`, `value`) to
      `bin/rro.py`, add it to `Rro.command`'s union in alphabetical place
      where the project's ordering rule applies, and dispatch it in `run`
      to `ralphlib.order.set_setting`, returning `{'ok': True}`

**Acceptance Criteria:**

- [x] Every test above passes; the `set-setting` and label tests fail
      before the change
- [x] `bin/rro.sh` itself is not changed

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run pytest src/tests/test_rro.py src/tests/test_order.py` passes

**Notes:**

- Depends on Task 2 and Task 3
- Key files: `bin/rro.py`, `bin/rro.sh`, `src/tests/test_rro.py`
- The stub `python` goes in a `tmp_path` directory placed first on `PATH`;
  it exits non-zero on any run, so the test fails if `rro.sh` falls through
  to it

---

## Task 5: Update the command and the user guide

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** Module location; Implementation (Start, A checkpoint, Progress page)

**User Story:** As an operator running `/rro`, I want the command to call
the script the way that works and to pass labels and settings through
subcommands, so that a run never stops on an interface gap or edits a
table by hand.

**Subtasks:**

- [x] In `claude/commands/rro.md`: say to run the script as
      `"$RALPHER_PATH/bin/rro.sh"`, and replace every `bin/rro.py` with
      `bin/rro.sh`
- [x] In `rro.md` (A checkpoint, step 3, and Resume): pass the step's or
      row's `label` from `next` to `set-status` unchanged, and never build a
      label
- [x] In `rro.md` (Progress page): write the URL with
      `bin/rro.sh set-setting <order> "progress page" <url>`, then commit
      and push
- [x] In `docs/run-order.md`: replace `bin/rro.py` with `bin/rro.sh` in the
      prose and the examples, add a `set-setting` example, and say that
      `next` returns each checkpoint's `label` and what its two forms are
- [x] Grep both files for `rro.py` afterwards; the only remaining mention
      may be the guide's note that `rro.sh` runs it

**Acceptance Criteria:**

- [x] `grep -n 'bin/rro.py' claude/commands/rro.md` finds nothing
- [x] Both files name `set-setting` and the checkpoint `label`

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `uv run --group docs mkdocs build --strict` passes

**Notes:**

- Depends on Task 4
- Key files: `claude/commands/rro.md`, `docs/run-order.md`

---

## Task 6: Whole-tree checks, close the spec and the TODO item

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** Tests; the whole amendment

**Technical Goal:** The branch passes every check before it merges, the
spec says it is built, and the `TODO.md` item moves to `DONE.md`.

**Subtasks:**

- [x] Run the checks below and fix anything they find
- [x] Set the spec's `**Status:**` to `implemented`
- [x] Move the `TODO.md` item "The `/rro` command's steps do not match
      `bin/rro.py`'s interface" to the end of `DONE.md`: append its heading
      and body unchanged, then a line
      `Done: <YYYY-MM-DD> - spec agents/specs/run-order/spec.md amendment 1.1, tasks agents/tasks/run-order/tasks-2.md.`
      and remove it from `TODO.md`
- [x] Take the baseline `TODO.md` from the commit that added this task list:
      `git show "$(git log --diff-filter=A --format=%H -- agents/tasks/run-order/tasks-2.md)":TODO.md > <scratch file>`

**Acceptance Criteria:**

- [x] Every check below passes on the branch

**Definition of Done:**

- [x] `pre-commit run --all-files` passes
- [x] `pre-commit run --hook-stage pre-push auditme-all --all-files` passes
- [x] `uv run pytest src/tests/test_order.py src/tests/test_rro.py src/tests/test_install_claude.py` passes
- [x] `uv run --group docs mkdocs build --strict` passes
- [x] `python3 ~/.claude/skills/todo-review/verify_bodies.py <scratch file> TODO.md DONE.md` exits 0

**Notes:**

- Depends on Task 5

---

## Task 7: Resolve the ruff version drift the pre-push audit reports

**Status:** done
**Priority:** high
**Complexity:** small
**Spec Reference:** none (found by Task 6)

**Technical Goal:** `pre-commit run --hook-stage pre-push auditme-all --all-files`
passes.

**Subtasks:**

- [x] The audit reports `.pre-commit-config.yaml:4 ruff-version-drift`: the
      ruff in the project environment (0.17.1) differs from the
      `ruff-pre-commit` rev (v0.17.3). Make them agree; this needs an edit to
      `.pre-commit-config.yaml` or `uv.lock`, both under "Do not modify" in
      `AGENTS.md`, so the operator must approve it
- [x] Re-run the Task 6 checks and finish Task 6

**Notes:**

- Depends on Task 6; Task 6 is blocked on this. Every other Task 6 check
  passed: `pre-commit run --all-files`, the three test files, the docs
  build, and `verify_bodies.py`. The spec status and the `TODO.md` to
  `DONE.md` move are already made
- Decided by the operator, 2026-11-06: use ruff 0.17.2 in both places.
  0.17.3 is newer than the project's 14-day `exclude-newer` window allows
  until 2026-11-10. `pyproject.toml` and `uv.lock` (through `uv add --dev
  ruff==0.17.2`) and the `ruff-pre-commit` rev now all say 0.17.2; the
  pre-push audit passes
