# Logs and state

Nothing is written unless you ask for it. Each option names a file; with
`--logdir DIR`, the names are relative to `DIR`, which is created if
missing.

| Option | Holds | Per iteration |
|--------|-------|---------------|
| `--stdout FILE` | the agent's raw stdout, one JSON object per line | yes |
| `--stderr FILE` | the agent's raw stderr | yes |
| `--progress FILE` | everything ralpher prints, as plain text | yes, plus a run file |
| `--errors FILE` | lines ralpher could not parse, and parse exceptions | yes |
| `--state FILE` | one JSON document for the whole run | no |

```shell
ralpher.sh ... --logdir ralpher-logs/config-loader/tasks-1 \
  --stdout stdout.jsonl --stderr stderr.jsonl --progress progress.log \
  --errors errors.log --state state.json
```

## File names

Per-iteration files get the iteration number before the extension, padded to
the width of `--iterations`: with `--iterations 20`, `progress.log` becomes
`progress-01.log` to `progress-20.log`. The progress file for the run as a
whole, with the start banner, loop times and exit reason, is `progress-00.log`.

If a file of that name already exists, ralpher adds `-1`, `-2` and so on
rather than overwriting it, so rerunning a queue into the same `--logdir`
keeps every earlier run: `progress-01.log` is the first run's iteration 1,
`progress-01-1.log` the second run's.

The state file is not numbered: a rerun with the same `--state` adds to the
same JSON document.

`--quiet` stops ralpher printing to the terminal; the progress file is still
written.

## The state file

`state.json` is rewritten after each change, under a lock file
(`state.json.lock`) beside it.

```json
{
  "agent": "claude",
  "args": "--verbose --include-partial-messages --print ...",
  "prompt": "...",
  "max_iterations": 20,
  "start": "2026-11-01T09:12:03.418772",
  "end": "2026-11-01T10:40:51.009311",
  "exit_reason": "complete",
  "stopping_reason": "",
  "iterations_completed": 7,
  "total_time_readable": "1 hour 28 minutes 47 seconds",
  "total_time_seconds": 5327.59,
  "loop_time_readable": "1 hour 28 minutes 33 seconds",
  "loop_time_seconds": 5313.2,
  "overhead_time_readable": "14 seconds",
  "overhead_time_seconds": 14.39,
  "iterations": {
    "01": {
      "start": "2026-11-01T09:12:05.102934",
      "end": "2026-11-01T09:25:40.551203",
      "iteration_time_readable": "13 minutes 35 seconds",
      "iteration_time_seconds": 815.45,
      "tools_used": ["Bash", "Edit", "Read"],
      "stop_rejected": {"total": 7, "not_done": [5, 6, 7]}
    }
  }
}
```

| Key | Meaning |
|-----|---------|
| `exit_reason` | `complete`, `error` or `termination`, joined with `, ` when several apply, or `completed all iterations` |
| `stopping_reason` | why a termination happened, such as `Operator input required for task 4`; empty otherwise |
| `overhead_time_*` | run time outside the agent processes: checks, hooks, startup |
| `iterations.<n>.tools_used` | tool names the agent called |
| `iterations.<n>.unknown_tools` | tools called with an input ralpher could not summarise |
| `iterations.<n>.unknown_ptypes` | stream line types ralpher did not recognise |
| `iterations.<n>.stop_rejected` | a stop marker the [verified stop](tasks.md#verified-stop) rejected: task count and the numbers of tasks not done |

Times are local, without a timezone.

## Using the logs

- The stdout log is the agent's own record: replay it with `jq` to see the
  full tool inputs and results that the terminal shortens.
- Search the run's progress file for `Exit reason:` to see how a run ended.
- `errors-<n>.log` is empty in a healthy run; lines there usually mean the
  agent's output format changed. See [Limits](../limits.md).
