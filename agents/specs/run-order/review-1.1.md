# Review: run-order spec amendment 1.1

**Review page:** https://claude.ai/artifact/3Nk6F46yV929P4TZTPxv8F
**Spec:** `agents/specs/run-order/spec.md` (version 1.1)
**Date:** 2026-11-06

## What is being reviewed and how

The run-order spec is amended to close the `TODO.md` item "The `/rro`
command's steps do not match `bin/rro.py`'s interface", found when `/rro`
ran an order in another project on 2026-11-06. Three steps of
`claude/commands/rro.md` failed or had no supported route: the script would
not start, no subcommand wrote the `progress page` setting, and the label
`set-status` takes for a checkpoint was not in `next`'s output. Approve or
flag each change below. Implementation waits until every item has an
answer; a task list follows, and the item stays in `TODO.md` until that list
is done.

## Automatic checks

- pass: `pre-commit run --files agents/specs/run-order/spec.md` (ruff format,
  audit hits in changed files, no project names).
- pass: drift check against the code on 2026-11-06. The 1.0 spec's API
  omitted `Order.implicit` and the `RunList`, `RunCheckpoint`, `Resume` and
  `Finished` step classes that `src/ralphlib/order.py` defines, and
  `set_status`'s label forms lived only in the code's docstring. The
  amendment writes all of them into the spec (item 6).

## The items

1. **Motivation.** A new "Amendment 1.1" subsection carries the three dated
   findings verbatim in substance, with the exact JSON and error seen.
2. **Run through `bin/rro.sh`.** The command and the user guide call
   `"$RALPHER_PATH/bin/rro.sh"`, never `bin/rro.py`. `bin/rro.sh` sources
   `bin/activate.sh`, so ralpher's venv is used whatever `python` the caller
   has. I chose this over making `rro.py` find its own venv because the
   shared rule for utility scripts gives every `bin/` script a `.sh`
   wrapper, and `/rrq` already runs `bin/rrq.sh`; it is reversible.
3. **The label in `next`'s output.** `CheckpointRow` gains `label`
   (`checkpoint:<n>` for the nth checkpoint row, `Checkpoint after <label>`
   for an implicit one), set by `read_order` and `next_step`.
   `RunCheckpoint` gains `label` too. Every step and row `next` returns then
   carries the exact string `set-status` takes, and `rro.md` says to pass it
   unchanged. This adds a field to `next`'s JSON; no existing field changes.
4. **A `set-setting <order> <name> <value>` subcommand.** `set_setting`
   rewrites one setting's Value cell and no other byte, as `set_status` does
   for a Status cell. A known setting with no row is added as the settings
   table's last row (I chose this to match `set_status` adding an implicit
   checkpoint's line). An unknown name, or a value that makes the file fail
   to parse (such as `checkpoint every` set to `x`), raises
   `OrderFormatError` and leaves the file byte-identical. `rro.md`'s
   Progress page step uses it for the URL.
5. **Error handling.** The `OrderFormatError` entry names the new
   `set_setting` failures and the existing `set_status` unknown-label
   failure.
6. **API brought level with the code.** The step classes and
   `Order.implicit` now appear in the spec's API block; `set_status`'s
   docstring there names its label forms.
7. **Tests.** A label round trip for every checkpoint shape `next_step` can
   return (explicit, final, implicit, implicit final on a one-list order,
   and a `Resume` of each); `set_setting`'s byte-for-byte edit, added row,
   unknown name, invalid value and `|` escaping; `set-setting`'s and
   `next`'s JSON in `test_rro.py`; and `bin/rro.sh next` run from outside
   the repository with a `python` lacking `cappa` on `PATH`.

`claude/commands/rro.md` and `docs/run-order.md` change in the same work,
following the spec; they are not separate items.

## Decisions

None. The two choices above (the wrapper, and adding a missing setting row)
are reported in items 2 and 4.

## Answers

Answered on the review page, 2026-11-06 13:58 UTC (accept-all, no comments):

| Item | Verdict |
|---|---|
| 1. Motivation | approve |
| 2. Run through `bin/rro.sh` | approve |
| 3. The label in `next`'s output | approve |
| 4. A `set-setting` subcommand | approve |
| 5. Error handling | approve |
| 6. API brought level with the code | approve |
| 7. Tests | approve |
