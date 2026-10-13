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
    """无头自检:起服务 -> 鉴权/只读/页面断言 -> 停止。失败时输出诊断细节。

    使用隔离的临时配置目录, 不读写用户真实配置。
    """
    import faulthandler
    import tempfile
    import urllib.error
    from lan_transfer.core.server import TransferServer
    from lan_transfer.core.storage import Storage

    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    free_port = probe.getsockname()[1]
    probe.close()

    share = Path(__file__).resolve().parent / "shared_files"
    share.mkdir(parents=True, exist_ok=True)
    meta = Path(tempfile.mkdtemp(prefix="wft-smoke-"))
    srv = TransferServer(share, free_port, storage=Storage(meta))
    token = srv.token
    srv.start()

    deadline = time.time() + 25
    while time.time() < deadline:
        if srv.started.wait(0.2):
            break

    def req(path: str, method: str = "GET", tok: str | None = None,
            data: bytes | None = None):
        headers = {"X-Token": tok} if tok else {}
        r = urllib.request.Request(f"http://127.0.0.1:{free_port}{path}",
                                   data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(r, timeout=3) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except Exception as e:  # noqa: BLE001
            return 0, repr(e).encode()

    checks: list[tuple[str, bool]] = []
    if srv.last_error:
        checks.append((f"bind: {srv.last_error}", False))
    else:
        # 默认关闭配对校验 → 直接可访问
        st, _ = req("/")
        checks.append(("index 200", st == 200))
        st, _ = req("/api/files")
        checks.append(("files 免令牌 200", st == 200))
        checks.append(("配对码为 4 位数字", srv.token.isdigit() and len(srv.token) == 4))
        # 开启配对校验 → 无令牌 401 / 错码 401 / 正码 200
        srv.storage.update_config(require_pairing=True)
        st, _ = req("/api/files")
        checks.append(("开启校验后无令牌 401", st == 401))
        st, _ = req("/api/files", tok="0000")
        checks.append(("错误配对码 401", st == 401))
        st, body = req("/api/files", tok=srv.token)
        checks.append(("正确配对码 200", st == 200))
        # 只读模式 → 写操作 403
        srv.storage.update_config(mode="readonly")
        st, _ = req("/api/upload", method="POST", tok=srv.token, data=b"y")
        checks.append(("readonly 上传 403", st == 403))
        srv.storage.update_config(mode="full")
        checks.append(("audit 非空", len(srv.storage.audit_records()) > 0))

    srv.stop()
    faulthandler.cancel_dump_traceback_later()
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    ok = bool(checks) and all(p for _, p in checks)
    diag = (f"  diagnostics: started={srv.started.is_set()} "
            f"thread_alive={srv._thread.is_alive() if srv._thread else None} "
            f"last_error={srv.last_error!r} port={free_port} share={share}")
    if ok:
        print("SMOKE_OK")
        return 0
    print("SMOKE_FAIL")
    print(diag)
    return 1


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

    from PyQt6.QtCore import QEvent, Qt
    from PyQt6.QtWidgets import QApplication

    from lan_transfer.gui.main_window import MainWindow, QSS

    _install_excepthook()

    class LanApp(QApplication):
        """macOS:主窗口收到托盘后,点 Dock 图标重新打开。"""
        mainwin = None

        def event(self, e):
            if (e.type() == QEvent.Type.ApplicationStateChange
                    and self.applicationState() == Qt.ApplicationState.ApplicationActive
                    and sys.platform == "darwin"):
                w = LanApp.mainwin
                if w is not None and not w.isVisible():
                    w.show()
                    w.raise_()
                    w.activateWindow()
            return super().event(e)

    app = LanApp(sys.argv)
    app.setApplicationName("LAN文件传输v2")
    app.setStyleSheet(QSS)
    win = MainWindow()
    LanApp.mainwin = win
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
