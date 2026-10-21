# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置(跨平台):
    macOS    → dist/Wlan-Flash-Transfer-V2.app (onedir bundle)
    Windows  → dist/Wlan-Flash-Transfer-V2.exe (onefile 单文件)

用法: pyinstaller lan-transfer-v2.spec --noconfirm --clean
"""
import importlib.util
import os
import sys

# 依赖快速失败: PyQt6 未安装时 PyInstaller 仍会"成功"打出缺模块的包,
# 直到运行 exe 才报 No module named 'PyQt6' —— 在构建期就拦住并给出明确提示。
if importlib.util.find_spec("PyQt6") is None:
    raise SystemExit(
        "[FAIL] 未检测到 PyQt6, 打包会产出无法运行的 exe。\n"
        "       请先安装依赖(与执行打包的 python 保持一致):\n"
        "           python -m pip install -r requirements.txt\n"
        "       网络慢可用镜像: -i https://pypi.tuna.tsinghua.edu.cn/simple")

spec_dir = SPECPATH
NAME = "Wlan-Flash-Transfer-V2"


def _icon(ext: str):
    path = os.path.join(spec_dir, "assets", f"icon.{ext}")
    return path if os.path.exists(path) else None


ICON = _icon("ico") if sys.platform == "win32" else _icon("icns")

a = Analysis(
    ["main.py"],
    pathex=[spec_dir],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    # 本应用只用 QtCore/QtGui/QtWidgets(见 main.py / gui/), 其余一律排除
    excludes=[
        # 标准库中 GUI 应用用不到的
        "tkinter", "unittest", "pydoc_data", "test", "xmlrpc", "ftplib",
        "setuptools", "pip", "wheel", "pkg_resources",
        # PyQt6 未使用模块, 防 hook 顺带收集
        "PyQt6.QtNetwork", "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtQuickWidgets",
        "PyQt6.QtMultimedia", "PyQt6.QtMultimediaWidgets", "PyQt6.QtPdf",
        "PyQt6.QtPdfWidgets", "PyQt6.QtSvg", "PyQt6.QtSvgWidgets",
        "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebChannel",
        "PyQt6.QtWebSockets", "PyQt6.QtBluetooth", "PyQt6.QtNfc",
        "PyQt6.QtSerialPort", "PyQt6.QtSensors", "PyQt6.QtPositioning",
        "PyQt6.QtCharts", "PyQt6.QtDataVisualization", "PyQt6.QtDesigner",
        "PyQt6.QtTest", "PyQt6.QtSql", "PyQt6.QtXml", "PyQt6.QtDBus",
        "PyQt6.QtOpenGL", "PyQt6.QtOpenGLWidgets",
    ],
    noarchive=False,
)

# ---- 瘦身: 剔除未使用的 Qt 动态库/插件/翻译 ----
# 只保留 Core/Gui/Widgets 及其必要插件(cocoa/windows 平台插件、样式、图标格式)。
# 若误删了真正需要的库, 产物会启动报错或渲染异常 —— build.sh 的 --smoke
# 与 GUI 渲染自检会在打包后立刻暴露问题。
_QT_DROP = (
    # Qt 动态库框架(PyInstaller 内路径形如 .../lib/QtNetwork.framework/..., 按框架名匹配)
    # 注意: conda 版 Qt 的 QtGui 硬链接 QtDBus, 不可剔除(否则冻结包 GUI 启动即崩)
    "qtnetwork", "qtpdf", "qpdf", "qtqml", "qtquick", "qtwebengine",
    "qtwebchannel", "qtwebsockets", "qtbluetooth", "qtnfc", "qtserialport",
    "qttest", "qtsql", "qtxml", "qtdesigner", "qtcharts", "qtdatavisualization",
    "qtvirtualkeyboard", "qtremoteobjects", "qtstatemachine", "qtscxml",
    "63d",
    # 图像/图标精简: GUI 不加载这些格式(tiff/webp/heif/2000日语系等), 也不用 SVG 图标
    "qtsvg", "qsvg", "qmacheif", "qmacjp2", "qtiff", "qwebp", "qtga",
    "qwbmp", "qtuiotouch",
    # 模块名兜底(如 PyQt6/QtNetwork.abi3.so)
    "qt6network", "qt6qml", "qt6quick", "qt6pdf", "qt6multimedia", "qt6sensors",
    "qt6positioning", "qt6websockets", "qt6webchannel", "qt6bluetooth", "qt6nfc",
    "qt6serialport", "qt6test", "qt6sql", "qt6xml", "qt6designer", "qt6charts",
    "qt6datavisualization", "qt6virtualkeyboard", "qt6remoteobjects",
    "qt6statemachine", "qt6scxml", "qt6networkinformation", "qt6tls",
    # 用不到的插件目录
    "qmltooling", "sceneparsers", "geometryloaders", "networkinformation",
    "webengine", "webview", "multimedia", "sensors", "sensorgestures",
    "position", "canbus", "gamepad", "texttospeech",
    # 翻译(.qm)全量剔除 —— 界面文案为代码内写死中文
    "translations",
)


def _keep(entry) -> bool:
    name = entry[0].replace("\\", "/").lower()
    return not any(t in name for t in _QT_DROP)


a.binaries = [b for b in a.binaries if _keep(b)]
a.datas = [d for d in a.datas if _keep(d)]

pyz = PYZ(a.pure)

if sys.platform == "win32":
    # 单文件: 二进制与资源全部打进 exe
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name=NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon=ICON,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,   # macOS 下剥符号表, 进一步减小体积(Windows 分支不用 strip)
        upx=False,
        console=False,
        icon=ICON,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=True,
        upx=False,
        name=NAME,
    )
    if sys.platform == "darwin":
        app = BUNDLE(
            coll,
            name=f"{NAME}.app",
            icon=ICON,
            bundle_identifier="com.lantransfer.gui.v2",
        )
