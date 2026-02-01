#!/usr/bin/env bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
parent=$(dirname "$SCRIPT_DIR")
lib=$parent/src

# shellcheck disable=SC1091
source "$parent/.venv/bin/activate"

if [[ -n "${PYTHONPATH:-}" ]]; then
    export PYTHONPATH="$lib:$PYTHONPATH"
else
    export PYTHONPATH="$lib"
fi
