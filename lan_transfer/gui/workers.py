# -*- coding: utf-8 -*-
"""后台线程执行器。

Qt 控件只能在主线程操作;文件列表扫描、删除等可能耗时,
经 Worker 放后台线程,结果经 done 信号(跨线程自动排队)回主线程。
"""
from __future__ import annotations

import traceback

from PyQt6.QtCore import QThread, pyqtSignal


class Worker(QThread):
    """执行 fn() 并把结果(或异常实例)经 done 信号发回主线程。"""

    done = pyqtSignal(object)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            result = e
        self.done.emit(result)
