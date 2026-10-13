#!/usr/bin/env bash
# macOS 打包脚本: 产物 dist/Wlan-Flash-Transfer-V2.app (含 frozen 冒烟)
# 用法: bash build.sh
set -euo pipefail
cd "$(dirname "$0")"

NAME="Wlan-Flash-Transfer-V2"
APP="dist/$NAME.app"

echo ">> 解释器: $(python3 -c 'import sys; print(sys.executable, sys.version.split()[0])')"
python3 -c "import PyInstaller" 2>/dev/null || {
  echo ">> 安装 PyInstaller …"
  python3 -m pip install pyinstaller
}
python3 -c "import PyQt6" 2>/dev/null || {
  echo ">> 安装 PyQt6 …"
  python3 -m pip install -r requirements.txt
}

echo ">> 打包 $NAME.app …"
python3 -m PyInstaller lan-transfer-v2.spec --noconfirm --clean

echo ""
echo ">> 冒烟验证打包产物 …"
"$APP/Contents/MacOS/$NAME" --smoke

echo ">> GUI 渲染自检(offscreen 构建主窗口) …"
"$APP/Contents/MacOS/$NAME" --screenshot "${TMPDIR:-/tmp}/wft-gui-check.png" >/dev/null 2>&1
test -s "${TMPDIR:-/tmp}/wft-gui-check.png" || { echo "[FAIL] GUI 构建失败"; exit 1; }
echo "   GUI 渲染 OK"

echo ""
echo "✓ 完成: $APP"
echo "  运行: open '$APP'"
echo "  分发被拦截时: xattr -dr com.apple.quarantine '$APP'"
