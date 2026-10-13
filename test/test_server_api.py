# -*- coding: utf-8 -*-
"""TransferServer API 集成测试(鉴权 / 上传 / 下载 / 删除 / 聊天 / 路径安全)。

运行: pytest test/test_server_api.py -q
"""
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from lan_transfer.core.server import TransferServer
from lan_transfer.core.storage import Storage


@pytest.fixture()
def server(tmp_path):
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    srv = TransferServer(tmp_path / "share", port,
                         storage=Storage(tmp_path / "meta"))
    srv.start()
    assert srv.started.wait(5), srv.last_error
    srv.port = port
    yield srv
    srv.stop()


def _req(srv, method, path, data=None, headers=None, token=True):
    h = dict(headers or {})
    if token:
        h["X-Token"] = srv.token
    r = urllib.request.Request(f"http://127.0.0.1:{srv.port}{path}",
                               data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _q(name):
    return urllib.parse.quote(name)


# ------------------------------------------------------------------ #
def test_auth_required(server):
    st, _ = _req(server, "GET", "/api/files", token=False)
    assert st == 401
    st, _ = _req(server, "GET", "/api/files",
                 headers={"X-Token": "wrong-token"}, token=False)
    assert st == 401


def test_index_always_served(server):
    st, _ = _req(server, "GET", "/", token=False)
    assert st == 200


def test_upload_download_roundtrip(server):
    body = "你好 LAN Transfer v2.1".encode("utf-8") * 10
    name = "测试文件.txt"
    st, out = _req(server, "POST", "/api/upload", data=body,
                   headers={"X-Filename": _q(name)})
    assert st == 200 and json.loads(out)["ok"]
    st, out = _req(server, "GET", "/api/files")
    files = json.loads(out)["files"]
    assert files and files[0]["name"] == name and files[0]["size"] == len(body)
    st, out = _req(server, "GET", f"/api/download/{_q(name)}")
    assert st == 200 and out == body


def test_delete(server):
    _req(server, "POST", "/api/upload", data=b"del-me",
         headers={"X-Filename": "del.txt"})
    st, _ = _req(server, "DELETE", "/api/delete/del.txt")
    assert st == 200
    st, out = _req(server, "GET", "/api/files")
    assert json.loads(out)["files"] == []


def test_path_traversal_blocked(server):
    st, _ = _req(server, "GET", "/api/download/..%2F..%2Fmain.py")
    assert st != 200
    st, _ = _req(server, "DELETE", "/api/delete/..%2Fmain.py")
    assert st != 200
    st, _ = _req(server, "POST", "/api/upload", data=b"x",
                 headers={"X-Filename": "..%2Fevil.txt"})
    assert st == 400


def test_bad_filename_rejected(server):
    st, _ = _req(server, "POST", "/api/upload", data=b"x",
                 headers={"X-Filename": ""})
    assert st == 400


def test_readonly_mode_blocks_write(server):
    server.storage.update_config(mode="readonly")
    st, _ = _req(server, "POST", "/api/upload", data=b"x",
                 headers={"X-Filename": "a.txt"})
    assert st == 403
    st, _ = _req(server, "POST", "/api/chat",
                 data=json.dumps({"nickname": "n", "message": "m"}).encode())
    assert st == 403
    st, _ = _req(server, "DELETE", "/api/delete/anything.txt")
    assert st == 403


def test_chat_roundtrip(server):
    got = []
    server.on_chat = got.append
    st, _ = _req(server, "POST", "/api/chat",
                 data=json.dumps({"nickname": "QA", "message": "hello"}).encode())
    assert st == 200 and got and got[-1]["message"] == "hello"
    st, out = _req(server, "GET", "/api/chat")
    assert json.loads(out)["messages"][-1]["nickname"] == "QA"


def test_qr_route_png(server):
    st, out = _req(server, "GET", "/qr")
    assert st == 200 and out[:8] == b"\x89PNG\r\n\x1a\n"


def test_audit_written(server):
    _req(server, "POST", "/api/upload", data=b"abc",
         headers={"X-Filename": "a.txt"})
    recs = server.storage.audit_records()
    assert any(r.get("action") == "upload" and r.get("ok") for r in recs)


def test_config_persisted(server, tmp_path):
    server.storage.update_config(token="fixed-token", mode="readonly")
    st, _ = _req(server, "GET", "/api/files", token=False)   # 旧令牌/无令牌 → 401
    assert st == 401
    st, out = _req(server, "GET", "/api/config")
    assert json.loads(out)["readonly"] is True
