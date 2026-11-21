# Done

Finished `TODO.md` items, oldest first.

## The auditme checker is not adopted here, so its hits accumulate unrecorded

Found on 2026-10-31 in a TODO review: `.pre-commit-config.yaml` runs ruff
and shellcheck only, so no hook runs the shared auditme checker, and the
finding below says to re-run it "once the hooks are adopted" without any item
recording that adoption. Running `python3 ~/.claude/skills/auditme/checks/audit.py .`
on 2026-10-31 at `f339eec` reported unaccepted hits from rules that predate
that day's checker changes, as well as the one hit the finding below records.
Hits by rule on 2026-10-31:

| Rule | Unaccepted hits |
|---|---|
| `bare-parametric-annotation` | 8 |
| `except-interpolation` | 14 |
| `filesystem-envelope-gap` | 1 |
| `from-import` | 45 |
| `get-container-default-then-method-call` | 4 |
| `leading-underscore-binding` | 3 |
| `leading-underscore-def-class` | 1 |
| `literal-duplication` | 16 |
| `mutable-module-level-exported` | 6 |
| `mutable-store-without-copy` | 2 |
| `non-alphabetical-literal` | 1 |
| `paired-sibling-helpers` | 13 |
| `passthrough-shim` | 2 |
| `silent-broad-except` | 2 |
| `stdlib-logging` | 1 |

Cause: the project has not adopted the shared audit hooks, so nothing fails
when a hit appears, and each checker change surfaces hits that no item tracks.
Adopting them means clearing every hit first, because the pre-push hook fails
on any unaccepted one; the finding below is one part of that.

Fix direction: fix or accept every hit the checker reports (the finding
below gives the fix-or-accept rule), then adopt the hooks with the
`project-setup` skill. That edits `.pre-commit-config.yaml`, which `AGENTS.md`
lists as not to be modified without explicit instruction, so ask before that
step.

Spec: agents/specs/auditme-adoption/spec.md; tasks: agents/tasks/auditme-adoption/tasks-1.md.

### The auditme checker's 2026-10-31 rules report hits here

Found on 2026-10-31 by running the shared auditme checker at agents `108559d`
on this repository at `2726c44e`. Two checker changes shipped that day (agents
`c437b07`) report hits here:

- `mutable-module-level-exported` now counts the builtin constructor calls
  `list(...)`, `dict(...)` and `set(...)` as their literals:
  - `src/ralphlib/hooks.py:27` `processed_hooks`, a `set(...)` read by one
    other file
- the new `raises-section-drift` rule (A4) compares each `Raises:` section with
  the domain errors reaching the caller: none.

Cause: the checker gained the rules; the code predates them.

Fix direction: fix or accept each hit - wrap an exported constructor call in
`tuple(...)`, `frozenset(...)` or `types.MappingProxyType(...)`, and correct each
`Raises:` section from the body. A hit the rule gets wrong is accepted with
`# auditme: accept[<rule>] <reason>` on its `def` or assignment line, and the
pattern raised as a request in the auditme skill's `requests.md`.
Re-run with `pre-commit run auditme-all --hook-stage manual --all-files` once
the hooks are adopted, or `python3 ~/.claude/skills/auditme/checks/audit.py .`.

Done: 2026-11-01 - agents/specs/auditme-adoption/spec.md, agents/tasks/auditme-adoption/tasks-1.md.

## The printed cleanup commands stop before the push when the branch was pushed

Found on 2026-11-01 after the `agents/tasks/auditme-adoption/tasks-1.md`
queue completed. The operator ran the "Probable cleanup commands" it printed.
The merge and the worktree removal succeeded, then `git branch -d
worktree-auditme-adoption-tasks-1` failed with "not deleting branch ... that
is not yet merged to 'refs/remotes/origin/worktree-auditme-adoption-tasks-1',
even though it is merged to HEAD", and the `&&` chain stopped before
`git push`. The branch had been pushed with `-u` for a CI run (Task 12), and
two more commits landed on it after that push, so its upstream was behind it.
`git branch -d` checks a branch with an upstream against that upstream, not
only against `HEAD`. The remote branch was also left on GitHub, which nothing
in the printed commands removes.

