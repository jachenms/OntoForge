"""动作类型 CRUD / 模板渲染 / runAction 执行引擎(CORE Task 4-5)。"""
from __future__ import annotations

import re
from datetime import date

from ._common import (BASE_TYPES, EDIT_OPS, NAME_RE, RULE_OPS, State, Result,
                      clone, js_str, uid)
from .state import schema_of, now_iso
from .schema import _bump, type_by_name

_TPL_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def render_template(tpl, ctx: State):
    """`{{ a.b.c }}` 路径插值;缺路径给空串。非字符串原样返回。"""
    if not isinstance(tpl, str):
        return tpl

    def _sub(m: re.Match) -> str:
        v = ctx
        for k in m.group(1).strip().split("."):
            if v is None:
                break
            v = v.get(k) if isinstance(v, dict) else None
        return js_str(v)

    return _TPL_RE.sub(_sub, tpl)


def _validate_action_def(state: State, defn: State, exclude_id: str | None) -> str | None:
    s = schema_of(state)
    if not NAME_RE.match(defn.get("name") or ""):
        return "name 需为蛇形标识"
    if any(a["name"] == defn["name"] and a["id"] != exclude_id for a in s["actionTypes"]):
        return "动作类型重名"
    roles: set[str] = set()
    for t in defn.get("targets", []):
        if not NAME_RE.match(t.get("role") or ""):
            return "target role 需为蛇形标识"
        if t["role"] in roles:
            return "target role 重复: " + t["role"]
        roles.add(t["role"])
        if not type_by_name(state, t.get("type") or ""):
            return "target 类型不存在: " + str(t.get("type"))
    pnames: set[str] = set()
    for p in defn.get("params", []):
        if not NAME_RE.match(p.get("name") or ""):
            return "参数 name 需为蛇形标识"
        if p["name"] in pnames:
            return "参数重名: " + p["name"]
        pnames.add(p["name"])
        if p.get("type") not in BASE_TYPES:
            return "参数非法 type: " + str(p.get("type"))
        if p["type"] == "enum" and not p.get("enumValues"):
            return "enum 参数需 enumValues"
    for r in defn.get("rules", []):
        if r.get("op") not in RULE_OPS:
            return "规则非法 op: " + str(r.get("op"))
    for e in defn.get("edits", []):
        if e.get("op") not in EDIT_OPS:
            return "edit 非法 op: " + str(e.get("op"))
        if e["op"] == "create" and (not e.get("objectType") or not isinstance(e.get("props"), dict)):
            return "create edit 需 objectType+props"
        if e["op"] == "create" and not type_by_name(state, e["objectType"]):
            return "create 的类型不存在: " + e["objectType"]
        if e["op"] in ("addLink", "removeLink") and not (e.get("linkType") and e.get("from") and e.get("to")):
            return e["op"] + " 需 linkType+from+to"
        if e["op"] in ("addLink", "removeLink") and e.get("linkType") and not any(
                l["id"] == e["linkType"] or l["name"] == e["linkType"] for l in s["linkTypes"]):
            return "linkType 不存在: " + e["linkType"]
    for f in defn.get("sideEffects", []):
        if f.get("type") not in ("notify", "webhookLog"):
            return "非法副作用: " + str(f.get("type"))
    return None


def add_action_type(state: State, defn: State) -> Result:
    err = _validate_action_def(state, defn, None)
    if err:
        return {"ok": False, "error": err}
    at = {"id": uid("at"), "name": defn["name"], "label": defn.get("label") or defn["name"],
          "targets": defn.get("targets", []), "params": defn.get("params", []),
          "rules": defn.get("rules", []),
          "submissionCriteria": defn.get("submissionCriteria") or {"requireConfirm": False},
          "edits": defn.get("edits", []), "sideEffects": defn.get("sideEffects", [])}
    schema_of(state)["actionTypes"].append(at)
    _bump(state)
    return {"ok": True, "id": at["id"]}


def update_action_type(state: State, action_id: str, patch: State) -> Result:
    s = schema_of(state)
    at = next((a for a in s["actionTypes"] if a["id"] == action_id), None)
    if not at:
        return {"ok": False, "error": "动作类型不存在"}
    merged = {**at, **patch, "id": at["id"], "name": at["name"]}
    err = _validate_action_def(state, merged, action_id)
    if err:
        return {"ok": False, "error": err}
    at.update(merged)
    _bump(state)
    return {"ok": True}


def delete_action_type(state: State, action_id: str) -> Result:
    s = schema_of(state)
    s["actionTypes"] = [a for a in s["actionTypes"] if a["id"] != action_id]
    _bump(state)
    return {"ok": True}


