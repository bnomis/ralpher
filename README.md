# ralpher

A ralph loop.

More ralph.

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
            "/opt/homebrew/bin/alerter --title 'ralpher done' --message 'End! {{iteration}}/{{iterations}} {{total_time_seconds}}s {{total_time_readable}}' --sound Funky"
        ],
        "error": [
            "/opt/homebrew/bin/alerter --title 'ralpher error' --message 'Error! {{iteration}}/{{iterations}}' --sound Funky"
        ],
        "iteration_end": [
            "/opt/homebrew/bin/alerter --title 'ralpher' --message 'Loop End! {{iteration}}/{{iterations}} {{iteration_time_seconds}}s {{iteration_time_readable}}'"
        ],
        "iteration_start": [
            "/opt/homebrew/bin/alerter --title 'ralpher loop {{iteration}}/{{iterations}}' --message 'Loop Start! {{iteration}}/{{iterations}}'"
        ],
        "start": [
            "/opt/homebrew/bin/alerter --title 'ralpher start' --message 'Start! {{iteration}}/{{iterations}}'"
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