Cause: `cleanup_cmds` in `src/ralphlib/looper.py` builds the chain with
`git branch -d {branch}`, which refuses whenever the branch tracks a remote
copy that lacks its last commits. No test covers `cleanup_cmds`.

Fix direction: print `git branch -D {branch}`, which is safe because it runs
only after the merge in the same `&&` chain has succeeded. Decide whether to
also print `git push origin --delete {branch}` when the branch has a remote
copy, or a note saying so. Add tests on `cleanup_cmds`'s output.

Done: 2026-11-01 - `cleanup_cmds` in `src/ralphlib/looper.py` prints `git branch -D` and then a guarded `(git push origin --delete <branch> 2>/dev/null || true)` after `git push`; `TestCleanupCmds` in `src/tests/test_looper.py` covers it.

## The verified-stop spec still says `proposed` though its task list is done

Found on 2026-11-01 in a TODO review: `agents/specs/verified-stop/spec.md`
has `**Status:** proposed`, while every task in
`agents/tasks/verified-stop/tasks-1.md` has `**Status:** done`. The
auditme-adoption spec's "Out of scope" section and item 18 of
`agents/specs/auditme-adoption/review-1.md` (both 2026-10-31) say this stale
status "is fixed separately"; nothing recorded that work.

Cause: no task in `agents/tasks/verified-stop/tasks-1.md` sets the spec's
status, so nothing moved it on (suspected to predate the `taskdev` rule that a
list's last task sets its spec to `implemented`; not checked).

Fix direction: check that the code still matches the spec (`/specdev` drift
detection on `src/ralphlib/verifier.py`), then set `**Status:** implemented`.

Done: 2026-11-01 - drift check found the code matching the spec (API, `--no-verify-stop`, rejection line, `stop_rejected` state, `rrq.md` relay, README; `test_verifier.py` and `test_looper.py` pass); `agents/specs/verified-stop/spec.md` set to `**Status:** implemented`.

## The auditme checker misses an `OSError` held in a named exception tuple

Found on 2026-11-01 in a TODO review. On 2026-10-31 the checker's
`filesystem-envelope-gap` rule flagged `src/ralphlib/verifier.py:129`,
although the next handler catches `READ_ERRORS`
(`src/ralphlib/verifier.py:17`), a tuple that holds `OSError`. The checker
reads the handler's name, not the tuple's value. The hit is accepted with
`# auditme: accept[filesystem-envelope-gap]` on line 129. The auditme-adoption
spec's "Out of scope" section says the miss "is raised separately, in the
shared repository's auditme `requests.md`", but on 2026-11-01 that file's
"Open" section says "None".

Cause: the rule resolves `except` clauses by name and does not follow a
module-level tuple constant to its members (suspected from the hit; the
checker code is not read here).

Fix direction: file an entry in the agents repository's
`claude/skills/auditme/requests.md`, where the change is made. Once the
checker resolves module-level exception tuples, remove the accept marker at
`src/ralphlib/verifier.py:129` and check that the rule reports no hit there.

Note 2026-11-01: cause confirmed. `check_filesystem_envelope_gap` in the
agents repository's `claude/skills/auditme/checks/auditme/rules/error_handling.py`
unparses each handler's type and searches the text for `OSError` and its kin,
so `except READ_ERRORS` shows only the name. Filed as "filesystem-envelope-gap
should resolve a module-level exception tuple" under "Open" in that
repository's `claude/skills/auditme/requests.md` (agents `c170c8c`, not yet
pushed). Waiting on that change; then the step above.

Note 2026-11-01: as of 06:56 UTC, agents `c170c8c` is on that repository's
`origin/main`, so the request is visible to other sessions.

Done: 2026-11-01 - agents `76ab65a` ("feat(auditme): resolve exception tuples in handlers") shipped the request; ralpher pins agents at `e7901e6`, and the accept marker in `src/ralphlib/verifier.py` is removed with the whole-tree audit still passing.

