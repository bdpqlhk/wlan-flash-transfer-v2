# -*- coding: utf-8 -*-
"""LAN 文件传输服务核心(v2 重构版)。

v1 的服务器嵌在 tkinter GUI 文件里、状态用模块级全局变量;
v2 收敛为可实例化的 TransferServer: 一个实例 = 一个服务,
上传目录 / 聊天记录 / 日志回调全部实例态, 线程模型不变
(ThreadingHTTPServer 跑在守护线程, start/stop 由 GUI 控制)。

对外接口:
    srv = TransferServer(upload_dir, port, bind="0.0.0.0")
    srv.on_log = cb          # 请求日志(子线程回调, GUI 侧自行转主线程)
    srv.on_chat = cb         # 新聊天消息(dict)
    srv.start() / srv.stop() / srv.started / srv.last_error
    srv.url                  # http://<lan_ip>:<port>
    srv.list_files()         # [(name, size, mtime)] 按时间倒序
"""
from __future__ import annotations

import http.server
import json
import mimetypes
import os
import secrets
import shutil
import socket
import socketserver
import threading
import time
import urllib.parse
from pathlib import Path

from .storage import Storage
from ..qrterm import qr_png_bytes
from .webui import HTML_PAGE

CHUNK = 1024 * 1024
CHAT_MAX = 200


