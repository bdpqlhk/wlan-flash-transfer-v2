#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LAN 文件传输 v2 入口(PyQt6 版)。

用法:
    python3 main.py                        # 启动 GUI
    python3 main.py --smoke                # 无头自检:起服务 -> 请求接口 -> 停止
    python3 main.py --screenshot out.png   # 无头渲染并截图(验证 / 演示用)
"""
import os
import socket
import sys
import time
import traceback
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _install_excepthook() -> None:
    """兜底:PyQt6.5+ 中 slot 内未处理异常默认 qFatal 直接闪退;
    换成自定义 excepthook 后 PyQt 会把异常交给它,记录日志并继续运行。"""
    def hook(t, v, tb):
        text = "".join(traceback.format_exception(t, v, tb))
        sys.stderr.write(text)
        try:
            log = Path.home() / ("Library/Logs/LAN文件传输v2.log"
                                 if sys.platform == "darwin" else "LAN文件传输v2.log")
            with open(log, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception:
            pass
    sys.excepthook = hook


def _smoke() -> int:
    """无头自检:起服务 -> HTTP 请求 /api/files 与主页 -> 停止。"""
    from lan_transfer.core.server import TransferServer

    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    free_port = probe.getsockname()[1]
    probe.close()

    share = Path(__file__).resolve().parent / "shared_files"
    share.mkdir(exist_ok=True)
    srv = TransferServer(share, free_port)
    srv.start()

    ok = False
    deadline = time.time() + 10
    while time.time() < deadline:
        if srv.started.wait(0.2):
            break
    if not srv.last_error:
        for path in ("/", "/api/files"):
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{free_port}{path}", timeout=3) as r:
                    ok = r.status == 200
            except Exception:
                ok = False
            if not ok:
                break

    srv.stop()
    print("SMOKE_OK" if ok else "SMOKE_FAIL")
    return 0 if ok else 1


def run_screenshot(path: str) -> int:
    """以 offscreen 平台渲染窗口并截图(无显示环境验证)。"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    from lan_transfer.gui.main_window import MainWindow, QSS

    app = QApplication(sys.argv[:1])
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.resize(1020, 700)
    win.show()

    def save_and_quit() -> None:
        win.grab().save(path)
        print(f"screenshot saved: {path}")
        app.quit()

    QTimer.singleShot(1500, save_and_quit)
    return app.exec()


def main() -> int:
    if "--smoke" in sys.argv:
        return _smoke()
    if "--screenshot" in sys.argv:
        i = sys.argv.index("--screenshot")
        path = sys.argv[i + 1] if len(sys.argv) > i + 1 else "/tmp/lan-transfer-v2.png"
        return run_screenshot(path)

    from PyQt6.QtWidgets import QApplication

    from lan_transfer.gui.main_window import MainWindow, QSS

    _install_excepthook()
    app = QApplication(sys.argv)
    app.setApplicationName("LAN文件传输v2")
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
