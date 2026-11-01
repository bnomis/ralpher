Run a ralpher queue in the background, relay task progress as it happens,
and report in full only when it has finished.

Before any /rrq, check pwd; if it is a worktree, prefix the command with cd to the main checkout.

Invoke as `/rrq [--decide] <spec> <index>`. `--decide` is this command's
own option, not the script's: take it out of the arguments, and run the
script with the rest. Without it, a stop for the operator ends the run and
waits for the user, as below; with it, you decide the stop yourself (see
Deciding operator stops, at the end).

Run this command with `run_in_background` set to true, where `<spec>` and
`<index>` are the arguments left once `--decide` is taken out:

    $RALPHER_PATH/bin/rrq.sh <spec> <index>

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
instruction is the user's to give. With `--decide`, an operator stop is the
exception: see below.

Show means paste: read the lines with a tool, then copy them verbatim into
your reply inside a code block. The user does not see tool output, so a
reply that only points at it ("the lines are above") shows them nothing.

## Deciding operator stops (`--decide`)

Only when the user passed `--decide`, and only when the tail's stopping
reason is a task stopped for the operator ("Operator input required for task
<N>"); any other exit is reported as above. Paste the tail first, then:

1. Read the stop: the task's subtasks, the stop condition it met, and the
   evidence the queue's agent recorded in the queue's worktree. Check that
   evidence against the code or the committed files, not only the agent's
   summary.
2. Decide. Take the option the spec, review or task list recommends where
   it names one; otherwise make the call yourself and give the reason. A
   decision covers only the case the stop named.
3. Record it in the worktree where the stop's own record lives (the spec
   section, the review document's Answers section, the task's Notes), dated
   and marked "decided by Claude, not yet reviewed". Tick the subtasks it
   completes and set the task's status.
4. Commit it in the worktree with the trailer
   `Queue-decision: <task list path> Task <N>`, so the user can find every
   such decision later with `git log --grep '^Queue-decision:'`.
5. Tell the user in two or three lines what you decided and why, naming the
   task in plain words, then run this command again with the same arguments,
   `--decide` included.

Do not decide, and wait for the user instead, when the stop:

- asks for work only the user can do (labelling data, a step the task says
  the operator does by hand);
- would spend money, change a licence or commercial-use position, delete
  data, or edit `.envrc` or another file holding secrets;
- has evidence that contradicts every option offered, so any choice would
  stretch a decision past the cases it named.

The project's own rules may add to these exceptions, and say when and where
the user reviews the decisions; follow them.