def get_lan_ip() -> str:
    """本机局域网 IP(UDP connect 探测, 不发包; 失败回退 hostname/127.0.0.1)。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
            if ip != "127.0.0.1":
                return ip
        except Exception:
            pass
        return "127.0.0.1"


def format_size(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


class _ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def server_bind(self) -> None:
        """跳过 HTTPServer.server_bind 中的 socket.getfqdn() 反向 DNS 查询 ——
        在部分网络环境(如 CI runner / 无反向解析的内网)会阻塞 30 秒以上。
        本服务不需要 server_name 的 FQDN,直接用 IP。"""
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port

    def handle_error(self, request, client_address):
        """客户端断开等噪音不打印堆栈。"""
        pass


class TransferServer:
    """局域网文件共享 + 聊天服务(可实例化, 线程安全回调)。"""

    def __init__(self, upload_dir: Path, port: int, bind: str = "0.0.0.0",
                 storage: Storage | None = None):
        self.upload_dir = Path(upload_dir)
        self.port = port
        self.bind = bind
        self.storage = storage or Storage()
        self.on_log = None      # callable(str)  请求日志
        self.on_chat = None     # callable(dict) 新消息
        self.last_error = ""
        self.started = threading.Event()
        self._chat: list[dict] = []
        self._chat_lock = threading.Lock()
        self._httpd: _ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def token(self) -> str:
        """配对令牌(实时读配置, 重新生成后立即生效)。"""
        return self.storage.config.get("token", "")

    @property
    def readonly(self) -> bool:
        return self.storage.config.get("mode") == "readonly"

    # ---------------- 对外 ----------------
    @property
    def url(self) -> str:
        return f"http://{get_lan_ip()}:{self.port}"

    @property
    def running(self) -> bool:
        return self._httpd is not None

    def start(self) -> None:
        """起线程绑定端口并 serve; 结果(成功/失败)经 started 事件 + last_error 通知。"""
        if self.running:
            return
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.last_error = ""
        self.started.clear()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        httpd, self._httpd = self._httpd, None
        if httpd is None:
            return
        try:
            httpd.shutdown()
        except Exception:
            pass
        try:
            httpd.server_close()
        except Exception:
            pass
        self._log("服务已停止")

    def list_files(self) -> list[tuple[str, int, float]]:
        """[(名称, 大小, 修改时间)], 按时间倒序。"""
        entries = []
        try:
            for e in self.upload_dir.iterdir():
                if e.is_file():
                    st = e.stat()
                    entries.append((e.name, st.st_size, st.st_mtime))
        except OSError:
            pass
        return sorted(entries, key=lambda t: t[2], reverse=True)

    def chat_messages(self) -> list[dict]:
        with self._chat_lock:
            return list(self._chat)

    # ---------------- 内部 ----------------
    def _log(self, msg: str) -> None:
        if self.on_log:
            try:
                self.on_log(msg)
            except Exception:
                pass

    def _serve(self) -> None:
        try:
            state = self
            httpd = _ThreadingHTTPServer((self.bind, self.port), _make_handler(state))
            self._httpd = httpd
            self.started.set()
            self._log(f"服务已启动 端口 {self.port} 目录 {self.upload_dir}")
            httpd.serve_forever()
        except Exception as e:  # noqa: BLE001
            self.last_error = str(e)
            self.started.set()
            self._log(f"服务启动失败: {e}")


def _make_handler(state: TransferServer) -> type[http.server.BaseHTTPRequestHandler]:
    """生成绑定到 state 的 Handler(闭包而非全局, 支持多实例)。"""

    class TransferHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            try:
                state._log("[%s] %s" % (self.client_address[0], fmt % args))
            except Exception:
                pass

        # ---- 鉴权 / 设备 / 审计 ----
        def _device_id(self) -> str:
            return self.headers.get("X-Device", "")

        def _check_auth(self) -> bool:
            """校验开关关闭时直接放行; 开启则校验 4 位配对码, 失败回 401 并审计。"""
            cfg = state.storage.config
            if not cfg.get("require_pairing"):
                return True
            given = self.headers.get("X-Token", "")
            if not given:
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                given = (q.get("t") or [""])[0]
            token = cfg.get("token", "")
            if given and secrets.compare_digest(given, token):
                state.storage.touch_device(
                    self._device_id(),
                    self.headers.get("X-Device-Name", ""),
                    self.client_address[0])
                return True
            self.send_json({"error": "需要配对码"}, 401)
            state.storage.append_audit(
                {"action": "denied", "ip": self.client_address[0],
                 "path": self.path, "ok": False})
            return False

        def _audit(self, action: str, **kw) -> None:
            state.storage.append_audit(
                {"action": action, "ip": self.client_address[0],
                 "device": self._device_id(), **kw})

        def _readonly(self) -> bool:
            """只读模式时回 403。"""
            if state.readonly:
                self.send_json({"error": "只读模式, 不允许该操作"}, 403)
                return True
            return False

        # ---- 响应工具 ----
        def send_json(self, data, status=200):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        def send_error_json(self, msg, status=400):
            self.send_json({"error": msg}, status)

        def safe_filename(self, name):
            name = urllib.parse.unquote(name)
            name = name.replace("\\", "/")
            if "/" in name:
                return None  # 带 URL 编码分隔符 = 疑似路径穿越, 一律拒绝
            if not name or name in (".", ".."):
                return None
            return name

        def _file_path(self, name):
            p = (state.upload_dir / name).resolve()
            if not str(p).startswith(str(state.upload_dir.resolve())):
                return None  # 越界路径
            return p

        # ---- GET ----
        def do_GET(self):
            path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
            if path in ("/", "/index.html"):
                self._serve_index()      # 页面始终可开, 数据接口由令牌保护
                return
            if not self._check_auth():
                return
            if path == "/api/config":
                self.send_json({
                    "app": "lan-transfer",
                    "mode": state.storage.config.get("mode", "full"),
                    "readonly": state.readonly,
                    "version": 2,
                })
            elif path == "/qr":
                # 本地渲染二维码(含配对令牌), 不经任何外部 QR API
                url = f"http://{get_lan_ip()}:{self.server.server_port}/?t={state.token}"
                body = qr_png_bytes(url)
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", len(body))
                self.end_headers()
                self.wfile.write(body)
            elif path == "/api/files":
                self._api_files()
            elif path == "/api/chat":
                self.send_json({"messages": state.chat_messages()})
            elif path.startswith("/api/download/"):
                self._api_download(path[len("/api/download/"):])
            else:
                self.send_error_json("Not Found", 404)

        def _serve_index(self):
            html = (HTML_PAGE
                    .replace("__LAN_IP__", get_lan_ip())
                    .replace("__PORT__", str(self.server.server_port))
                    .replace("__TOKEN_Q__",
                             "?t=" + urllib.parse.quote(state.token)))
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        def _api_files(self):
            files = []
            try:
                for name, size, mtime in state.list_files():
                    files.append({"name": name, "size": size,
                                  "modified": mtime, "is_dir": False})
            except Exception as e:  # noqa: BLE001
                self.send_error_json(str(e), 500)
                return
            self.send_json({"files": files})

        def _api_download(self, filename):
            name = self.safe_filename(filename)
            if not name:
                self.send_error_json("非法的文件名", 400)
                return
            filepath = self._file_path(name)
            if filepath is None or not filepath.is_file():
                self.send_error_json("文件不存在", 404)
                return
            try:
                size = filepath.stat().st_size
                mime = mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", size)
                quoted = urllib.parse.quote(name)
                self.send_header(
                    "Content-Disposition",
                    f"attachment; filename=\"{quoted}\"; filename*=UTF-8''{quoted}")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self._audit("download", path=name, size=size, ok=True)
                with open(filepath, "rb") as f:
                    while True:
                        chunk = f.read(CHUNK)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                pass

        # ---- POST ----
        def do_POST(self):
            path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
            if not self._check_auth():
                return
            if path in ("/api/upload", "/api/chat") and self._readonly():
                return
            if path == "/api/upload":
                self._api_upload()
            elif path == "/api/chat":
                self._api_chat()
            else:
                self.send_error_json("Not Found", 404)

        def _api_upload(self):
            name = self.safe_filename(self.headers.get("X-Filename", ""))
            if not name:
                self.send_error_json("缺少文件名", 400)
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                length = 0
            if length <= 0:
                self.send_error_json("没有文件内容", 400)
                return
            # 磁盘空间预检
            try:
                free = shutil.disk_usage(str(state.upload_dir)).free
                if length > free:
                    self.send_error_json(
                        f"磁盘空间不足，需要 {format_size(length)}，"
                        f"可用 {format_size(free)}", 400)
                    return
            except Exception:
                pass
            filepath = self._file_path(name)
            if filepath is None:
                self.send_error_json("非法的文件名", 400)
                return
            try:
                written = 0
                with open(filepath, "wb") as f:
                    while written < length:
                        chunk = self.rfile.read(min(CHUNK, length - written))
                        if not chunk:
                            break
                        f.write(chunk)
                        written += len(chunk)
                self._audit("upload", path=name, size=written, ok=True)
                self.send_json({"ok": True, "name": name, "size": written})
            except Exception as e:  # noqa: BLE001
                if filepath.exists():
                    try:
                        filepath.unlink()
                    except Exception:
                        pass
                self.send_error_json(f"上传失败: {e}", 500)

        def _api_chat(self):
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length <= 0:
                    self.send_error_json("没有消息内容", 400)
                    return
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                text = (data.get("message") or "").strip()
                if not text:
                    self.send_error_json("消息内容不能为空", 400)
                    return
                msg = {
                    "id": 0,
                    "nickname": (data.get("nickname") or "匿名用户")[:20],
                    "message": text[:2000],
                    "timestamp": time.time(),
                    "ip": self.client_address[0],
                }
                with state._chat_lock:
                    msg["id"] = len(state._chat) + 1
                    state._chat.append(msg)
                    if len(state._chat) > CHAT_MAX:
                        state._chat.pop(0)
                if state.on_chat:
                    try:
                        state.on_chat(msg)
                    except Exception:
                        pass
                self._audit("chat", ok=True)
                self.send_json({"ok": True, "id": msg["id"]})
            except Exception as e:  # noqa: BLE001
                self.send_error_json(f"发送失败: {e}", 500)

        # ---- DELETE ----
        def do_DELETE(self):
            if not self._check_auth():
                return
            if self._readonly():
                return
            path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
            if path.startswith("/api/delete/"):
                name = self.safe_filename(path[len("/api/delete/"):])
                filepath = self._file_path(name) if name else None
                if filepath is None or not filepath.exists():
                    self.send_error_json("文件不存在", 404)
                    return
                try:
                    filepath.unlink()
                    self._audit("delete", path=name, ok=True)
                    self.send_json({"ok": True})
                except Exception as e:  # noqa: BLE001
                    self.send_error_json(f"删除失败: {e}", 500)
            else:
                self.send_error_json("Not Found", 404)

    return TransferHandler
