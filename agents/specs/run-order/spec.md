# Run order

**Version:** 1.2
**Status:** implemented
**Date:** 2026-11-07 (1.2: no implicit checkpoint before a short tail; 1.1: 2026-11-06; 1.0: 2026-11-04)
**Review page:** https://claude.ai/artifact/3a2sGJiXFLn78YeDsixi2G (1.0: every section approved by the operator, 2026-11-04 08:29 UTC)
**Review page (1.1):** https://claude.ai/artifact/3Nk6F46yV929P4TZTPxv8F (review document: `agents/specs/run-order/review-1.1.md`)

`/rrq --decide` runs one task list as a queue and decides the stops it may
decide. A larger piece of work is several task lists run in a set order: each
list is merged before the next starts, a slower whole-project check runs after
every few lists, and the stops Claude decided are reviewed by the operator in
batches. Until now the session running such an order carried that routine in
its head and in one project's rules. This spec makes it a command, `/rro`,
that runs a whole order from one order file, with the parts that differ per
project (the checkpoint command, how often it runs, where the final test log
is, which stops always wait) read from the order file's own settings.

Background (another project, 2026-11-02 to 2026-11-04): two orders ran this
way unattended, the queue stops were decided and reviewed in batches, and the
operator was asked only for labelling, file copies into a data directory, and
the batch reviews. The operator asked for
the same way of working in other projects on 2026-11-04.

### Amendment 1.1 (2026-11-06)

`/rro` ran an order in another project on 2026-11-06, and three of its steps
failed or had no supported route, each a gap between what `rro.md` tells the
session to do and what `bin/rro.py` offers:

- `rro.md` said to run `"$RALPHER_PATH/bin/rro.py"`. Run that way from
  another project's directory it stopped at once with
  `ModuleNotFoundError: No module named 'cappa'`: its `#!/usr/bin/env python`
  runs whatever `python` is first on the caller's `PATH`. `bin/rro.sh`, which
  sources `bin/activate.sh` first, ran every subcommand.
- `rro.md` says to write the progress page's URL to the `progress page`
  setting and never to edit a table by hand, but no subcommand writes a
  setting, so the session edited the settings table with `sed`.
- On an order with one list and no checkpoint row, `next` returned
  `{"kind":"run-checkpoint","position":0,"final":true,"after":"1"}`.
  `set-status <order> final ...` failed with `OrderFormatError: no row
  labelled 'final'`; `set-status <order> "Checkpoint after 1" ...` worked.
  The label `set-status` takes for a checkpoint was stated only in
  `set_status`'s docstring, so the session had to build it.

The amendment makes the command and the script name the same things: the
command runs `bin/rro.sh`; every step and row `next` returns carries the
exact label `set-status` takes; a new `set-setting` subcommand writes one
setting cell. Running through the wrapper follows the project's rule that
every `bin/` script has a `.sh` wrapper that activates the venv, as `/rrq`
already does with `bin/rrq.sh`.

Operator decisions, 2026-11-04: the command lives in ralpher beside `/rrq`;
each order file carries its settings; a checkpoint publishes its batch review
and the order keeps going without waiting for the answers; a list's final
test run is checked from a log its last task saves at a set path, not rerun.

## Module location

- `claude/commands/rro.md` - the command (installed by `bin/install-claude.sh`
  like `rrq.md`)
- `src/ralphlib/order.py` - reading the order file, choosing the next step,
  checking a test log, writing a status back
- `bin/rro.py` - the command-line front end; the command calls it through
  `bin/rro.sh`, which activates ralpher's venv first
- `src/tests/test_order.py`, `src/tests/test_rro.py`
- `docs/run-order.md` - user guide page, linked from `mkdocs.yml`

## The order file

A Markdown file in the project, `agents/tasks/order-<name>.md` by
convention, with a settings table and an order table, in that order. Every
other line is free text and is kept as written.