## The locked ruff is older than the pre-commit ruff hook

Found on 2026-11-01 while getting CI to pass (`agents/tasks/auditme-adoption/tasks-1.md`
Task 12): the CI audit runs `ruff` from the project's `.venv`, so ruff was
added to the dev group. The pre-commit ruff hook is at `v0.17.3`, but the
`exclude-newer = "14 days"` cooldown in `pyproject.toml` only allowed
`ruff==0.17.1`, which was locked. Both versions passed the tree on
2026-11-01, but a later difference between them would make the commit hook
and the CI audit disagree.

Fix direction: once 0.17.3 clears the cooldown (published 2026-10-27, so
from 2026-11-10), run `uv add --dev ruff==0.17.3` so the locked ruff
matches the hook's `rev`, and keep the two equal whenever either moves.

Note 2026-11-01: agents `e7901e6` adds the `ruff-version-drift` rule, which
fails while the hook's `rev` and the locked ruff differ. To pass it, the
ruff-pre-commit hook was pinned back to `v0.17.1`, the locked version, so the
two match now. Remaining work: from 2026-11-10, raise both together - the
hook's `rev` to `v0.17.3` and `uv add --dev ruff==0.17.3` - in one commit.

Done: 2026-11-01 - `2717f66` pinned the ruff-pre-commit hook to `v0.17.1`, the locked version, and agents' `ruff-version-drift` rule (pinned at `e7901e6`) now fails any commit where the two differ. Raising both to 0.17.3 after the cooldown is routine upkeep.

## The pre-run git checks ignore `--worktree-base-ref`

Found 2026-11-01 while writing the user guide, at `631f6b1`:
`check_repo_clean` (`src/ralphlib/giter.py:87`) and `check_divergence`
(`src/ralphlib/giter.py:163`) take the worktree base ref from
`claude_worktree_base_ref`, which reads only Claude Code's settings files.
`--worktree-base-ref` reaches the agent through `add_settings`
(`src/ralphlib/iteration.py:183`) but never the checks. With
`--worktree-base-ref fresh` and `"baseRef": "head"` in the settings, the
divergence check is skipped and the worktree starts from an `origin` that
lacks the local commits; with the opposite pair, the checks warn about a
divergence that does not matter. `docs/limits.md` records it as a limit.
`add_settings` also builds the `--settings` JSON with `%` formatting,
against the project's f-string rule.

Cause: no single place holds the effective base ref (option first, then
settings); each consumer reads one source.

Fix direction: add one function that returns the effective base ref from
the options and the settings, use it in both checks, build the
`--settings` JSON with `json.dumps`, test both combinations, and drop the
line from `docs/limits.md`.

Done: 2026-11-01 - `worktree_base_ref` in `src/ralphlib/giter.py` gives both pre-run checks the base ref the agent gets, through `RalpherOptions.passed_worktree_base_ref`, which `add_settings` now also uses and which builds its JSON with `orjson`; `TestWorktreeBaseRef`, `TestCheckDivergence` and `TestCheckRepoClean` in `src/tests/test_giter.py` and the `add_settings` tests in `src/tests/test_iteration.py` cover it; `docs/guide/worktrees.md` and `docs/limits.md` updated.

## CI's actions are pinned by tag, not commit

Found 2026-11-01 at `631f6b1`: `.github/workflows/ci.yml:16`, `:22` and
`:25` use `actions/checkout`, `actions/setup-python` and
`astral-sh/setup-uv` by tag. `.github/workflows/docs.yml` pins the same
kind of actions to full commit SHAs, after that day's security review
flagged tags there: a moved tag runs new code in the job without a change
here.

Cause: `ci.yml` predates the pinning in `docs.yml`.

Fix direction: pin each action in `ci.yml` to its commit SHA with the tag
in a trailing comment, as `docs.yml` does.

