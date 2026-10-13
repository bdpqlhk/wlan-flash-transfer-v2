# -*- coding: utf-8 -*-
"""pytest 根配置:把仓库根加入 sys.path, 保证 `import lan_transfer` 可用。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
