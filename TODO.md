# TODO

Open work only, in implementation order, nearest first. Finished items move to
`DONE.md` unchanged. See the shared `todo-add` and `todo-review` skills for
the shape of an item.

## The auditme checker's 2026-10-31 rules report hits here

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
