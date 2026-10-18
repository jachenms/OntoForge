"""链接类型 / 链接实例(CORE Task 3)。"""
from __future__ import annotations

from ._common import CARDINALITIES, NAME_RE, State, Result, uid
from .state import schema_of
from .schema import _bump, type_by_name


def add_link_type(state: State, defn: State) -> Result:
    s = schema_of(state)
    if not NAME_RE.match(defn.get("name") or ""):
        return {"ok": False, "error": "name 需为蛇形标识"}
    if any(l["name"] == defn["name"] for l in s["linkTypes"]):
        return {"ok": False, "error": "链接类型重名"}
    if not type_by_name(state, defn.get("from") or ""):
        return {"ok": False, "error": "from 类型不存在: " + str(defn.get("from"))}
    if not type_by_name(state, defn.get("to") or ""):
        return {"ok": False, "error": "to 类型不存在: " + str(defn.get("to"))}
    if defn.get("cardinality") not in CARDINALITIES:
        return {"ok": False, "error": "非法 cardinality"}
    lt = {"id": uid("lt"), "name": defn["name"], "label": defn.get("label") or defn["name"],
          "from": defn["from"], "to": defn["to"], "cardinality": defn["cardinality"],
          "keyMapping": defn.get("keyMapping") or {"fromKey": "", "toKey": ""}}
    s["linkTypes"].append(lt)
    _bump(state)
    return {"ok": True, "id": lt["id"]}


def update_link_type(state: State, link_type_id: str, patch: State) -> Result:
    lt = next((l for l in schema_of(state)["linkTypes"] if l["id"] == link_type_id), None)
    if not lt:
        return {"ok": False, "error": "链接类型不存在"}
    if "from" in patch or "to" in patch:
        return {"ok": False, "error": "不可改 from/to"}
    if "cardinality" in patch:
        if patch["cardinality"] not in CARDINALITIES:
            return {"ok": False, "error": "非法 cardinality"}
        lt["cardinality"] = patch["cardinality"]
    if "label" in patch:
        lt["label"] = patch["label"]
    if "keyMapping" in patch:
        lt["keyMapping"] = patch["keyMapping"]
    _bump(state)
    return {"ok": True}


def delete_link_type(state: State, link_type_id: str) -> Result:
    s = schema_of(state)
    if any(l["__type"] == link_type_id for l in state["data"]["links"]):
        return {"ok": False, "error": "存在该类型链接实例,不可删除"}
    s["linkTypes"] = [l for l in s["linkTypes"] if l["id"] != link_type_id]
    _bump(state)
    return {"ok": True}


def create_link(state: State, link_type_id: str, from_obj_id: str, to_obj_id: str) -> Result:
    lt = next((l for l in schema_of(state)["linkTypes"] if l["id"] == link_type_id), None)
    if not lt:
        return {"ok": False, "error": "链接类型不存在"}
    fo = next((o for o in state["data"]["objects"] if o["__id"] == from_obj_id), None)
    to = next((o for o in state["data"]["objects"] if o["__id"] == to_obj_id), None)
    if not fo or not to:
        return {"ok": False, "error": "端点对象不存在"}
    if fo["__type"] != lt["from"] or to["__type"] != lt["to"]:
        return {"ok": False, "error": f"端点类型须为 {lt['from']} → {lt['to']}"}
    links = state["data"]["links"]
    if any(l["__type"] == link_type_id and l["from"] == from_obj_id and l["to"] == to_obj_id for l in links):
        return {"ok": False, "error": "链接已存在"}
    from_side = lambda l: l["__type"] == link_type_id and l["from"] == from_obj_id  # noqa: E731
    to_side = lambda l: l["__type"] == link_type_id and l["to"] == to_obj_id  # noqa: E731
    if lt["cardinality"] in ("1:1", "N:1") and any(from_side(l) for l in links):
        return {"ok": False, "error": "基数约束:from 侧已有关联"}
    if lt["cardinality"] in ("1:1", "1:N") and any(to_side(l) for l in links):
        return {"ok": False, "error": "基数约束:to 侧已有关联"}
    link = {"__id": uid("lk"), "__type": link_type_id, "from": from_obj_id, "to": to_obj_id}
    links.append(link)
    return {"ok": True, "id": link["__id"]}


def delete_link(state: State, link_id: str) -> Result:
    n = len(state["data"]["links"])
    state["data"]["links"] = [l for l in state["data"]["links"] if l["__id"] != link_id]
    return {"ok": True} if len(state["data"]["links"]) < n else {"ok": False, "error": "链接不存在"}


def links_of(state: State, link_type_id: str) -> list[State]:
    return [l for l in state["data"]["links"] if l["__type"] == link_type_id]
