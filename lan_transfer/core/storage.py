# -*- coding: utf-8 -*-
"""元数据存储:配置 / 设备 / 审计日志。

全部为标准库实现(JSON + JSONL 追加),零第三方依赖。
- 配置与设备持久化在 <root>/ 下(默认 ~/.wlan-flash-transfer/),
  不随共享目录切换而丢失
- 审计日志为追加式 audit.jsonl,一行一条记录
- 所有写操作均为原子写(tmp + os.replace),避免写一半损坏

文件本体(共享的文件)永远以文件系统为准;这里只存索引/配置/日志,
删掉整个目录也不丢共享文件,仅丢失配置与历史。
"""
from __future__ import annotations

import json
import os
import secrets
import threading
import time
from pathlib import Path

CONFIG_NAME = "config.json"
DEVICES_NAME = "devices.json"
AUDIT_NAME = "audit.jsonl"

_DEFAULT_CONFIG = {
    "port": 8765,
    "mode": "full",           # full: 上传/下载/删除/聊天; readonly: 仅下载
    "require_pairing": True,  # True: 请求需带配对令牌
    "token": "",              # 首次初始化自动生成
    "share_dir": "",          # 上次使用的共享目录(记忆)
}


def generate_token() -> str:
    """8 字符配对令牌(URL 安全, 如 Kx3_qT9z)。"""
    return secrets.token_urlsafe(6)[:8]


class Storage:
    """线程安全的元数据存储(一个实例对应一个数据目录)。"""

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else Path.home() / ".wlan-flash-transfer"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._config = self._load_config()

    # ---------------- 配置 ----------------
    def _load_config(self) -> dict:
        cfg = dict(_DEFAULT_CONFIG)
        path = self.root / CONFIG_NAME
        if path.exists():
            try:
                cfg.update(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                pass  # 损坏则回退默认
        if not cfg.get("token"):
            cfg["token"] = generate_token()
            self._write_config(cfg)
        return cfg

    @property
    def config(self) -> dict:
        return dict(self._config)  # 拷贝, 防外部直接改

    def update_config(self, **kw) -> None:
        with self._lock:
            self._config.update(kw)
            self._write_config(self._config)

    def _write_config(self, cfg: dict) -> None:
        self._save_json_atomic(CONFIG_NAME, cfg)

    # ---------------- 设备 ----------------
    def touch_device(self, device_id: str, name: str = "", ip: str = "") -> None:
        if not device_id:
            return
        with self._lock:
            path = self.root / DEVICES_NAME
            devices = {}
            if path.exists():
                try:
                    devices = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    devices = {}
            now = time.time()
            info = devices.get(device_id, {"first_seen": now})
            info.update({"name": name or info.get("name", "未命名设备"),
                         "ip": ip, "last_seen": now})
            devices[device_id] = info
            self._save_json_atomic(DEVICES_NAME, devices)

    def devices(self) -> dict:
        path = self.root / DEVICES_NAME
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    # ---------------- 审计 ----------------
    def append_audit(self, record: dict) -> None:
        entry = {"ts": time.time(), **record}
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with self._lock:
            with open(self.root / AUDIT_NAME, "a", encoding="utf-8") as f:
                f.write(line)

    def audit_records(self, limit: int = 5000) -> list[dict]:
        path = self.root / AUDIT_NAME
        if not path.exists():
            return []
        out = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        pass
        return out[-limit:]

    # ---------------- 内部 ----------------
    def _save_json_atomic(self, name: str, data) -> None:
        tmp = self.root / (name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        os.replace(tmp, self.root / name)