Done: 2026-11-01 - closed by the operator's decision: workflows pin actions to exact release tags, not commit SHAs. `docs.yml` went back to tags, and the `ci.yml` comment that asked for SHAs now asks for release tags.

## The `agent_process_end` hook event is never fired

Found 2026-11-01 while writing the user guide, at `631f6b1`:
`RalpherEventType.AGENT_PROCESS_END` and its name `agent_process_end` are
defined in `src/ralphlib/types.py:45` and `:58`, but only
`AGENT_PROCESS_START` is sent (`src/ralphlib/iteration.py:452`). A hook set
on `agent_process_end` is accepted and never runs. `docs/guide/hooks.md`
and `docs/reference/variables.md` leave the event out.

Cause: the event was declared alongside `agent_process_start` and its call
was never added.

Fix direction: fire it when the agent process exits, with
`agent_process_id` and the exit status in the context, test it in
`src/tests/test_hooks.py` or `test_iteration.py`, and add it to both docs
pages.

Note 2026-11-01: since the `--worktree-base-ref` fix, `AGENT_PROCESS_START` is
sent at `src/ralphlib/iteration.py:450`.

Done: 2026-11-01 - `process` in `src/ralphlib/iteration.py` fires `agent_process_end` after the agent exits, with `agent_process_id` and `agent_exit_code`; `test_process_fires_agent_process_end_with_exit_code` in `src/tests/test_iteration.py` covers it; `docs/guide/hooks.md` and `docs/reference/variables.md` list the event.

## The `--vars` validation from audit review 2 has no tests

