# Terminal output

## What a run prints

1. A banner: start time, agent, arguments, the unrendered prompt, iterations.
2. For each iteration: the rendered prompt; then, as the agent works, its
   streamed text, each tool call with its main input, and task progress
   lines; then the tools used; then the end time and duration.
3. At the end: each iteration's duration, the total time, the loop time and
   overhead when the overhead is a second or more, the exit reason, and
   either the cleanup commands or a suggested next prompt.

Agent stderr is printed in the `error` style as it arrives.

## Lines worth watching for

| Line | Meaning |
|------|---------|
| `task 3: Read settings from TOML 3/7 start` | a task started (`done`, `blocked`, `operator` likewise) |
| `===== Loop complete signal received, stopping after 7 iterations. =====` | the run is ending; the word is the exit reason |
| `===== Loop complete signal rejected, 3 of 7 tasks not done =====` | a stop marker failed the [verified stop](tasks.md#verified-stop) |
| `Probable cleanup commands...` | see [After the queue](worktrees.md#after-the-queue) |
| `Probable next prompt...` | the run stopped for you; paste the prompt into an interactive session |

To follow a queue from another program, filter the progress file, or
ralpher's stdout, with
`grep -E '^task [0-9]+|^=+ Loop .* signal (received|rejected)'`.

## Themes

Each line is printed in a style chosen by its kind. Set the styles under
`theme` in [settings](../reference/settings.md), as
[Rich style strings](https://rich.readthedocs.io/en/stable/style.html):

```json
{
  "theme": {
    "alert": "bold red",
    "content_delta": "cyan",
    "default": "grey30",
    "error": "red",
    "progress": "yellow",
    "regular": "grey30",
    "system": "yellow",
    "tool_use": "magenta"
  }
}
```

These are the defaults.

| Key | Used for |
|-----|----------|
| `alert` | signal handling: Ctrl+C, shutdown, the pre-run prompts |
| `content_delta` | the agent's streamed text |
| `error` | agent stderr, error results, the loop-end line after an error |
| `progress` | task progress lines |
| `regular` | ralpher's own messages: banners, prompts, times |
| `system` | ralpher and agent system messages, such as `Started agent process`; the loop-end and rejection lines |
| `tool_use` | tool calls |
| `default` | any kind with no key of its own |

A `theme` in a settings file replaces the whole default theme, not single
keys, so give every key you care about; the rest fall back to `default`, then
to `grey30`. See [how settings are merged](../reference/settings.md#how-files-are-merged).
