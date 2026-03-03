#!/usr/bin/env bash
set -uoe pipefail
THIS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# shellcheck disable=SC1091
source "$THIS_DIR/activate.sh"

parent=$(dirname "$THIS_DIR")

usage() {
    cat <<EOF
Usage: $(basename "$0") ITERATIONS PROMPT LOGDIR [TASKS]

Arguments:
  ITERATIONS      number of iterations
  PROMPT          prompt file (e.g., PROMPT.md)
                  prompt file will be processed with Jinja2
                  {{iteration}} will be substituted with the current iteration number (starting from 1)
                  {{task_file}} will be substituted with the value of TASKS, if provided
  LOGDIR          directory to hold logs and state (will be created if it doesn't exist)
  TASKS           value substituted into prompt as {{task_file}} (e.g., tasks.txt),
                  if your prompt doesn't use {{task_file}} you can pass any string here
                  you can also omit this argument if your prompt doesn't use {{task_file}}

Note: You must set the RALPHER_PATH env var, so this script knows where to find ralpher.
EOF
    exit 1
}

if [ $# -ne 3 ] && [ $# -ne 4 ]; then
    usage
fi

if [[ -z $RALPHER_PATH ]]; then
    echo "Missing or blank RALPHER_PATH env var"
    exit 1
fi

iterations="$1"
prompt="$2"
logdir="$3"

# make command array
cmd=(
    "$RALPHER_PATH/bin/ralpher.sh"
    --cwd="$parent"
    --logdir="$logdir"
    --stdout=stdout.jsonl
    --stderr=stderr.jsonl
    --progress=progress.log
    --errors=errors.log
    --state=state.json
    --iterations="$iterations"
    --prompt="$prompt"
    --worktree
)

if [ $# -eq 4 ]; then
    cmd+=(
         --task-file="$4"
    )
fi

# run the command
"${cmd[@]}"