Found on 2026-11-02, reviewing `TODO.md` against the queue log for
`agents/tasks/audit-reviews/tasks-2.md` Task 5 ("Validate `--vars` before the
loop starts"). The agent reported adding tests for a bad format, each reserved
key and good vars in `src/tests/test_templater.py`, and looper tests for
`noequals` and `iteration=3`. Its commit, `a72ca80`, changes no test file, and
on 2026-11-02 nothing under `src/tests/` names `parse_vars`, a reserved key or
the loop refusing bad `--vars`. The tests were most likely written in the
queue's worktree and never staged. The task's subtask to confirm the looper
test fails against the old code was ticked without being run.

`templater.parse_vars` (`src/ralphlib/templater.py`) raises `InvalidVarFormat`
for a value without `=` and for a key `render` sets itself; `looper.loop`
(`src/ralphlib/looper.py`) calls it before the `start` hook.

Fix direction: add the tests the task describes - bad format, each reserved
key and good vars for `parse_vars`, and a `loop` test asserting no `start`
hook, no iteration and a `True` (error) return on bad `--vars` - and confirm
each fails against `a72ca80^`.

Done: 2026-11-02 - tests for `parse_vars` (each built-in key, a value without `=`, good vars) in `src/tests/test_templater.py` and for `loop` refusing bad `--vars` before the `start` hook in `src/tests/test_looper.py`; each targeted test fails with the reserved-key check and the early `parse_vars` call removed.

## The audit summary still lists the findings tasks-2 fixed as unresolved

Found on 2026-11-02, after `agents/tasks/audit-reviews/tasks-2.md` shipped in
merge `8d320ce`. The auditme skill's step 8b says that once a review's task
list ships, `agents/audit-reviews/summary.md` moves the resolved findings from
Unresolved to Recently resolved, and the list's Task 14 Notes repeat it. The
Task 14 agent left it for the merge, and nothing did it.

Fix direction: re-check each Unresolved finding in `summary.md` against the
code (the review-2 locations), move the fixed ones to Recently resolved with
review-2 as the review that raised them, and keep the rest, including the
property-test gaps in the next item.

Done: 2026-11-02 - `agents/audit-reviews/summary.md` re-checked against the code: every review-2 finding fixed by `agents/tasks/audit-reviews/tasks-2.md` moved to Recently resolved; the property-test gaps (Finding 18) and the D2 plugin dependencies (Finding 19) stay unresolved.

## Seven functions from audit review 2's property-test gaps have no property test

Found on 2026-11-02 in the queue log for
`agents/tasks/audit-reviews/tasks-2.md` Task 14. Review-2's T2 question
(Finding 18) lists functions with well-defined input domains and only example
tests. Task 14 added hypothesis tests for eight of them, and its agent
reported that it skipped the rest without recording why none fits, though it
ticked the acceptance criterion:

- `iteration.process_line`, `iteration.process_stream_event`,
  `iteration.input_field_to_content` and `iteration.agent_environment`
  (`src/ralphlib/iteration.py`)
- `templater.render` (`src/ralphlib/templater.py`)
- `logger.log_file` (`src/ralphlib/logger.py`)
- `state.add_to_state` (`src/ralphlib/state.py`, the `key1`/`key2` merge)

Fix direction: add a hypothesis test for each
(`@hypothesis.settings(max_examples=20, deadline=10000)`), with strategies
for the stream-JSON payload shapes shared between `process_line` and
`process_stream_event`; where a property test does not fit, say why in the
test module and add an example test instead.

Done: 2026-11-02 - a hypothesis test for each function: `process_line`, `process_stream_event`, `input_field_to_content` and `agent_environment` in `src/tests/test_iteration.py` (sharing the `STREAM_EVENTS` payload strategy), `render` in `src/tests/test_templater.py`, `log_file` in `src/tests/test_logger.py` and `add_to_state` in `src/tests/test_state.py`; each fails against a planted defect in its function.

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

Done: 2026-11-06 - spec agents/specs/run-order/spec.md amendment 1.1, tasks agents/tasks/run-order/tasks-2.md.

## `rro decisions` drops a `Queue-decision:` line that git does not parse as a trailer

Found on 2026-11-09, at the final checkpoint of an order in another project:
`bin/rro.sh decisions <order> --since <ref>` printed `[]`, while
`git log --grep '^Queue-decision:' <ref>..main` listed the one decided stop.
Three of the six `Queue-decision:` commits on that project's default branch
had the same shape.

Cause: `decisions_since` (`src/ralphlib/order.py`) selects commits with
`--grep=^Queue-decision:` but reads the value with
`%(trailers:key=Queue-decision,valueonly)`, and git parses trailers only in a
message's last paragraph. The missed commits put a blank line between the
`Queue-decision:` line and `Co-Authored-By:`, so the grep matched, the trailer
parser returned nothing, and the `if task.strip()` check dropped the commit
without a word. Removing the blank line makes `git interpret-trailers --parse`
find it. The missed commit was a task's own commit made by the queue agent,
with a free-text value ("sites S1, S3 and S4 change; ..."), not the
`<task list path> Task <N>` that `claude/commands/rrq.md` step 4 asks the
session for.

Fix direction: in `decisions_since`, take the value from the body's
`^Queue-decision:` line when the trailer parser returns nothing, or raise an
error naming each commit the grep matched and the parser did not, so a batch
review is never published empty by mistake. Add a test with the blank-line
shape beside `test_decisions_since_filters_and_orders`
(`src/tests/test_order.py`). Consider saying in `rrq.md` that the line goes in
the message's last paragraph, beside the other trailers. Small; no spec.

Done: 2026-11-09 - `decisions_since` in `src/ralphlib/order.py` reads the value from every `^Queue-decision:` line in the message instead of the trailer parser; test `test_decisions_since_reads_a_line_outside_the_last_paragraph` in `src/tests/test_order.py`; `claude/commands/rrq.md` step 4 puts the line in the last paragraph.

## `claude-review` fails on every Dependabot pull request

Found on 2026-11-21 by a survey: the `claude-review` job of
`.github/workflows/claude-code-review.yml` fails on all five open Dependabot
pull requests with `Workflow initiated by non-human actor: dependabot (type:
Bot). Add bot to allowed_bots list or use '*' to allow all bots.` (run
43683071806, 2026-11-15).

Cause: the job's `if:` condition is commented out
(`.github/workflows/claude-code-review.yml:16`), so the review starts for bot
pull requests, which the action refuses.

Fix direction: skip the job for Dependabot (`if: github.actor !=
'dependabot[bot]'`) rather than allowing bots, so a dependency bump spends no
review. Small; no spec.

Done: 2026-11-21 - the `claude-review` job in `.github/workflows/claude-code-review.yml` now runs only when the pull request's author is not `dependabot[bot]`; not yet seen in a pull request run.

## CI's `check` job fails on every Dependabot pull request

Found on 2026-11-21 by a survey: `check` fails on all five open Dependabot
pull requests (#21, #22, #24, #25, #26) with `Load key
"/home/runner/.ssh/agents_deploy_key": error in libcrypto` and `Permission
denied (publickey)` when pre-commit fetches the audit hooks (runs of
2026-11-15, e.g. run 43683071813).

Cause: a workflow run that Dependabot triggers reads Dependabot secrets, not
Actions secrets. `gh secret list --app dependabot` lists none, while the
deploy key is set only as the Actions secret `AUDITOR_DEPLOY_KEY`, which
`.github/workflows/ci.yml:48` writes to `~/.ssh/auditor_deploy_key`. The
failed runs predate the move to the auditor repository, but a rebased pull
request meets the same empty secret.

Fix direction: the operator adds the auditor deploy key as a Dependabot
secret named `AUDITOR_DEPLOY_KEY` (repository settings, Secrets and
variables, Dependabot); only the operator holds the key. Then ask Dependabot
to rebase each open pull request (`@dependabot rebase`) and check that
`check` passes. Small; no spec.

Note 2026-11-21: at 15:42 UTC a new read-only deploy key (`ralpher ci`, id
`170673638`) was added to `bnomis/auditor`, its private half set as
`AUDITOR_DEPLOY_KEY` for both Actions and Dependabot, and the old key
(`170651006`) deleted. As of 15:43 UTC no open Dependabot pull request had
run CI since, so the rebase and the check that `check` passes remain.

Done: 2026-11-21 - the Dependabot secret `AUDITOR_DEPLOY_KEY` (deploy key `170673638`); after `@dependabot rebase` at 15:49 UTC, `check` fetched the audit hooks on #21, #24, #25 and #26 and passed on #21, #25 and #26 (#24 fails on `ruff-version-drift`, the next item); #22 had not been rebased as of 15:58 UTC.

## Merging the ruff 0.17.3 bump would fail the push hook

Found on 2026-11-21 by a survey: Dependabot pull request #24 moves ruff from
0.17.2 to 0.17.3 in `pyproject.toml` and `uv.lock` only, while
`.pre-commit-config.yaml:4` pins the `ruff-pre-commit` hook at `rev:
v0.17.2`.

Cause: the audit's `ruff-version-drift` check compares the ruff in `.venv`
with that `rev` and reports any difference, so once the lock holds 0.17.3
the `auditme-all` push hook and CI fail until the `rev` matches.
`.pre-commit-config.yaml` is under "Do not modify" in `AGENTS.md`.

Fix direction: with the operator's go-ahead to edit `.pre-commit-config.yaml`,
raise the `rev` to `v0.17.3` in the same change that merges #24 (push a
commit to the Dependabot branch, or take the bump on `main` by hand and close
the pull request). Waits on the `check` item above for #24's own CI. Small;
no spec.

Note 2026-11-21: the `check` item is done (see `DONE.md`). #24, rebased at
15:49 UTC, now fails only here: run 44921408958 reports `ruff-version-drift`
at `.pre-commit-config.yaml:4`.

Done: 2026-11-21 - #24 was retargeted to ruff 0.17.4 when rebased; `pyproject.toml`, `uv.lock` (via `uv lock`) and the `ruff-pre-commit` `rev` in `.pre-commit-config.yaml` all moved to 0.17.4 together on branch `build/ruff-0.17.4`, matching #24's lock exactly, with the operator's go-ahead to edit `.pre-commit-config.yaml`; `pre-commit run --all-files` and the `auditme-all` push hook pass.