```markdown
# Order: <name>

| Setting | Value |
|---|---|
| checkpoint command | `make test-slow` |
| checkpoint every | 3 |
| test log | `ralpher-logs/{spec}/tasks-{index}/final-tests.log` |
| test pass line | `all selected test directories passed` |
| test fail pattern | `FAILED` |
| always wait for | `claude/rules/queue-stops.md` |
| progress page | |

| # | Task list | Waits for | Stops for you | Status |
|---|---|---|---|---|
| 1 | `parser/tasks-1.md` | - | - | todo |
| 2 | `lexicon/tasks-1.md` | - | the verdicts on the new entries (Task 3) | todo |
| | **Checkpoint** | | | todo |
| 3 | `report/tasks-2.md` | 1 | - | todo |
| | **Final checkpoint** | | | todo |
```

- `#` is any label without spaces (`3a` is allowed); labels are unique.
- `Task list` is a path under `agents/tasks/`, as `<spec>/tasks-<index>.md`.
- `Waits for` is `-` or labels separated by commas; each must be merged
  before the row may start.
- `Stops for you` is free text naming the stops that always wait for the
  operator in that list; `-` means none beyond the settings' rule file.
- `Status` is written by `/rro` only: `todo`, `running`,
  `waiting: <what>`, `merged <short hash>`, or for a checkpoint
  `passed <counts>` or `failed <counts>`.
- A `**Checkpoint**` row may be written by hand; where the table has none,
  `/rro` runs one after every `checkpoint every` merged lists and after the
  last, but skips one that would leave fewer than `checkpoint every` lists
  before the last: with `checkpoint every` 3, an order of four or five lists
  gets one checkpoint, after the last, and six get two. A short tail would
  otherwise cost a whole checkpoint run for one or two lists. A
  `**Final checkpoint**` row ends the order.

## Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `checkpoint command` | `str` | required | Shell command run from the main checkout on the default branch, in the background |
| `checkpoint every` | `int` | `3` | Merged lists between checkpoints when the table has no checkpoint rows |
| `test log` | `str` | `ralpher-logs/{spec}/tasks-{index}/final-tests.log` | Path, relative to the main checkout, where a list's last task saves its final test output; `{spec}` and `{index}` are filled per list |
| `test pass line` | `str` | required | A line the log must contain for the run to count as passed |
| `test fail pattern` | `str` | `FAILED` | Regular expression; any match in the log fails the gate |
| `always wait for` | `str` | empty | Comma-separated rule files whose listed stops are never decided, in addition to `/rrq`'s own exceptions |
| `progress page` | `str` | empty | Artifact URL of the progress page; filled in by `/rro` when it first publishes one |

An order file with no settings table, or without a required setting, is an
error before anything runs.

## API

