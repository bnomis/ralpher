Run a ralpher queue in the background, relay task progress as it happens,
and report in full only when it has finished.

Before any /rrq, check pwd; if it is a worktree, prefix the command with cd to the main checkout.

Run this command with `run_in_background` set to true:

    $RALPHER_PATH/bin/rrq.sh $ARGUMENTS

Note the output file path the background task reports, then start a
`Monitor` on it with `timeout_ms` set to 1800000, the description
`ralpher task progress`, and this command, with `<output-file>` replaced
by that path:

    tail -n +1 -F "<output-file>" | grep -E --line-buffered '^task [0-9]+|^=+ Loop .* signal (received|rejected)' | { n=$(cat "<output-file>.seen" 2>/dev/null || echo 0); i=0; while IFS= read -r line; do i=$((i+1)); if [ "$i" -gt "$n" ]; then printf '%s\n' "$line"; echo "$i" > "<output-file>.seen"; fi; done; }

The last stage records in `<output-file>.seen` how many lines it has
delivered, so a restarted monitor delivers only lines it has not
delivered before. It is a shell `read` loop, not `awk`, because `mawk`
(which some systems install as `awk`) buffers piped input in
blocks: the few short progress lines never fill a block, so an `awk`
stage delivers nothing until the queue ends.

Then stop. The monitor's filtered lines are the only output that may
enter the conversation. Do not read, tail, grep or otherwise consume the
output file yourself while the command runs, however long it takes or
however curious the wait becomes. Do not poll for completion either: the
harness re-invokes you when the process exits, so a check-in loop only
burns tokens.

When a monitor event arrives, relay each new line as one short line and
nothing else:

- a `task …` line → `▶` for `start`, `✓` for `done`, `✗` for `blocked`,
  `?` for `operator` (the queue needs the operator's input), then the
  task position and title, for example `✓ 3/12 Add SearchBatch dataclass`.
  A line with no status, such as `task 1 of 4: add the compress config
  setting`, is shown as `▶ 1/4 add the compress config setting`
- `===== Loop <reason> signal received, … =====` → `■ loop <reason>`
- `===== Loop complete signal rejected, <n> of <m> tasks not done =====` →
  `■ loop complete rejected, <n> of <m> tasks not done`

Skip a `task` line identical to the previous one. Do not comment on,
investigate or act on an event.

If the monitor expires while the background command is still running,
start it again with the same command and say nothing at all: no
"monitor restarted", no summary of progress so far. The restarted
monitor delivers only new lines, so relay each event it delivers as
above.

When the background command completes, stop the monitor with `TaskStop`
if it is still running, then show the last 100 lines of the output file
and nothing else. If it exited non-zero, say so alongside those lines
rather than investigating - the tail is what was asked for, and the next
instruction is the user's to give.