# ── runAction 执行引擎 ──

def _today() -> str:
    return date.today().isoformat()


def _mk_ctx(state: State, at: State, params: State, targets: State) -> Result:
    resolved: State = {}
    for t in at["targets"]:
        oid = targets.get(t["role"])
        obj = next((o for o in state["data"]["objects"] if o["__id"] == oid), None)
        if not obj:
            return {"error": "target 对象不存在: " + t["role"]}
        if obj["__type"] != t["type"]:
            return {"error": f"target {t['role']} 须为 {t['type']}"}
        resolved[t["role"]] = obj
    roles = list(resolved.keys())
    return {"ctx": {"param": params, "targets": resolved,
                    "target": resolved[roles[0]] if roles else None, "now": _today()}}


def _render_ctx(ctx: State) -> State:
    """每次渲染提供新 auto id(JS 侧为 getter,每次读取生成;此处每次调用生成,按渲染粒度等价)。"""
    return {**ctx, "auto": uid("obj")}


def _validate_params(at: State, params: State) -> str | None:
    for p in at["params"]:
        v = params.get(p["name"])
        if v is None or v == "":
            if p.get("required"):
                return "参数必填: " + p["name"]
            continue
        if p["type"] == "number":
            try:
                float(v)
            except (TypeError, ValueError):
                return "参数须为数字: " + p["name"]
        if p["type"] == "enum" and v not in (p.get("enumValues") or []):
            return "参数取值非法: " + p["name"]
    return None


def _rule_left(ctx: State, target: str, field: str):
    if target == "param":
        return ctx["param"].get(field)
    obj = ctx["targets"].get(target)
    return obj["props"].get(field) if obj else None


def _check_rules(at: State, ctx: State) -> str | None:
    for r in at["rules"]:
        left = _rule_left(ctx, r["target"], r["field"])
        right = render_template(str(r["value"]), ctx)
        vals = str(right).split("|")
        op = r["op"]
        if op == "eq":
            hit = js_str(left) == right
        elif op == "neq":
            hit = js_str(left) != right
        elif op == "in":
            hit = js_str(left) in vals
        elif op == "notIn":
            hit = js_str(left) not in vals
        elif op in ("gt", "lt", "ge", "le"):
            lnum, rnum = float(left), float(right)
            hit = {"gt": lnum > rnum, "lt": lnum < rnum,
                   "ge": lnum >= rnum, "le": lnum <= rnum}[op]
        elif op == "contains":
            hit = right in js_str(left)
        else:
            hit = False
        if not hit:
            return r.get("message") or f"规则未通过:{r['target']}.{r['field']} {r['op']} {r['value']}"
    return None