```python
@dataclass(frozen=True)
class OrderSettings:
    checkpoint_command: str
    checkpoint_every: int
    test_log: str
    pass_line: str
    fail_pattern: str
    wait_rules: tuple[str, ...]
    progress_page: str | None


@dataclass(frozen=True)
class ListRow:
    label: str
    task_list: str  # '<spec>/tasks-<index>.md'
    waits_for: tuple[str, ...]
    stops_for_you: str
    status: str

    @property
    def spec(self) -> str: ...
    @property
    def index(self) -> str: ...


@dataclass(frozen=True)
class CheckpointRow:
    label: str  # the label set_status takes: 'checkpoint:<n>' or 'Checkpoint after <label>'
    final: bool
    status: str


@dataclass(frozen=True)
class Order:
    settings: OrderSettings
    rows: tuple[ListRow | CheckpointRow, ...]
    implicit: tuple[tuple[str, str], ...] = ()  # (after label, status) per implicit checkpoint line


@dataclass(frozen=True)
class RunList:
    row: ListRow


@dataclass(frozen=True)
class RunCheckpoint:
    label: str  # the label set_status takes
    position: int  # index in Order.rows of the checkpoint row, or of the list it follows
    final: bool
    after: str  # label of the last list the checkpoint covers


@dataclass(frozen=True)
class Resume:
    row: ListRow | CheckpointRow


@dataclass(frozen=True)
class Finished: ...


def read_order(path: pathlib.Path) -> Order:
    """Parse an order file; raise OrderFormatError naming the line on any fault."""


Step = RunList | RunCheckpoint | Resume | Finished


def next_step(order: Order) -> Step:
    """The first row not yet merged or passed, in table order.

    A running or waiting row is returned as Resume(row). A list whose
    waits_for holds an unmerged label raises WaitsForUnmetError. A checkpoint
    is due when the table names one next, or, with none in the table, after
    every `checkpoint_every` merged lists and after the last, skipping one
    that would leave fewer than `checkpoint_every` lists before the last.
    """


def check_test_log(order: Order, row: ListRow, root: pathlib.Path) -> LogVerdict:
    """LogVerdict(passed, path, fail_lines, has_pass_line) for the row's saved log."""


def set_status(path: pathlib.Path, label: str, status: str) -> None:
    """Rewrite one row's Status cell in place, leaving every other byte unchanged.

    label is a list's label, 'checkpoint:<n>' for the nth checkpoint row, or
    'Checkpoint after <label>' for an implicit checkpoint's line below the
    order table, added the first time it is set.
    """


def set_setting(path: pathlib.Path, name: str, value: str) -> None:
    """Rewrite one setting's Value cell in place, leaving every other byte unchanged.

    A known setting with no row is added as the last row of the settings
    table. Raises OrderFormatError for an unknown name, and for a value that
    makes the file fail read_order, in which case the file is left as it was.
    """


def decisions_since(root: pathlib.Path, ref: str) -> list[Decision]:
    """Commits on the default branch since ref carrying a Queue-decision trailer."""
```

`bin/rro.py` exposes them as subcommands, each printing one line of JSON:
`next <order>`, `check-log <order> <label>`, `set-status <order> <label>
<status>`, `set-setting <order> <name> <value>`, `decisions <order> --since
<ref>`. `bin/rro.sh` is the entry point the command and the user guide name.

Labels in `next`'s output: a `run-checkpoint` step carries `label`, and every
row it returns (`run-list` and `resume`) carries `label` too, whether a list
or a checkpoint row. That string is passed to `set-status` unchanged; the
command never builds a label itself. For example, on an order with one list
and no checkpoint row, after the list is merged:

```json
{"kind":"run-checkpoint","label":"Checkpoint after 1","position":0,"final":true,"after":"1"}
```

and for the second `**Checkpoint**` row in the table, `"label":"checkpoint:2"`.
`set-setting` prints `{"ok": true}` as `set-status` does.

## Error handling

- `OrderFormatError`: missing or unknown settings, a duplicate label, a
  task list path that does not exist, a `Waits for` label not in the table.
  Raised by `read_order`; the command stops before any run and quotes it.
  Also raised by `set_status` for a label no row has, and by `set_setting`
  for an unknown setting name or a value the file then fails to parse with
  (for example `checkpoint every` set to `x`); `set_setting` restores the
  file's original bytes before raising.
- `WaitsForUnmetError`: the next row waits for a row that is not merged;
  the command stops and names both. It is never skipped over, since the
  table order is the operator's.
- Test gate failure (`LogVerdict.passed` false): a missing log, no pass
  line, or a fail-pattern match. The command does not merge. It reruns the
  failing directories serially if the log names them, as the project's last
  task would, and merges only if they pass, recording that in the row's
  status; otherwise it sets `waiting: test gate` and stops for the operator.
- A merge conflict, a rejected push, or a failing pre-push hook: stop and
  report; never force, never skip hooks.
- A failed checkpoint: status `failed <counts>`, stop, and report the lists
  merged since the last passing checkpoint, newest first, as the suspects.

## Implementation

