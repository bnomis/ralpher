Run a ralpher queue in the background and report only when it has finished.

Run this command with `run_in_background` set to true:

    $RALPHER_PATH/bin/rrq.sh $ARGUMENTS

Then stop. Do not read, tail, grep or otherwise consume the output file
while the command runs - none of its content should enter the conversation,
however long it takes or however curious the wait becomes. Do not poll for
completion either: the harness re-invokes you when the process exits, so a
check-in loop only burns tokens.

When it completes, show the last 100 lines of the output file and nothing
else. If it exited non-zero, say so alongside those lines rather than
investigating - the tail is what was asked for, and the next instruction is
the user's to give.
