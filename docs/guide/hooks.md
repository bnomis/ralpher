# Hooks

A hook is a command ralpher starts when something happens in a run: a
desktop notification when a queue finishes, a chat message when a task is
blocked. Hooks are set in [settings](../reference/settings.md) under `hooks`,
as a list of commands per event:

```json
{
  "hooks": {
    "end": [
      "terminal-notifier -title '{{cwd_basename}} {{task_file_dir_basename}}' -message '{{exit_reason}} after {{iterations_completed}}/{{iterations}}, {{total_time_readable}}'"
    ],
    "llm_task_progress": [
      "terminal-notifier -title '{{cwd_basename}}' -message 'task {{task_id}} {{task_status}}: {{task_title}}'"
    ]
  }
}
```

!!! warning
    Hooks run as commands. The `.ralpher/settings.json` in the `--cwd`
    repository can define them, so run ralpher only on repositories you trust.

## Events

| Event | When | Extra variables |
|-------|------|-----------------|
| `start` | after the pre-run checks, before the first iteration | `iteration` (0), `prompt` (unrendered) |
| `iteration_start` | before an iteration's agent starts | `iteration`, `prompt` (rendered) |
| `agent_process_start` | the agent process has started | `agent_process_id` |
| `agent_process_end` | the agent process has exited, or ralpher has stopped it | `agent_process_id`, `agent_exit_code` (negative when a signal ended it; `None` if it was still running after ralpher tried to stop it) |
| `llm_task_progress` | a task progress line: a `<task>` block, or a task newly marked `in-progress` | `task_id`, `task_title`, `task_index`, `task_count`, `task_status` |
| `iteration_end` | after an iteration's agent has exited | `iteration`, `iteration_time_readable`, `iteration_time_seconds` |
| `error` | the run ended with an error, before `end` | as `end` |
| `end` | the run ended, for any reason | `iteration` (0), `exit_reason`, `iterations_completed`, `total_time_readable`, `total_time_seconds` |

Every event also gets the variables in
[Template variables](../reference/variables.md#hooks).

## How a hook runs

- The command is split into arguments as a POSIX shell would
  (`shlex.split`) and started directly, not through a shell: no pipes,
  redirection or `$VAR` expansion. For those, call `sh -c '...'`.
- It starts in its own session, with stdout and stderr discarded, and
  ralpher does not wait for it. A hook that fails to start is logged and
  ignored.
- An event with the same type and the same values runs its hooks once per
  run, so a task block the agent repeats does not notify twice.

## Templates

With `hook_templates` set to `true` (the default), each command is a
[sandboxed](https://jinja.palletsprojects.com/en/stable/sandbox/) Jinja
template, rendered with the event's variables.

Values are substituted after the command has been split into arguments, so
you never escape them. A value containing quotes, spaces or newlines lands
in exactly one argument: a task title such as
`Give each module's config a name` neither breaks the command nor splits it.
Quote the template for readability if you like; the quoting applies to the
template, not to the values.

Four filters work on paths: `basename`, `dirname`, `stem` and `suffix`.

```jinja
{{ task_file | dirname | basename }}   {# config-loader #}
{{ task_file | stem }}                 {# tasks-1 #}
```

With `hook_templates` set to `false`, the command is split and run as
written.

## Icons and sounds

Two settings give notification hooks a shared icon and sound:

| Setting | Becomes | Notes |
|---------|---------|-------|
| `hook_icon` | `{{hook_icon}}` | a template for a file path; set only if the file exists, otherwise a warning is logged |
| `hook_sound` | `{{hook_sound}}` | a template; a sound name, or a path (a value containing `/`), which is warned about if missing |

```json
{
  "hook_icon": "{{ralpher_root}}/img/ralpher.jpg",
  "hook_sound": "Glass",
  "hooks": {
    "end": ["alerter --app-icon '{{hook_icon}}' --sound '{{hook_sound}}' --title '{{cwd_basename}}' --message '{{exit_reason}}'"]
  }
}
```

## Changing hooks during a run

Settings are read once at the start. With `--load-settings-on-loop` they are
read again before each iteration, so an edit to a settings file takes effect
from the next iteration.
