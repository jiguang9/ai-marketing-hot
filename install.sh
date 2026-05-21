#!/bin/sh
# Install ai-marketing-hot skill to an Agent tool's skills directory.
#
# Usage:
#   sh install.sh                   # installs to $CODEX_HOME/skills/ai-marketing-hot
#                                   # or ~/.codex/skills/ai-marketing-hot if $CODEX_HOME unset
#   sh install.sh /path/to/skills   # installs to /path/to/skills/ai-marketing-hot
#
# Requires: sh, cp, chmod, mkdir (no third-party tools)

set -e

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="ai-marketing-hot"

if [ -n "$1" ]; then
    TARGET="$1/$SKILL_NAME"
elif [ -n "$CODEX_HOME" ]; then
    TARGET="$CODEX_HOME/skills/$SKILL_NAME"
else
    TARGET="$HOME/.codex/skills/$SKILL_NAME"
fi

echo "Installing $SKILL_NAME → $TARGET"

mkdir -p "$TARGET/agents" "$TARGET/scripts" "$TARGET/references"

cp "$SKILL_DIR/SKILL.md"           "$TARGET/SKILL.md"
cp "$SKILL_DIR/agents/"*           "$TARGET/agents/"
cp "$SKILL_DIR/scripts/"*.py       "$TARGET/scripts/"
cp "$SKILL_DIR/references/"*.yaml  "$TARGET/references/"
cp "$SKILL_DIR/references/"*.md    "$TARGET/references/"

chmod +x "$TARGET/scripts/"*.py

echo "Done. Skill installed at: $TARGET"
echo "Test: python3 $TARGET/scripts/fetch_aihot.py --since-hours 24 --take 3"
