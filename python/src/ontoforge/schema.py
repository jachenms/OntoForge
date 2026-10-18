"""对象类型 / 属性 / 共享属性 CRUD(CORE Task 2)。"""
from __future__ import annotations

from ._common import BASE_TYPES, NAME_RE, State, Result, uid
from .state import schema_of


def _bump(state: State) -> None:
    state["meta"]["rev"] += 1


def _find_type(state: State, type_id: str) -> State | None:
    return next((t for t in schema_of(state)["objectTypes"] if t["id"] == type_id), None)


def type_by_name(state: State, name: str) -> State | None:
    return next((t for t in schema_of(state)["objectTypes"] if t["name"] == name), None)


def add_object_type(state: State, defn: State) -> Result:
    s = schema_of(state)
    if not defn or not NAME_RE.match(defn.get("name") or ""):
        return {"ok": False, "error": "name 需为小写字母开头的蛇形标识"}
    if any(t["name"] == defn["name"] for t in s["objectTypes"]):
        return {"ok": False, "error": "对象类型 name 冲突: " + defn["name"]}
    t = {
        "id": uid("ot"), "name": defn["name"], "label": defn.get("label") or defn["name"],
        "icon": defn.get("icon") or "📦", "color": defn.get("color") or "#2563eb",
        "primaryKey": defn.get("primaryKey") or "", "properties": [], "sharedPropRefs": [],
    }
    if t["primaryKey"]:
        return {"ok": False, "error": "primaryKey 需在建属性后通过 update_object_type 设置"}
    s["objectTypes"].append(t)
    _bump(state)
    return {"ok": True, "id": t["id"]}


def update_object_type(state: State, type_id: str, patch: State) -> Result:
    t = _find_type(state, type_id)
    if not t:
        return {"ok": False, "error": "对象类型不存在"}
    for k in ["label", "icon", "color"]:
        if k in patch:
            t[k] = patch[k]
    if "primaryKey" in patch:
        pk = patch["primaryKey"]
        if pk != "" and not any(p["name"] == pk for p in t["properties"]):
            return {"ok": False, "error": "primaryKey 须为已有属性 name"}
        t["primaryKey"] = pk
    _bump(state)
    return {"ok": True}


def delete_object_type(state: State, type_id: str) -> Result:
    s = schema_of(state)
    t = _find_type(state, type_id)
    if not t:
        return {"ok": False, "error": "对象类型不存在"}
    if any(o["__type"] == t["name"] for o in state["data"]["objects"]):
        return {"ok": False, "error": "存在该类型实例,不可删除"}
    lt = next((l for l in s["linkTypes"] if l["from"] == t["name"] or l["to"] == t["name"]), None)
    if lt:
        return {"ok": False, "error": "被链接类型引用: " + lt["name"]}
    at = next((a for a in s["actionTypes"]
               if any(r.get("type") == t["name"] for r in a.get("targets", []))
               or any(e.get("objectType") == t["name"] for e in a.get("edits", []))), None)
    if at:
        return {"ok": False, "error": "被动作类型引用: " + at["name"]}
    s["objectTypes"] = [x for x in s["objectTypes"] if x["id"] != type_id]
    _bump(state)
    return {"ok": True}


def add_property(state: State, type_id: str, prop: State) -> Result:
    t = _find_type(state, type_id)
    if not t:
        return {"ok": False, "error": "对象类型不存在"}
    if not NAME_RE.match(prop.get("name") or ""):
        return {"ok": False, "error": "属性 name 需为蛇形标识"}
    if any(p["name"] == prop["name"] for p in t["properties"]):
        return {"ok": False, "error": "属性重名: " + prop["name"]}
    if prop.get("baseType") not in BASE_TYPES:
        return {"ok": False, "error": "非法 baseType"}
    if prop["baseType"] == "enum" and not prop.get("enumValues"):
        return {"ok": False, "error": "enum 需给 enumValues"}
    t["properties"].append({
        "name": prop["name"], "label": prop.get("label") or prop["name"],
        "baseType": prop["baseType"], "enumValues": prop.get("enumValues"),
        "required": bool(prop.get("required")), "formatting": prop.get("formatting") or "",
    })
    _bump(state)
    return {"ok": True}


def update_property(state: State, type_id: str, prop_name: str, patch: State) -> Result:
    t = _find_type(state, type_id)
    if not t:
        return {"ok": False, "error": "对象类型不存在"}
    p = next((p for p in t["properties"] if p["name"] == prop_name), None)
    if not p:
        return {"ok": False, "error": "属性不存在"}
    if "name" in patch and patch["name"] != prop_name:
        return {"ok": False, "error": "不允许改属性 name"}
    for k in ["label", "baseType", "enumValues", "required", "formatting"]:
        if k in patch:
            p[k] = patch[k]
    if p["baseType"] == "enum" and not p.get("enumValues"):
        return {"ok": False, "error": "enum 需给 enumValues"}
    _bump(state)
    return {"ok": True}


def delete_property(state: State, type_id: str, prop_name: str) -> Result:
    t = _find_type(state, type_id)
    if not t:
        return {"ok": False, "error": "对象类型不存在"}
    if t.get("primaryKey") == prop_name:
        return {"ok": False, "error": "不可删除主键属性"}
    t["properties"] = [p for p in t["properties"] if p["name"] != prop_name]
    _bump(state)
    return {"ok": True}


def add_shared_prop(state: State, defn: State) -> Result:
    s = schema_of(state)
    if not NAME_RE.match(defn.get("name") or ""):
        return {"ok": False, "error": "name 需为蛇形标识"}
    if any(p["name"] == defn["name"] for p in s["sharedProps"]):
        return {"ok": False, "error": "共享属性重名"}
    if defn.get("baseType") not in BASE_TYPES:
        return {"ok": False, "error": "非法 baseType"}
    sp = {"id": uid("sp"), "name": defn["name"], "label": defn.get("label") or defn["name"],
          "baseType": defn["baseType"], "enumValues": defn.get("enumValues")}
    s["sharedProps"].append(sp)
    _bump(state)
    return {"ok": True, "id": sp["id"]}


def attach_shared_prop(state: State, type_id: str, sp_id: str) -> Result:
    t = _find_type(state, type_id)
    if not t:
        return {"ok": False, "error": "对象类型不存在"}
    if not any(p["id"] == sp_id for p in schema_of(state)["sharedProps"]):
        return {"ok": False, "error": "共享属性不存在"}
    if sp_id in t["sharedPropRefs"]:
        return {"ok": False, "error": "已挂载"}
    t["sharedPropRefs"].append(sp_id)
    _bump(state)
    return {"ok": True}


def detach_shared_prop(state: State, type_id: str, sp_id: str) -> Result:
    t = _find_type(state, type_id)
    if not t:
        return {"ok": False, "error": "对象类型不存在"}
    t["sharedPropRefs"] = [x for x in t["sharedPropRefs"] if x != sp_id]
    _bump(state)
    return {"ok": True}


def delete_shared_prop(state: State, sp_id: str) -> Result:
    s = schema_of(state)
    if not any(p["id"] == sp_id for p in s["sharedProps"]):
        return {"ok": False, "error": "共享属性不存在"}
    used_by = [t["name"] for t in s["objectTypes"] if sp_id in t.get("sharedPropRefs", [])]
    if used_by:
        return {"ok": False, "error": "被 " + "、".join(used_by) + " 挂载中"}
    s["sharedProps"] = [p for p in s["sharedProps"] if p["id"] != sp_id]
    _bump(state)
    return {"ok": True}
