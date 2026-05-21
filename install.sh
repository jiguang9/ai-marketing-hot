#!/bin/sh
# Install ai-marketing-hot skill to an Agent tool's skills directory.
#
# IMPORTANT: Run this script from the ROOT of the cloned repository.
#   git clone https://github.com/jiguang9/ai-marketing-hot
#   cd ai-marketing-hot
#   sh install.sh [TARGET_DIR]
#
# Do NOT run a standalone install.sh or git-clone directly into the target
# directory — that would copy .git and miss the verification step.
#
# Usage:
#   sh install.sh                   # → $CODEX_HOME/skills/ai-marketing-hot
#                                   #   or ~/.codex/skills/ai-marketing-hot
#   sh install.sh /path/to/skills   # → /path/to/skills/ai-marketing-hot

set -e

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="ai-marketing-hot"

# Guard: must be run from the full repo (scripts/ and references/ must exist)
if [ ! -d "$SKILL_DIR/scripts" ] || [ ! -d "$SKILL_DIR/references" ]; then
    echo "ERROR: scripts/ or references/ not found in $SKILL_DIR"
    echo ""
    echo "This script must be run from the root of the cloned repository:"
    echo "  git clone https://github.com/jiguang9/ai-marketing-hot"
    echo "  cd ai-marketing-hot && sh install.sh"
    exit 1
fi

# Resolve target directory
if [ -n "$1" ]; then
    TARGET="$1/$SKILL_NAME"
elif [ -n "$CODEX_HOME" ]; then
    TARGET="$CODEX_HOME/skills/$SKILL_NAME"
else
    TARGET="$HOME/.codex/skills/$SKILL_NAME"
fi

# Warn if target looks like a git clone (contains .git)
if [ -d "$TARGET/.git" ]; then
    echo "WARNING: $TARGET/.git exists — the target appears to be a git clone."
    echo "This install will overlay a clean copy. To start fresh:"
    echo "  rm -rf $TARGET && sh install.sh"
    echo ""
fi

echo "Installing $SKILL_NAME → $TARGET"
mkdir -p "$TARGET/agents" "$TARGET/scripts" "$TARGET/references"

cp "$SKILL_DIR/SKILL.md"           "$TARGET/SKILL.md"
cp "$SKILL_DIR/agents/"*           "$TARGET/agents/"
cp "$SKILL_DIR/scripts/"*.py       "$TARGET/scripts/"
cp "$SKILL_DIR/references/"*.yaml  "$TARGET/references/"
cp "$SKILL_DIR/references/"*.md    "$TARGET/references/"
chmod +x "$TARGET/scripts/"*.py

# Verify critical files are present
MISSING=""
for f in SKILL.md scripts/fetch_aihot.py scripts/fetch_sources.py scripts/rank_items.py scripts/build_report.py references/sources.yaml; do
    if [ ! -f "$TARGET/$f" ]; then
        MISSING="$MISSING $f"
    fi
done

if [ -n "$MISSING" ]; then
    echo "ERROR: Installation incomplete. Missing:$MISSING"
    exit 1
fi

echo ""
echo "Done. Installed at: $TARGET"
echo "Quick test:"
echo "  python3 $TARGET/scripts/fetch_aihot.py --since-hours 24 --take 3"
