# Settings

Settings are JSON objects read from files. None is required.

## Files

Read in this order; a later file's keys win:

1. built-in defaults (the [theme](../guide/terminal.md#themes) only);
2. `~/.ralpher/settings.json`;
3. `.ralpher/settings.json` in the `--cwd` directory, only when `--cwd` is
   given (the wrapper scripts give it);
4. `--settings-file FILE`.

The `.ralpher/settings.json` in the `--cwd` repository can define
[hooks](../guide/hooks.md), which run as commands, so run ralpher only on
repositories you trust.

A file that does not exist is skipped. A file that is not valid JSON stops
the run.

Settings are read once, before the first iteration, or before every
iteration with `--load-settings-on-loop`.

## How files are merged

Each file's top-level keys replace the same keys from earlier files; nested
objects are not merged. A project file with a `hooks` object replaces your
user file's `hooks` entirely, and a `theme` with one key replaces the whole
default theme.

## Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `hooks` | object: event name to list of command strings | none | Commands to run on events. See [Hooks](../guide/hooks.md). |
| `hook_templates` | boolean (`true` or `false`, not a string) | `true` | Render hook commands as Jinja templates. |
| `hook_icon` | string (template) | none | A file path offered to hooks as `{{hook_icon}}`. |
| `hook_sound` | string (template) | none | A sound name or path offered to hooks as `{{hook_sound}}`. |
| `worktree_setup` | list of strings | none | Commands the agent runs in the worktree before anything else, with `--worktree`. Each must be safe to repeat. See [Giving the worktree an environment](../guide/worktrees.md#giving-the-worktree-an-environment). |
| `theme` | object: message kind to Rich style | see [Themes](../guide/terminal.md#themes) | Terminal colours and styles. |

Unknown keys are ignored.

## Example

`~/.ralpher/settings.json`, for macOS notifications with
[alerter](https://github.com/vjeantet/alerter):

```json
{
  "hook_icon": "{{ralpher_root}}/img/ralpher.jpg",
  "hooks": {
    "start": [
      "alerter --app-icon '{{hook_icon}}' --title '{{cwd_basename}} {{task_file_dir_basename}} start' --message 'max iterations {{iterations}}'"
    ],
    "end": [
      "alerter --app-icon '{{hook_icon}}' --title '{{cwd_basename}} {{task_file_dir_basename}} done' --message '{{exit_reason}} {{iterations_completed}}/{{iterations}} {{total_time_readable}}' --sound Funky"
    ],
    "error": [
      "alerter --app-icon '{{hook_icon}}' --title '{{cwd_basename}} {{task_file_dir_basename}} error' --message '{{exit_reason}}' --sound Funky"
    ]
  },
  "theme": {
    "alert": "bold red",
    "content_delta": "cyan",
    "default": "grey30",
    "error": "red",
    "progress": "bold yellow",
    "regular": "grey30",
    "system": "yellow",
    "tool_use": "magenta"
  }
}
```