`claude/commands/rro.md` is the routine; `order.py` holds everything a
script can decide, so the routine never parses a table by hand.

1. **Start.** Invoke as `/rro <order file>`. Check the working directory is
   the main checkout on the default branch, clean, and level with its
   remote. Run `"$RALPHER_PATH/bin/rro.sh" next`; every call in the command
   goes through `bin/rro.sh`, never `bin/rro.py` directly.
2. **A list.** Set its status to `running`, commit the order file, and run
   it exactly as `/rrq --decide <spec> <index>` does (background run,
   monitor, relayed lines). Stops listed in its `Stops for you` cell or in
   an `always wait for` rule are not decided: set `waiting: <the stop>` and
   ask the operator. Every decided stop carries the `Queue-decision:`
   trailer.
3. **Merge.** When the queue completes with every task done, run
   `check-log`. On a pass: merge with `--no-ff`, run the pre-push hooks,
   push, remove the list's worktree and branch, set `merged <hash>`, commit
   and push the order file. Then take the next step.
4. **A checkpoint.** Run the checkpoint command in the background from the
   main checkout, one test run on the machine at a time as the project's
   rules say. On a pass, set `passed <counts>`, then collect
   `decisions --since` the previous checkpoint's commit, write the batch
   review document (`agents/reviews/queue-decisions-<n>.md`) with a
   recommendation per item, publish its page (approve or flag, an
   accept-all button, answers saved to the artifact database), and go on
   to the next list without waiting. When the operator says the page is
   answered, copy the answers into the document and commit it. The status
   is written with `set-status <order> <label>`, where `<label>` is the
   step's `label` exactly as `next` returned it.
5. **Progress page.** Publish one page per order at the first step,
   record its URL with `set-setting <order> "progress page" <url>`, and
   republish it at every list start,
   stop, merge and checkpoint: each row's status and the time of the last
   change. Its data is built from the order file, so the file stays the
   record and the page never disagrees with it.
6. **Resume.** The order file is the state: a new session given the same
   file continues from `next_step`, so an order survives a lost session.
7. **Finish.** After the final checkpoint and its batch review, report the
   merged lists and the decisions awaiting review.

## Prerequisites in other repositories

- The shared taskdev skill's last-task test check must save its output to
  the order's `test log` path. Until it does, a task list written for an
  order names the path in its last task by hand. Check: the skill's
  Definition of Done section mentions saving the final test log.

## Tests

`test_order.py`: parsing each valid shape (explicit checkpoints, none,
`3a` labels, free text around the tables) and each `OrderFormatError`;
`next_step` for each state, including an implicit checkpoint after the
third merge and a resume; `check_test_log` for pass, missing log, missing
pass line and a fail match; `set_status` changes one cell and no other
byte. `test_rro.py`: each subcommand's JSON on a fixture order.

Added in 1.1:

- the label round trip: for each checkpoint `next_step` can return
  (explicit, explicit final, implicit, implicit final on a one-list order,
  and a `Resume` of each kind), passing the returned `label` to
  `set_status` succeeds and the next `next_step` moves past it;
- `set_setting`: writing an empty `progress page` cell changes that cell and
  no other byte; a missing known row is added to the settings table; an
  unknown name raises `OrderFormatError`; an invalid `checkpoint every`
  raises and leaves the file byte-identical; a value holding `|` round-trips
  through `read_order`;
- `test_rro.py`: `set-setting`'s JSON, and `label` in `next`'s JSON;
- `bin/rro.sh next <order>` run from a directory outside the repository
  with a `PATH` whose `python` lacks `cappa` succeeds (the regression for
  the first finding).

## External dependencies

- `/rrq` and `bin/rrq.sh` (this repository).
- `bin/activate.sh` (this repository), which `bin/rro.sh` sources.
- `git`, and the project's `pre-commit` hooks.
- The Claude Code Artifact tool, for the progress page and batch reviews; without
  it the command writes the review document and reports that no page was
  published.
