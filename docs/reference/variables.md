# Template variables

Prompts and hook commands are Jinja templates with different variables.

## Prompts

Rendered before each iteration. See [Prompts](../guide/prompts.md).

| Variable | Value |
|----------|-------|
| `iteration` | this iteration's number, from 1 |
| `iterations` | `--iterations` |
| `task_file` | absolute path of the tasks file; empty without one |
| `task_file_relative_path` | the tasks file relative to `--cwd` when inside it, else absolute; empty without one |
| `worktree` | boolean: `--worktree` given |
| `worktree_name` | the worktree name, with `--worktree` and `--task-file`; else empty |
| each `--vars` key | its value; replaces a built-in of the same name |

## Hooks

Rendered when the hook runs, in a sandbox. Values are strings. See
[Hooks](../guide/hooks.md).

### Every event

| Variable | Value |
|----------|-------|
| `event_type` | the event name, such as `iteration_end` |
| `iterations` | `--iterations` |
| `current_iteration` | the iteration running, or 0 |
| `iteration_count` | iterations finished so far |
| `datetime_utc` | now, ISO 8601, ending `Z` |
| `datetime_local` | now, ISO 8601 with offset |
| `time_epoch` | now, whole seconds since the epoch |
| `cwd` | absolute `--cwd`; empty without it |
| `cwd_basename`, `cwd_dirname` | its last component, and its parent |
| `task_file` | absolute path of the tasks file; empty without one |
| `task_file_relative_path` | relative to `--cwd` when inside it |
| `task_file_basename` | `tasks-1.md` |
| `task_file_stem` | `tasks-1` |
| `task_file_suffix` | `.md` |
| `task_file_dirname` | the directory holding it |
| `task_file_dir_basename` | that directory's name, such as `config-loader` |
| `task_file_number` | the number after the last `-` in the stem, such as `1`; empty if none |
| `last_commit_summary` | the subject of the last commit in the `--cwd` repository |
| `ralpher_root` | ralpher's checkout |
| `hook_icon`, `hook_sound` | from [settings](settings.md#keys), when set |

### Per event

| Event | Variables |
|-------|-----------|
| `start` | `iteration` (`0`), `prompt` |
| `iteration_start` | `iteration`, `prompt` (rendered) |
| `agent_process_start` | `agent_process_id` |
| `agent_process_end` | `agent_process_id`, `agent_exit_code` |
| `llm_task_progress` | `task_id`, `task_title`, `task_index`, `task_count`, `task_status` |
| `iteration_end` | `iteration`, `iteration_time_readable`, `iteration_time_seconds` |
| `end`, `error` | `iteration` (`0`), `exit_reason`, `iterations_completed`, `total_time_readable`, `total_time_seconds` |

### Filters

| Filter | `{{ "/a/b/tasks-1.md" \| filter }}` |
|--------|-------------------------------------|
| `basename` | `tasks-1.md` |
| `dirname` | `/a/b` |
| `stem` | `tasks-1` |
| `suffix` | `.md` |
