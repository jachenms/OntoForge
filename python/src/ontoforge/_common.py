"""OntoForge 领域核心内部共享件:uid / clone / 常量 / JS 语义工具。

对应 ontoforge.html `<script id="core">` 段开头的工具区。
"""
from __future__ import annotations

import itertools
import random
import re
import time
from copy import deepcopy
from typing import Any

# JSON 兼容状态(与 JS 侧 localStorage 持久化格式一致)
State = dict[str, Any]
Result = dict[str, Any]

_seq = itertools.count()
_B36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def _b36(n: int) -> str:
    if n <= 0:
        return "0"
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = _B36[r] + out
    return out


def uid(prefix: str) -> str:
    """与 JS CORE 同形的 id:`<p>_<毫秒ts36>_<序号36><随机4位>`。"""
    rand = "".join(random.choices(_B36, k=4))
    return f"{prefix}_{_b36(int(time.time() * 1000))}_{_b36(next(_seq))}{rand}"


def clone(o: Any) -> Any:
    """深拷贝;状态一律 JSON 兼容,等价于 JS 的 JSON.parse(JSON.stringify(o))。"""
    return deepcopy(o)


BASE_TYPES = ["string", "number", "boolean", "date", "enum"]
RULE_OPS = ["eq", "neq", "in", "notIn", "gt", "lt", "ge", "le", "contains"]
CARDINALITIES = ["1:1", "1:N", "N:1", "M:N"]
EDIT_OPS = ["set", "create", "delete", "addLink", "removeLink"]
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
BRANCH_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def js_str(v: Any) -> str:
    """对齐 JS String(v) 的关键差异:true/false/null。"""
    if v is None:
        return ""
    if v is True:
        return "true"
    if v is False:
        return "false"
    return str(v)
