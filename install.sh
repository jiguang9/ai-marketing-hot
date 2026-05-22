#!/bin/sh
# Install ai-marketing-hot skill to an Agent tool's skills directory.
#
# Run this script from the ROOT of the cloned repository:
#   git clone https://github.com/jiguang9/ai-marketing-hot
#   cd ai-marketing-hot && sh install.sh [TARGET_DIR] [--verify]
#
# Usage:
#   sh install.sh                          # → $CODEX_HOME/skills/ai-marketing-hot
#                                          #   or ~/.codex/skills/ai-marketing-hot
#   sh install.sh /path/to/skills         # → /path/to/skills/ai-marketing-hot
#   sh install.sh --verify                 # 安装后附加联网验证（10 秒超时）
#   sh install.sh /path/to/skills --verify

set -e

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="ai-marketing-hot"
VERIFY_NETWORK=0
INSTALL_ARG=""

# 严格参数解析：只接受 [TARGET_DIR] [--verify]，其余报错
for arg in "$@"; do
    case "$arg" in
        --verify|--verify-network)
            VERIFY_NETWORK=1
            ;;
        -*)
            echo "ERROR: unknown option: $arg"
            echo "Usage: sh install.sh [TARGET_DIR] [--verify]"
            exit 1
            ;;
        *)
            if [ -n "$INSTALL_ARG" ]; then
                echo "ERROR: unexpected argument: $arg"
                echo "Usage: sh install.sh [TARGET_DIR] [--verify]"
                exit 1
            fi
            INSTALL_ARG="$arg"
            ;;
    esac
done

# Guard: must be run from the full repo
if [ ! -d "$SKILL_DIR/scripts" ] || [ ! -d "$SKILL_DIR/references" ]; then
    echo "ERROR: scripts/ or references/ not found in $SKILL_DIR"
    echo "Run this script from the root of the cloned repository:"
    echo "  git clone https://github.com/jiguang9/ai-marketing-hot"
    echo "  cd ai-marketing-hot && sh install.sh"
    exit 1
fi

# Resolve target directory
if [ -n "$INSTALL_ARG" ]; then
    TARGET="$INSTALL_ARG/$SKILL_NAME"
elif [ -n "$CODEX_HOME" ]; then
    TARGET="$CODEX_HOME/skills/$SKILL_NAME"
else
    TARGET="$HOME/.codex/skills/$SKILL_NAME"
fi

mkdir -p "$TARGET/agents" "$TARGET/scripts" "$TARGET/references"

# 只复制 skill 运行必需文件（跳过 .git / README.md / CLAUDE.md）
cp "$SKILL_DIR/SKILL.md"          "$TARGET/SKILL.md"
cp "$SKILL_DIR/agents/"*          "$TARGET/agents/"
cp "$SKILL_DIR/scripts/"*.py      "$TARGET/scripts/"
cp "$SKILL_DIR/references/"*.yaml "$TARGET/references/"
cp "$SKILL_DIR/references/"*.md   "$TARGET/references/"
chmod +x "$TARGET/scripts/"*.py

# 本地文件完整性检查（不联网）
MISSING=""
for f in SKILL.md agents/openai.yaml \
          scripts/fetch_aihot.py scripts/fetch_sources.py scripts/fetch_social.py \
          scripts/rank_items.py scripts/build_report.py \
          references/; do
    if [ ! -e "$TARGET/$f" ]; then
        MISSING="$MISSING $f"
    fi
done

if [ -n "$MISSING" ]; then
    echo "ERROR: Installation incomplete. Missing:$MISSING"
    exit 1
fi

echo "已安装 $SKILL_NAME 到："
echo "  $TARGET"
echo ""
echo "已检查："
echo "  - SKILL.md"
echo "  - agents/openai.yaml"
echo "  - scripts/ (5 个脚本)"
echo "  - references/"

# 可选联网验证（--verify / --verify-network）
# 使用 Python subprocess 实现跨平台 10 秒超时（macOS 无 GNU timeout）
if [ "$VERIFY_NETWORK" = "1" ]; then
    echo ""
    echo "联网验证中（最多 10 秒）..."
    if python3 - "$TARGET/scripts/fetch_aihot.py" <<'PYEOF'
import subprocess, sys
script = sys.argv[1]
try:
    r = subprocess.run(
        ["python3", script, "--since-hours", "24", "--take", "1"],
        timeout=10, capture_output=True
    )
    sys.exit(0 if r.returncode == 0 else 1)
except subprocess.TimeoutExpired:
    sys.exit(1)
PYEOF
    then
        echo "联网验证通过。"
    else
        echo "联网验证未完成，可稍后重试："
        echo "  python3 $TARGET/scripts/fetch_aihot.py --since-hours 24 --take 1"
    fi
else
    echo ""
    echo "如需联网验证，请运行："
    echo "  python3 $TARGET/scripts/fetch_aihot.py --since-hours 24 --take 1"
fi
