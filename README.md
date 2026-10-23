# ralpher

A ralph loop.

More ralph.

## Verified stop

When the agent prints a completion marker, ralpher stops the loop. With `--task-file`, ralpher first checks the tasks file, and ignores the marker while any task is not done:

```shell
ralpher.sh --task-file agents/tasks/my-feature/tasks-1.md ...
```

- The check passes when every `**Status:**` line in the tasks file is `done`. Task-shaped examples inside fenced code blocks are ignored.
- With `--worktree`, ralpher reads the copy of the tasks file inside the agent's worktree (branch `worktree-<name>`), never the copy in the main checkout.
- On rejection ralpher prints `===== Loop complete signal rejected, <n> of <m> tasks not done =====`, lists the unfinished tasks, records `stop_rejected` for the iteration in `state.json`, and carries on with the next iteration. A rejection on the last iteration ends the loop with the exit reason `completed all iterations`.
- If the check cannot be made (file missing, unreadable, no tasks found, worktree not found), ralpher trusts the marker, logs a warning and stops.

`--no-verify-stop` (default: off) skips the check and stops on any marker. Use it when the tasks file does not follow the `## Task <n>: <title>` and `**Status:** <status>` format. The trade-off is that one premature marker from the agent ends the whole queue.

Without `--task-file` the check never runs.

## The agent's environment

The agent starts with the environment ralpher was started with, minus ralpher's own Python: `bin/activate.sh` puts ralpher's `.venv` on `PATH` and its `src` on `PYTHONPATH`, and ralpher removes both, and `VIRTUAL_ENV` when it names that `.venv`, before starting the agent. So `python` and `pytest` in the agent's shell are whatever the project's own setup provides (its `bin/activate.sh`, or the user's `PATH`), never ralpher's packages. Any other virtual environment active when ralpher started is kept.

## Configuration

ralpher will read the file `~/.ralpher/settings.json` if it exists.

Below is an example of such a file.

For an explanation of the contents see:

- [Hooks](#hooks)
- [Colours](#colours)

```json
{
  "hook_templates": true,
  "hooks": {
    "end": [
      "/opt/homebrew/bin/alerter --app-icon {{ralpher_root}}/img/ralpher.jpg --title '{{cwd|basename}} {{task_file|dirname|basename}} done' --message '{{exit_reason}} {{iteration}}/{{iterations}} {{total_time_readable}}' --sound Funky"
    ],
    "error": [
      "/opt/homebrew/bin/alerter --app-icon {{ralpher_root}}/img/ralpher.jpg --title '{{cwd|basename}} {{task_file|dirname|basename}} error' --message '{{exit_reason}} {{iteration}}/{{iterations}}' --sound Funky"
    ],
    "iteration_end": [
      "/opt/homebrew/bin/alerter --app-icon {{ralpher_root}}/img/ralpher.jpg --title 'r{{cwd|basename}} {{task_file|dirname|basename}} loop end' --message '{{iteration}}/{{iterations}} {{iteration_time_readable}}'"
    ],
    "iteration_start": [
      "/opt/homebrew/bin/alerter --app-icon {{ralpher_root}}/img/ralpher.jpg --title '{{cwd|basename}} {{task_file|dirname|basename}} loop start' --message '{{iteration}}/{{iterations}}'"
    ],
    "start": [
      "/opt/homebrew/bin/alerter --app-icon {{ralpher_root}}/img/ralpher.jpg --title '{{cwd|basename}} {{task_file|dirname|basename}} start' --message 'Start! max iterations {{iterations}}'"
    ]
  },
    "theme": {
        "alert": "bold red",
        "content_delta": "cyan",
        "default": "grey30",
        "error": "red",
        "regular": "grey30",
        "system": "yellow",
        "tool_use": "magenta"
    }
}
```

## Hooks

The following hook events are supported:

- 'start': ralpher started
- 'iteration_start': an iteration started
- 'iteration_end': an iteration ended
- 'end': ralpher ended, either got the complete signal, or finished iterations
- 'error': ralpher ended with an error

## Hooks as templates

To include some context in your hooks they can be preprocessed as Jinja templates before being run. Use the `hook_templates` setting to turn this functionality on/off.

Context values are substituted after the command has been split into arguments, so you never need to escape them. A value containing quotes, spaces or newlines lands in exactly one argument -- a task title such as `Give each project's config.py a module name` will not break the command or split into several arguments. Quote your templates for readability if you like; the quoting applies to the template, not to the values.

The available context is:

```json
{
    'event_type': type of the event see above
    'iteration': the current iteration number, will be zero if not in an iteration
    'iterations': total number of iterations
    'datetime_utc': datetime in utc timezone
    'datetime_local': datetime in local timezone
    'prompt': the prompt
    'time_epoch': time since epoch
    'task_file': the task file (if in use)
}
```

At the end of an iteration additional context variables are available:

```json
{
    'iteration_time_readable': a readable iteration duration
    'iteration_time_seconds': iteration duration in seconds
}
```

When ralpher ends the following context variables are available:

```json
{
    'exit_reason': readable exit reason
    'iterations_completed': number of iterations completed
    'total_time_readable': readable total duration
    'total_time_seconds': total duration in seconds
}
```

## Colours

The colours and styles of messages printed to the terminal can be controlled by the "theme" key in `settings.json`.

The theme colours and styles are [rich style strings](https://rich.readthedocs.io/en/stable/style.html).

The printed messages will be one of:

```json
{
    "alert": e.g. you hit ctrl-c, shutdown
    "content_delta": streamed messages
    "default": default, fallback
    "error": e.g. run out of usage
    "regular": regular messages
    "system": e.g. "Started agent process"
    "tool_use": e.g. "Read, Edit, Write, Bash"
}
```
