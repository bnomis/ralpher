# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

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

Spec: agents/specs/auditme-adoption/spec.md; tasks: not yet written.

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
