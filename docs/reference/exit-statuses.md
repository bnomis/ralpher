# Exit statuses

| Status | When | Exit reason |
|--------|------|-------------|
| 0 | the agent printed a stop marker that passed the verified stop | `complete` |
| 0 | every iteration ran without a stop | `completed all iterations` |
| 0 | `--help`, `--cleanup` | |
| 1 | the agent reported an error result | `error` |
| 1 | an exception inside ralpher during an iteration | `exception during iteration <n>` |
| 1 | Ctrl+C twice, `SIGTERM`, an `operator` task block, or a loop on a blocked task | `termination` |
| 1 | a signal during shutdown | none: ralpher exits at once |
| 1 | a ralpher error before the first iteration: an unreadable or invalid settings file, an invalid `--args`, a `--cwd` that cannot be entered, a log directory that cannot be created, a `--state` path outside the log directory | none: ralpher prints `Error: ...` |
| 1 | a pre-run check you answered "no" to, a missing or empty prompt or tasks file, an invalid `--vars` | none: ralpher stops before the first iteration and prints why |

When several apply in one iteration, the exit reason joins them, such as
`complete, termination`, and the status is 1 if any is `error` or
`termination`.

The exit reason is printed as `Exit reason:` at the end of the run, stored
in the [state file](../guide/logs.md#the-state-file), and given to the `end`
and `error` hooks as `{{exit_reason}}`. A termination also prints
`Stopping reason:` with its cause.
