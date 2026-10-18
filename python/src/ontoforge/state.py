"""状态构造、序列化与校验(CORE Task 1)。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ._common import State, Result


def now_iso() -> str:
    """JS `new Date().toISOString()` 的 Python 对应(UTC,毫秒)。"""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def create_empty_state() -> State:
    return {
        "v": 1,
        "meta": {"ontologyName": "未命名本体", "createdAt": now_iso(), "rev": 0},
        "branch": {"current": "main", "list": [
            {"name": "main", "baseRev": 0, "status": "active", "createdAt": now_iso()},
        ]},
        "schemas": {"main": {"objectTypes": [], "linkTypes": [], "actionTypes": [], "sharedProps": []}},
        "proposals": [],
        "data": {"objects": [], "links": []},
        "audit": [],
        "notices": [],
        "ui": {"view": "discover", "sel": None, "favorites": [], "recent": []},
    }


def schema_of(state: State) -> State:
    """当前分支的 schema(建模一切改动都落在它上面)。"""
    return state["schemas"][state["branch"]["current"]]


def serialize(state: State) -> str:
    return json.dumps({"app": "ontoforge", "v": 1, "state": state}, ensure_ascii=False, indent=2)


def validate_state(s: Any) -> list[str]:
    errs: list[str] = []
    if not isinstance(s, dict):
        return ["state 不是对象"]
    if s.get("v") != 1:
        errs.append("state.v 必须为 1")
    if not isinstance(s.get("meta"), dict) or not isinstance(s["meta"].get("ontologyName"), str):
        errs.append("缺 meta.ontologyName")
    branch = s.get("branch")
    if not isinstance(branch, dict) or not branch.get("current") or not isinstance(branch.get("list"), list):
        errs.append("缺 branch 结构")
    schemas = s.get("schemas")
    if not isinstance(schemas, dict):
        errs.append("缺 schemas")
    elif branch and branch.get("current") and branch["current"] not in schemas:
        errs.append("当前分支无 schema: " + str(branch.get("current")))
    if isinstance(schemas, dict) and isinstance(branch, dict) and isinstance(schemas.get(branch.get("current")), dict):
        cur = schemas[branch["current"]]
        for k in ["objectTypes", "linkTypes", "actionTypes", "sharedProps"]:
            if not isinstance(cur.get(k), list):
                errs.append("schema." + k + " 非数组")
    data = s.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("objects"), list) or not isinstance(data.get("links"), list):
        errs.append("缺 data.objects/links")
    if not isinstance(s.get("audit"), list):
        errs.append("audit 非数组")
    if not isinstance(s.get("proposals"), list):
        errs.append("proposals 非数组")
    if not isinstance(s.get("notices"), list):
        errs.append("notices 非数组")
    return errs


def deserialize(text: str) -> Result:
    try:
        o = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        return {"ok": False, "error": "JSON 解析失败: " + str(e)}
    if not isinstance(o, dict) or o.get("app") != "ontoforge":
        return {"ok": False, "error": "不是 OntoForge 导出文件"}
    errs = validate_state(o.get("state"))
    if errs:
        return {"ok": False, "error": errs[0], "errors": errs}
    return {"ok": True, "state": o["state"]}