def _apply_edits_sim(state: State, at: State, ctx: State) -> Result:
    """在 data 的深拷贝上顺序应用 edits;中途失败不留痕(原子性)。"""
    sim = clone(state["data"])
    changes: list[str] = []

    def sim_obj(role: str) -> State | None:
        real = ctx["targets"].get(role)
        if not real:
            return None
        return next((o for o in sim["objects"] if o["__id"] == real["__id"]), None)

    new_objs: State = {}
    for e in at["edits"]:
        if e["op"] == "set":
            o = sim_obj(e["target"]) or new_objs.get(e["target"])
            if not o:
                return {"error": "set 目标不存在: " + e["target"]}
            v = render_template(e["value"], _render_ctx(ctx))
            old = o["props"].get(e["field"])
            changes.append(f"{e['target']}({o['__id']}).{e['field']}: {old if old is not None else '∅'} → {v}")
            o["props"][e["field"]] = v
        elif e["op"] == "create":
            props = {k: render_template(tpl, _render_ctx(ctx)) for k, tpl in e["props"].items()}
            obj = {"__id": uid("obj"), "__type": e["objectType"], "props": props}
            sim["objects"].append(obj)
            if e.get("target"):
                new_objs[e["target"]] = obj
            changes.append(f"新建 {e['objectType']}({e.get('target') or obj['__id']})")
        elif e["op"] == "delete":
            o = sim_obj(e["target"])
            if not o:
                return {"error": "delete 目标不存在: " + e["target"]}
            sim["objects"] = [x for x in sim["objects"] if x["__id"] != o["__id"]]
            sim["links"] = [l for l in sim["links"] if l["from"] != o["__id"] and l["to"] != o["__id"]]
            changes.append(f"删除 {e['target']}({o['__id']})")
        elif e["op"] in ("addLink", "removeLink"):
            lt = next((l for l in schema_of(state)["linkTypes"]
                       if l["id"] == e["linkType"] or l["name"] == e["linkType"]), None)
            fo = sim_obj(e["from"]) or new_objs.get(e["from"])
            to = sim_obj(e["to"]) or new_objs.get(e["to"])
            if not lt:
                return {"error": "linkType 不存在: " + e["linkType"]}
            if not fo or not to:
                return {"error": f"{e['op']} 端点角色未解析: {e['from']}/{e['to']}"}
            if fo["__type"] != lt["from"] or to["__type"] != lt["to"]:
                return {"error": f"链接端点类型须为 {lt['from']} → {lt['to']}"}
            if e["op"] == "addLink":
                if any(l["__type"] == lt["id"] and l["from"] == fo["__id"] and l["to"] == to["__id"]
                       for l in sim["links"]):
                    return {"error": "链接已存在(基数/重复)"}
                from_side = lambda l: l["__type"] == lt["id"] and l["from"] == fo["__id"]  # noqa: E731
                to_side = lambda l: l["__type"] == lt["id"] and l["to"] == to["__id"]  # noqa: E731
                if lt["cardinality"] in ("1:1", "N:1") and any(from_side(l) for l in sim["links"]):
                    return {"error": "基数约束:from 侧已有关联"}
                if lt["cardinality"] in ("1:1", "1:N") and any(to_side(l) for l in sim["links"]):
                    return {"error": "基数约束:to 侧已有关联"}
                sim["links"].append({"__id": uid("lk"), "__type": lt["id"],
                                     "from": fo["__id"], "to": to["__id"]})
                changes.append(f"建链接 {lt['name']}:{e['from']} → {e['to']}")
            else:
                n = len(sim["links"])
                sim["links"] = [l for l in sim["links"]
                                if not (l["__type"] == lt["id"] and l["from"] == fo["__id"] and l["to"] == to["__id"])]
                if len(sim["links"]) == n:
                    return {"error": "待删链接不存在"}
                changes.append(f"删链接 {lt['name']}:{e['from']} → {e['to']}")
    # create 产生的对象补充进 ctx.targets 供后续 edits/模板引用
    ctx["targets"].update(new_objs)
    return {"sim": sim, "changes": changes}


def describe_edits(state: State, at: State, ctx: State) -> list[str]:
    """确认弹窗的变更预览;不改状态。"""
    r = _apply_edits_sim(state, at, clone(ctx))
    if "error" in r:
        return ["(预览失败) " + r["error"]]
    return r["changes"]


def run_action(state: State, action_id: str, input: State) -> Result:
    """执行动作:参数校验 → target 解析 → 规则 → 确认门槛 → 原子应用 edits → 副作用 → 审计。"""
    at = next((a for a in schema_of(state)["actionTypes"] if a["id"] == action_id), None)
    if not at:
        return {"ok": False, "error": "动作不存在"}
    params = input.get("params") or {}
    targets = input.get("targets") or {}
    pe = _validate_params(at, params)
    if pe:
        return {"ok": False, "error": pe}
    cr = _mk_ctx(state, at, params, targets)
    if "error" in cr:
        return {"ok": False, "error": cr["error"]}
    ctx = cr["ctx"]
    re_ = _check_rules(at, ctx)
    if re_:
        return {"ok": False, "error": re_}
    sc = at.get("submissionCriteria") or {}
    if sc.get("requireConfirm") and not input.get("confirmed"):
        return {"ok": False, "needConfirm": True, "preview": describe_edits(state, at, ctx)}
    r = _apply_edits_sim(state, at, ctx)
    if "error" in r:
        return {"ok": False, "error": r["error"]}
    state["data"] = r["sim"]
    effects: list[State] = []
    for f in at["sideEffects"]:
        cfg = f.get("config") or {}
        if f["type"] == "notify":
            text = render_template(cfg.get("text", ""), ctx)
            state["notices"].append({"id": uid("nt"), "ts": now_iso(), "to": cfg.get("to", ""),
                                     "text": text, "read": False, "actionId": action_id})
            effects.append({"type": "notify", "text": text})
        elif f["type"] == "webhookLog":
            effects.append({"type": "webhookLog", "note": "已记录 webhook 调用(原型不落网)"})
    state["audit"].append({
        "id": uid("au"), "ts": now_iso(), "branch": state["branch"]["current"],
        "actor": input.get("actor") or "本地用户", "actionId": action_id, "actionLabel": at["label"],
        "summary": f"{at['label']} · {len(r['changes'])} 项变更", "diff": r["changes"], "effects": effects,
    })
    return {"ok": True, "changes": r["changes"]}
