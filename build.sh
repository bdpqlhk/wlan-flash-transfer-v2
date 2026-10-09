#!/usr/bin/env bash
# macOS 打包脚本: 产物 dist/LAN文件传输v2.app (含 frozen 冒烟)
# 用法: bash build.sh
set -euo pipefail
cd "$(dirname "$0")"

echo ">> 解释器: $(python3 -c 'import sys; print(sys.executable, sys.version.split()[0])')"
python3 -c "import PyInstaller" 2>/dev/null || {
  echo ">> 安装 PyInstaller …"
  python3 -m pip install pyinstaller
}
python3 -c "import PyQt6" 2>/dev/null || {
  echo ">> 安装 PyQt6 …"
  python3 -m pip install -r requirements.txt
}

echo ">> 打包 LAN文件传输v2.app …"
python3 -m PyInstaller lan-transfer-v2.spec --noconfirm --clean

echo ""
echo ">> 冒烟验证打包产物 …"
"dist/LAN文件传输v2.app/Contents/MacOS/LAN文件传输v2" --smoke

echo ""
echo "✓ 完成: dist/LAN文件传输v2.app"
echo "  运行: open 'dist/LAN文件传输v2.app'"
echo "  分发被拦截时: xattr -dr com.apple.quarantine 'dist/LAN文件传输v2.app'"
