#!/usr/bin/env bash
# Install ralpher's Claude Code files (claude/: the /rrq and /rro commands and
# their templates) into ~/.claude with the shared installer install-in-claude,
# at the commit this repository was tested with. Extra arguments pass
# through, e.g. --dry-run.
set -euo pipefail

INSTALL_IN_CLAUDE_REV=fa68deb10fb77ed1c59f1c35a79a93881f955901

REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)

exec uvx --from "git+ssh://git@github.com/bnomis/install-in-claude.git@$INSTALL_IN_CLAUDE_REV" \
    install-in-claude --source "$REPO/claude" "$@"
