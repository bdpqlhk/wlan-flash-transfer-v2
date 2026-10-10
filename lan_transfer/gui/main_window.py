# -*- coding: utf-8 -*-
"""LAN 文件传输 v2 主窗口(样式参考 tcode GUI 深色开发者工具风格)。

结构:顶部 header(品牌/版本) → Tab「服务」(状态徽标 / 访问地址 / 配置 /
屏上二维码 / 共享文件表) + Tab「聊天」(网页端消息实时镜像) →
底部「服务日志」Dock → 状态栏。服务跑在守护线程,回调经 Qt 信号
转主线程;文件列表/删除经 Worker 后台执行。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, QPointF, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QAction, QColor, QDesktopServices, QIcon, QImage, QPainter, QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication, QDockWidget, QFileDialog, QFormLayout, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QPlainTextEdit, QPushButton, QStatusBar, QSystemTrayIcon, QTabWidget,
    QVBoxLayout, QWidget,
)

from .. import __version__
from ..core import format_size
from ..core.server import TransferServer, get_lan_ip
from ..qrterm import qr_matrix
from .theme import DIM, GREEN, QSS, RED
from .widgets import chip, make_mono, make_table, set_chip, set_rows

def _default_share_dir() -> Path:
    """默认共享目录: ~/LAN文件传输。

    打包态 __file__ 在 .app 包内(PyInstaller 冻结目录),不可写也不该写;
    固定用用户主目录,开发/打包行为一致。
    """
    return Path.home() / "LAN文件传输"


class _Bridge(QObject):
    """服务线程 -> 主线程的信号桥(回调在子线程触发,经队列投递)。"""

    log_line = pyqtSignal(str)
    chat_msg = pyqtSignal(dict)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAN 文件传输 v2 · 局域网 AirDrop")
        self.resize(1020, 700)
        self.setMinimumSize(860, 560)

        self._server: TransferServer | None = None
        self._start_poll: QTimer | None = None
        self._bridge = _Bridge(self)
        self._bridge.log_line.connect(self._append_log)
        self._bridge.chat_msg.connect(self._append_chat)
        self._busy = 0

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_tabs())
        self._build_log_dock()
        self._build_statusbar()
        self._build_menus()
        self._build_tray()

        self._really_quitting = False
        self._tray_tip_shown = False

        self._reset_ui_stopped()
        self._refresh_files()          # 目录里已有的文件直接展示
        self._update_free_space()

    # ------------------------------------------------------------------ #
    # 界面搭建
    # ------------------------------------------------------------------ #
    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 12, 16, 12)
        brand = QLabel("⚡ LAN 文件传输")
        brand.setObjectName("brand")
        subtitle = QLabel("局域网 AirDrop · 浏览器即开即用 · PyQt6 重写版")
        subtitle.setObjectName("subtitle")
        version = QLabel(f"v{__version__}")
        version.setObjectName("version")
        hl.addWidget(brand)
        hl.addSpacing(12)
        hl.addWidget(subtitle)
        hl.addStretch(1)
        hl.addWidget(version)
        return header

    def _build_tabs(self) -> QTabWidget:
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_service_tab(), "服务")
        self.tabs.addTab(self._build_chat_tab(), "聊天")
        return self.tabs

    def _build_service_tab(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ---- 左列:状态 + 配置 + 文件 ----
        left = QVBoxLayout()
        left.setSpacing(12)

        top = QHBoxLayout()
        self._chip = chip("○ 已停止", "chipDim")
        self._url_lbl = QLabel("—")
        self._url_lbl.setObjectName("urlLabel")
        self._url_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        copy_btn = QPushButton("复制链接")
        copy_btn.clicked.connect(self._copy_url)
        open_btn = QPushButton("打开浏览器")
        open_btn.clicked.connect(self._open_browser)
        top.addWidget(self._chip)
        top.addSpacing(8)
        top.addWidget(self._url_lbl, 1)
        top.addWidget(copy_btn)
        top.addWidget(open_btn)
        left.addLayout(top)

        cfg = QGroupBox("服务配置")
        form = QFormLayout(cfg)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self._port_edit = QLineEdit(str(8765))
        self._dir_edit = QLineEdit(str(_default_share_dir()))
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse_dir)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self._dir_edit, 1)
        dir_row.addWidget(browse)
        self._space_lbl = QLabel("—")
        dir_wrap = QWidget()
        dir_wrap.setLayout(dir_row)
        form.addRow("端口:", self._port_edit)
        form.addRow("共享目录:", dir_wrap)
        form.addRow("可用空间:", self._space_lbl)
        left.addWidget(cfg)

        actions = QHBoxLayout()
        self._start_btn = QPushButton("启动服务")
        self._start_btn.setObjectName("primary")
        self._start_btn.clicked.connect(self.start_server)
        self._stop_btn = QPushButton("停止服务")
        self._stop_btn.clicked.connect(self.stop_server)
        self._stop_btn.setEnabled(False)
        opendir = QPushButton("打开共享目录")
        opendir.clicked.connect(self._open_dir)
        actions.addWidget(self._start_btn)
        actions.addWidget(self._stop_btn)
        actions.addStretch(1)
        actions.addWidget(opendir)
        left.addLayout(actions)

        files = QGroupBox("共享文件")
        flay = QVBoxLayout(files)
        fbar = QHBoxLayout()
        refresh = QPushButton("↻ 刷新")
        refresh.clicked.connect(self._refresh_files)
        self._del_btn = QPushButton("删除选中")
        self._del_btn.setObjectName("danger")
        self._del_btn.clicked.connect(self._delete_selected)
        self._count_lbl = QLabel("共 0 个")
        self._count_lbl.setObjectName("hint")
        fbar.addWidget(self._count_lbl)
        fbar.addStretch(1)
        fbar.addWidget(self._del_btn)
        fbar.addWidget(refresh)
        flay.addLayout(fbar)
        self._table = make_table(["文件名", "大小", "修改时间"], stretch_col=0)
        self._table.doubleClicked.connect(
            lambda idx: self._open_file(self._table.item(idx.row(), 0).text()))
        flay.addWidget(self._table)
        left.addWidget(files, 1)

        root.addLayout(left, 3)

        # ---- 右列:二维码 ----
        qr_box = QGroupBox("手机扫码直达")
        qlay = QVBoxLayout(qr_box)
        qlay.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._qr_lbl = QLabel("未运行")
        self._qr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_lbl.setMinimumSize(220, 220)
        qlay.addStretch(1)
        qlay.addWidget(self._qr_lbl)
        self._qr_hint = QLabel("启动服务后显示二维码\n手机摄像头对准即可打开")
        self._qr_hint.setObjectName("hint")
        self._qr_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qlay.addWidget(self._qr_hint)
        qlay.addStretch(1)
        root.addWidget(qr_box, 1)
        return page

    def _build_chat_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        bar = QHBoxLayout()
        title = QLabel("聊天(网页端消息实时镜像)")
        title.setObjectName("panelTitle")
        clear = QPushButton("清空显示")
        clear.clicked.connect(lambda: self._chat_view.clear())
        bar.addWidget(title)
        bar.addStretch(1)
        bar.addWidget(clear)
        root.addLayout(bar)
        self._chat_view = QPlainTextEdit()
        self._chat_view.setReadOnly(True)
        self._chat_view.setPlaceholderText("局域网设备在网页上发的消息会实时出现在这里…")
        make_mono(self._chat_view)
        root.addWidget(self._chat_view, 1)
        return page

    def _build_log_dock(self) -> None:
        self._log_dock = QDockWidget("服务日志", self)
        self._log_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(8, 4, 8, 8)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(5000)
        self._log.setPlaceholderText("HTTP 请求与服务事件…")
        make_mono(self._log)
        lay.addWidget(self._log)
        self._log_dock.setWidget(widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._log_dock)
        self.resizeDocks([self._log_dock], [130], Qt.Orientation.Vertical)

    def _build_statusbar(self) -> None:
        bar = QStatusBar()
        self.setStatusBar(bar)
        self._status_lbl = QLabel("就绪")
        bar.addWidget(self._status_lbl)
        self._busy_lbl = QLabel("⏳ 执行中…")
        self._busy_lbl.setObjectName("busy")
        bar.addPermanentWidget(self._busy_lbl)
        self._busy_lbl.hide()

    def _build_menus(self) -> None:
        m_file = self.menuBar().addMenu("文件")
        act_refresh = QAction("刷新文件列表", self)
        act_refresh.setShortcut("F5")
        act_refresh.triggered.connect(self._refresh_files)
        m_file.addAction(act_refresh)
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self.real_quit)  # 真正退出;点窗口 ✗ 是收到托盘
        m_file.addAction(act_quit)

        m_view = self.menuBar().addMenu("视图")
        m_view.addAction(self._log_dock.toggleViewAction())

        m_help = self.menuBar().addMenu("帮助")
        act_about = QAction("关于", self)
        act_about.triggered.connect(self._about)
        m_help.addAction(act_about)

    # ------------------------------------------------------------------ #
    # 托盘(Tray):关窗默认收到这里,服务继续运行;菜单「退出」才真正退出
    # ------------------------------------------------------------------ #
    def _build_tray(self) -> None:
        self._tray = QSystemTrayIcon(QIcon(self._render_tray_icon()), self)
        self._tray.setToolTip("LAN 文件传输 v2")

        menu = QMenu()
        self._act_show = QAction("显示主窗口", self)
        self._act_show.triggered.connect(self._show_from_tray)
        self._act_toggle = QAction("启动服务", self)
        self._act_toggle.triggered.connect(self._toggle_service_from_tray)
        act_open = QAction("打开网页", self)
        act_open.triggered.connect(self._open_browser)
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self.real_quit)
        for a in (self._act_show,):
            menu.addAction(a)
        menu.addSeparator()
        for a in (self._act_toggle, act_open):
            menu.addAction(a)
        menu.addSeparator()
        menu.addAction(act_quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _render_tray_icon(self) -> QPixmap:
        """菜单栏图标:蓝紫渐变圆角底 + 白色闪电(与 app 图标一致,无需外部文件)。"""
        size = 64
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        from PyQt6.QtGui import QLinearGradient
        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, QColor("#4f8af7"))
        grad.setColorAt(1.0, QColor("#7c6ff7"))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        m = size * 0.10
        p.drawRoundedRect(int(m), int(m), int(size - 2 * m), int(size - 2 * m),
                          int(size * 0.22), int(size * 0.22))
        bolt = [(0.60, 0.06), (0.26, 0.56), (0.47, 0.56),
                (0.38, 0.94), (0.74, 0.42), (0.52, 0.42), (0.66, 0.06)]
        sx, sy, ox, oy = size * 0.84, size * 0.88, size * 0.08, size * 0.06
        path = [QPointF(ox + x * sx, oy + y * sy) for x, y in bolt]
        p.setBrush(QColor("#ffffff"))
        p.drawPolygon(*path)
        p.end()
        return pm

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_service_from_tray(self) -> None:
        if self._server is not None and self._server.running:
            self.stop_server()
        else:
            self.start_server()
            self._show_from_tray()

    def real_quit(self) -> None:
        """真正退出(Tray 菜单 / 文件菜单「退出」)。"""
        self._really_quitting = True
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt 命名)
        if self._really_quitting or not self._tray.isVisible():
            self.stop_server()          # 服务干净收尾(daemon 线程兜底)
            self._tray.hide()
            event.accept()
            return
        # 点窗口 ✗:收到菜单栏,服务继续运行
        event.ignore()
        self.hide()
        if not self._tray_tip_shown:
            self._tray_tip_shown = True
            self._tray.showMessage(
                "LAN 文件传输仍在运行",
                "窗口已收到菜单栏,服务保持运行。点菜单栏图标可重新打开;退出请用其菜单中的「退出」。",
                QSystemTrayIcon.MessageIcon.Information, 5000)

    def _about(self) -> None:
        QMessageBox.about(
            self, "关于 LAN 文件传输 v2",
            f"<b>LAN 文件传输 v{__version__}</b>(PyQt6 重写版)<br>"
            f"局域网 AirDrop:任意设备浏览器打开地址即可上传/下载/聊天<br><br>"
            f"网页端零依赖任何客户端;桌面端负责启停服务、选目录、看日志与扫码。")

    # ------------------------------------------------------------------ #
    # 启停控制
    # ------------------------------------------------------------------ #
    def start_server(self) -> None:
        if self._server is not None and self._server.running:
            return
        try:
            port = int(self._port_edit.text().strip())
            if not 0 < port < 65536:
                raise ValueError
        except ValueError:
            self.show_status("✗ 端口必须是 1-65535 的数字", error=True)
            return
        upload_dir = Path(self._dir_edit.text().strip() or
                          str(_default_share_dir()))
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, "错误", f"共享目录不可用:\n{e}")
            return

        srv = TransferServer(upload_dir, port)
        srv.on_log = self._bridge.log_line.emit
        srv.on_chat = self._bridge.chat_msg.emit
        srv.start()
        self._server = srv
        self._set_starting_ui()
        self.set_busy(+1)
        self._start_poll = QTimer(self)
        self._start_poll.timeout.connect(lambda: self._poll_start(srv))
        self._start_poll.start(80)

    def _poll_start(self, srv: TransferServer) -> None:
        """轮询启动结果(服务线程绑定端口后置位 started)。"""
        if not srv.started.is_set():
            return
        self._start_poll.stop()
        self._start_poll = None
        self.set_busy(-1)
        if srv.last_error:
            self._server = None
            self._reset_ui_stopped()
            self._append_log(f"服务启动失败: {srv.last_error}")
            self.show_status(f"✗ 服务启动失败(端口被占用?): {srv.last_error}", error=True)
            return
        self._set_running_ui(srv)
        self._append_log(f"访问地址: {srv.url}")
        self._refresh_files()

    def stop_server(self) -> None:
        if self._server is None:
            return
        self._server.stop()
        self._server = None
        self._reset_ui_stopped()
        self.show_status("✓ 服务已停止")

    # ---- 状态切换 ----
    def _set_starting_ui(self) -> None:
        set_chip(self._chip, "● 启动中…", "chipWarn")
        self._start_btn.setEnabled(False)
        self._port_edit.setEnabled(False)
        self._dir_edit.setEnabled(False)
        self._act_toggle.setText("停止服务")
        self._act_toggle.setEnabled(False)
        self.show_status("正在绑定端口…")

    def _set_running_ui(self, srv: TransferServer) -> None:
        set_chip(self._chip, "● 运行中", "chipOk")
        self._url_lbl.setText(srv.url)
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._port_edit.setEnabled(False)
        self._dir_edit.setEnabled(False)
        self._act_toggle.setText("停止服务")
        self._act_toggle.setEnabled(True)
        self._qr_lbl.setPixmap(self._render_qr(srv.url))
        self._qr_hint.setText("扫码打开 · 或在浏览器输入下方地址")
        self.show_status(f"✓ 服务运行中: {srv.url}")

    def _reset_ui_stopped(self) -> None:
        set_chip(self._chip, "○ 已停止", "chipDim")
        self._url_lbl.setText("—")
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._port_edit.setEnabled(True)
        self._dir_edit.setEnabled(True)
        self._act_toggle.setText("启动服务")
        self._act_toggle.setEnabled(True)
        self._qr_lbl.setText("未运行")
        self._qr_lbl.setPixmap(QPixmap())
        self._qr_hint.setText("启动服务后显示二维码\n手机摄像头对准即可打开")

    # ------------------------------------------------------------------ #
    # 文件列表
    # ------------------------------------------------------------------ #
    def _refresh_files(self) -> None:
        if self._server is None:
            self._fill_files([])
            return
        srv = self._server
        self.set_busy(+1)
        from .workers import Worker
        w = Worker(lambda: srv.list_files(), parent=self)
        w.done.connect(self._on_files_loaded)
        w.finished.connect(w.deleteLater)
        w.start()
        self._workers = getattr(self, "_workers", [])
        self._workers.append(w)

    def _on_files_loaded(self, result) -> None:
        self.set_busy(-1)
        if isinstance(result, BaseException):
            self.show_status(f"✗ 读取文件列表失败: {result}", error=True)
            return
        self._fill_files(result)

    def _fill_files(self, entries) -> None:
        rows = [[name, format_size(size),
                 datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")]
                for name, size, mtime in entries]
        set_rows(self._table, rows)
        self._count_lbl.setText(f"共 {len(rows)} 个")

    def _delete_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0 or self._server is None:
            self.show_status("请先选中要删除的文件", error=True)
            return
        name = self._table.item(row, 0).text()
        if QMessageBox.question(self, "确认删除",
                                f"确定删除「{name}」?") != QMessageBox.StandardButton.Yes:
            return
        path = self._server.upload_dir / name
        self.set_busy(+1)
        from .workers import Worker
        w = Worker(lambda: path.unlink(), parent=self)
        w.done.connect(lambda r: (self.set_busy(-1),
                                  self._on_deleted(r, name)))
        w.finished.connect(w.deleteLater)
        w.start()
        self._workers.append(w)

    def _on_deleted(self, result, name: str) -> None:
        if isinstance(result, BaseException):
            self.show_status(f"✗ 删除失败: {result}", error=True)
        else:
            self._append_log(f"已删除 {name}")
            self.show_status(f"✓ 已删除 {name}")
        self._refresh_files()

    def _open_file(self, name: str) -> None:
        if self._server is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._server.upload_dir / name)))

    # ------------------------------------------------------------------ #
    # 小动作
    # ------------------------------------------------------------------ #
    def _render_qr(self, url: str) -> QPixmap:
        """URL -> 二维码 QPixmap(白底黑码)。"""
        matrix = qr_matrix(url)
        n = len(matrix)
        scale, quiet = 6, 4
        total = (n + quiet * 2) * scale
        img = QImage(total, total, QImage.Format.Format_RGB32)
        p = QPainter(img)
        p.fillRect(0, 0, total, total, QColor("white"))
        for y in range(n):
            for x in range(n):
                if matrix[y][x]:
                    p.fillRect((x + quiet) * scale, (y + quiet) * scale,
                               scale, scale, QColor("black"))
        p.end()
        return QPixmap.fromImage(img)

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择共享目录",
                                                self._dir_edit.text() or str(Path.home()))
        if path:
            self._dir_edit.setText(path)
            self._update_free_space(path)

    def _update_free_space(self, path: str | None = None) -> None:
        import shutil
        target = Path(path or self._dir_edit.text())
        try:
            # 目录可能尚未创建: 向上找最近存在的祖先(同一卷, 容量一致)
            probe = target
            while not probe.exists() and probe != probe.parent:
                probe = probe.parent
            usage = shutil.disk_usage(probe)
            self._space_lbl.setText(f"{format_size(usage.free)} / {format_size(usage.total)}")
        except Exception:
            self._space_lbl.setText("无法获取")

    def _copy_url(self) -> None:
        url = self._url_lbl.text()
        if url and url != "—":
            QApplication.clipboard().setText(url)
            self.show_status(f"✓ 已复制 {url}")

    def _open_browser(self) -> None:
        url = self._url_lbl.text()
        if url and url != "—":
            QDesktopServices.openUrl(QUrl(url))

    def _open_dir(self) -> None:
        d = self._dir_edit.text()
        if os.path.isdir(d):
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))

    # ------------------------------------------------------------------ #
    # 日志 / 聊天 / 状态
    # ------------------------------------------------------------------ #
    def _append_log(self, text: str) -> None:
        self._log.appendPlainText(f"[{datetime.now():%H:%M:%S}] {text}")

    def _append_chat(self, msg: dict) -> None:
        t = datetime.fromtimestamp(msg.get("timestamp", 0)).strftime("%H:%M:%S")
        self._chat_view.appendPlainText(
            f"[{t}] {msg.get('nickname', '?')}({msg.get('ip', '?')}): {msg.get('message', '')}")

    def set_busy(self, delta: int) -> None:
        self._busy = max(0, self._busy + delta)
        self._busy_lbl.setVisible(self._busy > 0)

    def show_status(self, msg: str, error: bool = False) -> None:
        self._status_lbl.setText(msg)
        color = RED.name() if error else (GREEN.name() if msg.startswith("✓") else "#e6e8eb")
        self._status_lbl.setStyleSheet(f"color: {color};")


def launch() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LAN文件传输v2")
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    return app.exec()
