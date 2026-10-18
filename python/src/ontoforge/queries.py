"""查询 / 搜索 / 关联遍历 / 审计统计(CORE Task 6)。"""
from __future__ import annotations

from datetime import date, timedelta

from ._common import State
from .state import schema_of
from .schema import type_by_name


def objects_of_type(state: State, type_name: str) -> list[State]:
    return [o for o in state["data"]["objects"] if o["__type"] == type_name]


def object_label(state: State, obj: State) -> str:
    t = type_by_name(state, obj["__type"])
    label = obj["props"].get("name") or obj["props"].get("title")
    if not label and t and t.get("primaryKey"):
        label = obj["props"].get(t["primaryKey"])
    return label or obj["__id"]


def search_objects(state: State, type_name: str, q: str) -> list[State]:
    all_ = objects_of_type(state, type_name)
    if not q:
        return all_
    needle = str(q).lower()
    return [o for o in all_
            if any(isinstance(v, str) and needle in v.lower() for v in o["props"].values())]


def linked_objects(state: State, object_id: str) -> list[State]:
    """双向遍历:返回 [{linkType, direction: 'out'|'in', object}]。"""
    s = schema_of(state)
    out: list[State] = []
    for l in state["data"]["links"]:
        lt = next((x for x in s["linkTypes"] if x["id"] == l["__type"]), None)
        if not lt:
            continue
        if l["from"] == object_id:
            o = next((o for o in state["data"]["objects"] if o["__id"] == l["to"]), None)
            if o:
                out.append({"linkType": lt, "direction": "out", "object": o})
        if l["to"] == object_id:
            o = next((o for o in state["data"]["objects"] if o["__id"] == l["from"]), None)
            if o:
                out.append({"linkType": lt, "direction": "in", "object": o})
    return out


def audit_for(state: State, filter: State) -> list[State]:
    """按 actionId / objectId 过滤审计;objectId 命中 diff 文本或对象类型名。"""
    def _hit(e: State) -> bool:
        if filter.get("actionId") and e["actionId"] != filter["actionId"]:
            return False
        if filter.get("objectId"):
            oid = filter["objectId"]
            hit = any(oid in d for d in e["diff"])
            obj = next((o for o in state["data"]["objects"] if o["__id"] == oid), None)
            hit_role = obj and any(obj["__type"] in d for d in e["diff"])
            if not hit and not hit_role:
                return False
        return True
    return [e for e in state["audit"] if _hit(e)]


def usage_by_day(state: State, action_id: str, days: int = 30) -> list[State]:
    """最近 N 天(含今天)的逐日执行次数,供用量柱状图。"""
    counts: dict[str, int] = {}
    for e in state["audit"]:
        if e["actionId"] == action_id:
            d = e["ts"][:10]
            counts[d] = counts.get(d, 0) + 1
    today = date.today()
    return [{"day": (today - timedelta(days=i)).isoformat(),
             "count": counts.get((today - timedelta(days=i)).isoformat(), 0)}
            for i in range(days - 1, -1, -1)]


def unread_notices(state: State) -> int:
    return sum(1 for n in state["notices"] if not n["read"])


def mark_notices_read(state: State) -> None:
    for n in state["notices"]:
        n["read"] = True
