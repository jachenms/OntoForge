"""分支 / diff / 提案合并(CORE Task 7;仅隔离 schema,实例数据全局)。"""
from __future__ import annotations

import json

from ._common import BRANCH_RE, State, Result, clone, uid
from .state import now_iso, schema_of
from .schema import _bump


def create_branch(state: State, name: str) -> Result:
    if not BRANCH_RE.match(name or ""):
        return {"ok": False, "error": "分支名需为小写字母/数字/连字符"}
    if name in state["schemas"]:
        return {"ok": False, "error": "分支已存在"}
    state["schemas"][name] = clone(state["schemas"]["main"])
    state["branch"]["list"].append(
        {"name": name, "baseRev": state["meta"]["rev"], "status": "active", "createdAt": now_iso()})
    state["branch"]["current"] = name
    return {"ok": True}


def switch_branch(state: State, name: str) -> Result:
    if name not in state["schemas"]:
        return {"ok": False, "error": "分支不存在"}
    state["branch"]["current"] = name
    return {"ok": True}


def _diff_coll(a: list[State], b: list[State]) -> State:
    added = [x for x in b if not any(y["name"] == x["name"] for y in a)]
    removed = [x for x in a if not any(y["name"] == x["name"] for y in b)]
    changed = []
    for y in b:
        x = next((z for z in a if z["name"] == y["name"]), None)
        if x:
            def strip(o: State) -> str:
                c = clone(o)
                c.pop("id", None)
                return json.dumps(c, ensure_ascii=False, sort_keys=True)
            if strip(x) != strip(y):
                changed.append({"name": y["name"], "before": x, "after": y})
    return {"added": added, "removed": removed, "changed": changed}


def diff_schemas(a: State, b: State) -> State:
    """schema a → b 的差异(按 name 对齐,id 不参与比较)。"""
    return {k: _diff_coll(a[k], b[k])
            for k in ["objectTypes", "linkTypes", "actionTypes", "sharedProps"]}


def diff_empty(d: State) -> bool:
    return all(not c["added"] and not c["removed"] and not c["changed"] for c in d.values())


def propose_merge(state: State, branch_name: str) -> Result:
    if state["branch"]["current"] != "main":
        return {"ok": False, "error": "请在 main 分支发起提案"}
    if branch_name not in state["schemas"]:
        return {"ok": False, "error": "分支不存在"}
    if branch_name == "main":
        return {"ok": False, "error": "main 无需提案"}
    if any(p["branch"] == branch_name and p["status"] == "open" for p in state["proposals"]):
        return {"ok": False, "error": "该分支已有待审提案"}
    diff = diff_schemas(state["schemas"]["main"], state["schemas"][branch_name])
    if diff_empty(diff):
        return {"ok": False, "error": "无变更"}
    p = {"id": uid("pr"), "branch": branch_name, "diff": diff, "status": "open", "createdAt": now_iso()}
    state["proposals"].append(p)
    return {"ok": True, "proposalId": p["id"]}


def merge_proposal(state: State, proposal_id: str) -> Result:
    p = next((x for x in state["proposals"] if x["id"] == proposal_id), None)
    if not p or p["status"] != "open":
        return {"ok": False, "error": "提案不存在或已处理"}
    state["schemas"]["main"] = clone(state["schemas"][p["branch"]])
    _bump(state)
    p["status"] = "merged"
    p["mergedAt"] = now_iso()
    b = next((x for x in state["branch"]["list"] if x["name"] == p["branch"]), None)
    if b:
        b["status"] = "merged"
    return {"ok": True}


def reject_proposal(state: State, proposal_id: str) -> Result:
    p = next((x for x in state["proposals"] if x["id"] == proposal_id), None)
    if not p or p["status"] != "open":
        return {"ok": False, "error": "提案不存在或已处理"}
    p["status"] = "rejected"
    p["rejectedAt"] = now_iso()
    return {"ok": True}
