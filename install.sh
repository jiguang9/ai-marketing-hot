#!/bin/sh
set -eu

SKILL_NAME="ai-marketing-hot"
REPO_ARCHIVE_URL=${AI_MARKETING_HOT_ARCHIVE_URL:-"https://github.com/jiguang9/ai-marketing-hot/archive/refs/heads/main.tar.gz"}
SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TMP_DIR=""

usage() {
  echo "Usage: sh install.sh [skills_dir]" >&2
  echo "Example: sh install.sh \"\$HOME/.codex/skills\"" >&2
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

cleanup() {
  if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

if [ ! -f "$SOURCE_DIR/SKILL.md" ]; then
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required when installing from a piped script." >&2
    exit 1
  fi
  if ! command -v tar >/dev/null 2>&1; then
    echo "tar is required when installing from a piped script." >&2
    exit 1
  fi
  TMP_DIR=$(mktemp -d)
  curl -fsSL "$REPO_ARCHIVE_URL" | tar -xz -C "$TMP_DIR"
  SOURCE_DIR="$TMP_DIR/ai-marketing-hot-main"
fi

if [ "${1:-}" ]; then
  TARGET_PARENT=$1
elif [ "${AGENT_SKILLS_DIR:-}" ]; then
  TARGET_PARENT=$AGENT_SKILLS_DIR
elif [ "${CODEX_HOME:-}" ]; then
  TARGET_PARENT="$CODEX_HOME/skills"
elif [ "${CLAUDE_HOME:-}" ]; then
  TARGET_PARENT="$CLAUDE_HOME/skills"
else
  TARGET_PARENT="$HOME/.codex/skills"
fi

TARGET_DIR="$TARGET_PARENT/$SKILL_NAME"

mkdir -p "$TARGET_PARENT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SOURCE_DIR/SKILL.md" "$TARGET_DIR/"
cp -R "$SOURCE_DIR/agents" "$TARGET_DIR/"
cp -R "$SOURCE_DIR/references" "$TARGET_DIR/"
cp -R "$SOURCE_DIR/scripts" "$TARGET_DIR/"

chmod +x "$TARGET_DIR/scripts/"*.py 2>/dev/null || true

echo "Installed $SKILL_NAME to $TARGET_DIR"
