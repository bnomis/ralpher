#!/usr/bin/env bash
set -uoe pipefail
THIS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# shellcheck disable=SC1091
source "$THIS_DIR/activate.sh"

parent=$(dirname "$THIS_DIR")

usage() {
    cat <<EOF
Usage: $(basename "$0") TASKS-SPEC TASKS-INDEX

Arguments:
  TASKS-SPEC      the name of the spec
  TASKS-INDEX     index of tasks file

Note: You must set the RALPHER_PATH env var, so this script knows where to find ralpher.
EOF
    exit 1
}

if [ $# -ne 2 ]; then
    usage
fi

if [[ -z $RALPHER_PATH ]]; then
    echo "Missing or blank RALPHER_PATH env var"
    exit 1
fi

spec="$1"
index="$2"

# make command array
cmd=(
    "$RALPHER_PATH/bin/ralpher.sh"
    --cwd="${PWD}"
    --logdir=ralpher-logs/"$spec"/tasks-"$index"
    --stdout=stdout.jsonl
    --stderr=stderr.jsonl
    --progress=progress.log
    --errors=errors.log
    --state=state.json
    --iterations=20
    --prompt="$parent"/agents/prompts/one-task.md
    --task-file=agents/tasks/"$spec"/tasks-"$index".md
    --worktree
)


# run the command
"${cmd[@]}"
