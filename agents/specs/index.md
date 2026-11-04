# Spec Index

| Spec | Path | Description |
|------|------|-------------|
| [Verified stop](verified-stop/spec.md) | `src/ralphlib/verifier.py` | Check a stop marker against the tasks file before ending the loop |
| [Auditme adoption](auditme-adoption/spec.md) | `src/ralphlib/`, `src/tests/`, `.pre-commit-config.yaml` | Clear every auditme hit and gate commits, pushes and CI on the checker |
| [Run order](run-order/spec.md) | `claude/commands/rro.md`, `src/ralphlib/order.py` | Run an order of task lists: queue each, merge, checkpoint, batch-review decided stops |
