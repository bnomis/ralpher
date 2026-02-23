#!/usr/bin/env bash
set -uoe pipefail
THIS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# shellcheck disable=SC1091
source "$THIS_DIR/activate.sh"

parent=$(dirname "$THIS_DIR")

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] ITERATIONS PROMPT TASKS LOGDIR

Arguments:
  ITERATIONS      number of iterations
  PROMPT          prompt file (e.g., PROMPT.md)
  TASKS           tasks file (e.g., tasks.txt), substituted into prompt as {{task_file}}
  LOGDIR          directory to hold logs

You must set the RALPHER_PATH env var, so this script knows where to find ralpher.
EOF
    exit 1
}

if [ $# -ne 4 ]; then
    usage
fi

iterations="$1"
prompt="$2"
tasks="$3"
logdir=$4

if [[ -z $RALPHER_PATH ]]; then
    echo "missing or blank RALPHER_PATH env var"
    exit 1
fi

"$RALPHER_PATH/bin/ralpher.sh" \
    --cwd="$parent" \
    --logdir="$logdir" \
    --stdout=stdout.jsonl \
    --stderr=stderr.jsonl \
    --progress=progress.log \
    --errors=errors.log \
    --state=state.json \
    --iterations="$iterations" \
    --prompt="$prompt" \
    --vars=task_file="$tasks"
