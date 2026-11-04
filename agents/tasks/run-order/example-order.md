# Order: example

An order of three task lists. Text outside the two tables is kept as written.

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
