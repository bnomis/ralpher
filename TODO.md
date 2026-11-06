# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## The `/rro` command's steps do not match `bin/rro.py`'s interface

Three steps of `claude/commands/rro.md` failed or had no supported route when
`/rro` ran an order in another project on 2026-11-06. Each is a gap between
what the command tells the session to do and what `bin/rro.py` offers. The
command and `docs/run-order.md` change together, and the run-order spec
(`agents/specs/run-order/`) where it fixes the interface.

Fix direction: make `next` and the command name the same things. Tell the
session to run `bin/rro.sh` (or make `rro.py` find its own venv); add a
`set-setting <order> <name> <value>` subcommand that rewrites one settings
cell as `set_status` rewrites one Status cell; and have `next` return, in
every `run-checkpoint` and checkpoint `resume`, the exact label `set-status`
takes, with `rro.md` saying to pass it unchanged. Update `docs/run-order.md`
in the same commit.

Spec: `agents/specs/run-order/spec.md` (amendment 1.1, approved 2026-11-06); tasks: `agents/tasks/run-order/tasks-2.md`.

### `bin/rro.py` fails when run as the command says

Found on 2026-11-06. `rro.md` says "Run the script as
`"$RALPHER_PATH/bin/rro.py"`", and every step names `bin/rro.py`. Run that
way from another project's directory it stopped at once with
`ModuleNotFoundError: No module named 'cappa'`. `bin/rro.sh`, which sources
`bin/activate.sh` first, ran every subcommand.

Cause: `bin/rro.py` starts `#!/usr/bin/env python`, so it runs whatever
`python` is first on the caller's `PATH`, not ralpher's venv, and imports
`cappa` and `orjson` (`bin/rro.py`, top of file). `rrq.md` already tells the
session to run `bin/rrq.sh` for the same reason.

### No subcommand writes the `progress page` setting

Found on 2026-11-06. `rro.md` (Progress page) says to write the page's URL to
the order file's `progress page` setting on the first publish, and its
opening says "never read or edit a table by hand". `bin/rro.py` offers only
`next`, `check-log`, `set-status` and `decisions`, so the session wrote the
URL with a one-line `sed` on the settings table.

Cause: `src/ralphlib/order.py` reads `progress page` into
`Settings.progress_page` but has no writer for any setting.

### The label `set-status` takes for an implicit checkpoint is not documented

Found on 2026-11-06, on an order with one list and no checkpoint row. `next`
returned `{"kind":"run-checkpoint","position":0,"final":true,"after":"1"}`.
`set-status <order> final "passed ..."` failed with `OrderFormatError: no row
labelled 'final'`; `set-status <order> "Checkpoint after 1" "passed ..."`
worked and added the line below the table. `rro.md` (A checkpoint, step 3)
says only `set-status <order> <label>`, and neither it nor
`docs/run-order.md` says what a checkpoint's label is.

Cause: `set_status` in `src/ralphlib/order.py` takes `checkpoint:<n>` for the
nth checkpoint row and `Checkpoint after <label>` for an implicit one, which
only its docstring states; `RunCheckpoint` carries `position`, `final` and
`after` but no label, so the session has to build it.
