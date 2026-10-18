"""Ontology Pipeline v1:批量数据源 → 声明式映射 → 校验 → 物化为本体对象/链接,带血缘。

与 CORE 同契约:state dict 首参、`{"ok"/"error"}` 结果、中文错误文案。
两阶段执行:全量校验通过才落数据(与 run_action 的原子性一致);
物化语义为按对象类型主键 upsert(已存在对象更新 props,__id 稳定)。

增量列 / 调度 / streaming 见 docs/roadmap.md,不在 v1 范围。
"""
from __future__ import annotations

import csv
import json
import os
from typing import Any, Callable

from ._common import NAME_RE, State, Result, js_str, uid
from .state import now_iso, schema_of
from .schema import type_by_name

TRANSFORMS: dict[str, Callable[[Any], Any]] = {}


def _t_str(v: Any) -> str:
    return js_str(v)


def _t_int(v: Any) -> int:
    return int(float(str(v).strip()))


def _t_float(v: Any) -> float:
    return float(str(v).strip())


def _t_bool(v: Any) -> bool:
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "y"):
        return True
    if s in ("false", "0", "no", "n"):
        return False
    raise ValueError("无法解析为布尔: " + js_str(v))


def _t_trim(v: Any) -> str:
    return str(v).strip()


TRANSFORMS.update({"str": _t_str, "int": _t_int, "float": _t_float, "bool": _t_bool, "trim": _t_trim})


# ---------- dataset 注册 ----------

def _rows_from_source(source: Any) -> Result:
    """source: list[dict] | csv 路径 | json 路径。返回 {"ok", "rows", "kind", "sourceRef"}。"""
    if isinstance(source, list):
        if not all(isinstance(r, dict) for r in source):
            return {"ok": False, "error": "rows 数据源须为 dict 列表"}
        return {"ok": True, "rows": source, "kind": "rows", "sourceRef": "<memory>"}
    if not isinstance(source, str):
        return {"ok": False, "error": "数据源须为 rows 列表或文件路径"}
    if not os.path.isfile(source):
        return {"ok": False, "error": "数据源文件不存在: " + source}
    ext = os.path.splitext(source)[1].lower()
    if ext == ".csv":
        with open(source, newline="", encoding="utf-8-sig") as f:
            return {"ok": True, "rows": [dict(r) for r in csv.DictReader(f)],
                    "kind": "csv", "sourceRef": source}
    if ext == ".json":
        try:
            with open(source, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return {"ok": False, "error": "JSON 数据源解析失败: " + str(e)}
        if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
            return {"ok": False, "error": "JSON 数据源须为 dict 数组"}
        return {"ok": True, "rows": data, "kind": "json", "sourceRef": source}
    return {"ok": False, "error": "不支持的数据源类型(仅 .csv / .json / rows 列表): " + source}


def register_dataset(state: State, name: str, source: Any) -> Result:
    """把数据源快照注册进 state["datasets"];同名拒绝(重注册请先 delete_dataset)。"""
    if not NAME_RE.match(name or ""):
        return {"ok": False, "error": "数据集 name 需为蛇形标识"}
    datasets = state.setdefault("datasets", {})
    if any(d["name"] == name for d in datasets.values()):
        return {"ok": False, "error": "数据集重名: " + name}
    r = _rows_from_source(source)
    if not r["ok"]:
        return r
    columns: list[str] = []
    for row in r["rows"]:
        for k in row:
            if k not in columns:
                columns.append(k)
    ds = {"__id": uid("ds"), "name": name, "kind": r["kind"], "sourceRef": r["sourceRef"],
          "columns": columns, "rowCount": len(r["rows"]), "registeredAt": now_iso(),
          "rows": r["rows"]}
    datasets[ds["__id"]] = ds
    return {"ok": True, "id": ds["__id"]}


def delete_dataset(state: State, dataset_id: str) -> Result:
    datasets = state.setdefault("datasets", {})
    if dataset_id not in datasets:
        return {"ok": False, "error": "数据集不存在"}
    del datasets[dataset_id]
    return {"ok": True}


def list_datasets(state: State) -> list[State]:
    return [{k: v for k, v in d.items() if k != "rows"}
            for d in state.get("datasets", {}).values()]


def pipeline_runs(state: State, limit: int = 20) -> list[State]:
    return state.get("pipelineRuns", [])[-limit:]


def _find_dataset(state: State, ref: str) -> State | None:
    for d in state.get("datasets", {}).values():
        if d["__id"] == ref or d["name"] == ref:
            return d
    return None


# ---------- 校验 ----------

def _err(errors: list[State], row: int | None, message: str) -> None:
    errors.append({"row": row, "message": message})


def _apply_transform(spec: Any, raw: Any) -> Any:
    """spec: 列名字符串 或 {"column": c, "transform": t}。可能抛 KeyError/ValueError。"""
    if isinstance(spec, dict):
        col, tname = spec.get("column"), spec.get("transform")
        v = raw
        if tname:
            v = TRANSFORMS[tname](v)
        return v
    return raw


def _check_base(value: Any, base_type: str, enum_values: Any) -> str | None:
    """物化前的 baseType/enum 检查;返回错误消息或 None。"""
    if base_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return "须为数值: " + js_str(value)
    elif base_type == "boolean":
        if not isinstance(value, bool):
            return "须为布尔: " + js_str(value)
    elif base_type == "enum":
        if enum_values and value not in enum_values:
            return "非法枚举值: " + js_str(value)
    elif base_type in ("string", "date"):
        if not isinstance(value, str):
            return "须为字符串: " + js_str(value)
    return None


def _validate_mapping(state: State, mapping: State) -> Result:
    """结构性校验(不逐行):返回 {"ok", "objects": [规范化块], "links": [...]} 或错误。"""
    if not isinstance(mapping, dict):
        return {"ok": False, "error": "mapping 须为对象"}
    obj_blocks = mapping.get("objects") or []
    link_blocks = mapping.get("links") or []
    if not obj_blocks and not link_blocks:
        return {"ok": False, "error": "mapping 需至少一个 objects 或 links 块"}
    s = schema_of(state)
    norm_objs = []
    for i, b in enumerate(obj_blocks):
        ds = _find_dataset(state, b.get("dataset") or "")
        if not ds:
            return {"ok": False, "error": f"objects[{i}] 数据集不存在: {b.get('dataset')}"}
        t = type_by_name(state, b.get("objectType") or "")
        if not t:
            return {"ok": False, "error": f"objects[{i}] 对象类型不存在: {b.get('objectType')}"}
        if not t.get("primaryKey"):
            return {"ok": False, "error": f"对象类型 {t['name']} 未设 primaryKey,无法物化"}
        key_col = b.get("key")
        if not key_col or key_col not in ds["columns"]:
            return {"ok": False, "error": f"objects[{i}] 主键列缺失: {key_col}"}
        props = b.get("properties") or {}
        if not isinstance(props, dict):
            return {"ok": False, "error": f"objects[{i}] properties 须为对象"}
        pdefs = {p["name"]: p for p in t["properties"]}
        for pname, spec in props.items():
            if pname not in pdefs:
                return {"ok": False, "error": f"objects[{i}] 属性不存在: {t['name']}.{pname}"}
            col = spec.get("column") if isinstance(spec, dict) else spec
            if col not in ds["columns"]:
                return {"ok": False, "error": f"objects[{i}] 列缺失: {col}"}
            if isinstance(spec, dict) and spec.get("transform") and spec["transform"] not in TRANSFORMS:
                return {"ok": False, "error": f"objects[{i}] 未知 transform: {spec['transform']}"}
        norm_objs.append({"ds": ds, "type": t, "key": key_col, "props": props, "pdefs": pdefs})
    norm_links = []
    for i, b in enumerate(link_blocks):
        lt = next((l for l in s["linkTypes"] if l["name"] == b.get("linkType")), None)
        if not lt:
            return {"ok": False, "error": f"links[{i}] 链接类型不存在: {b.get('linkType')}"}
        ds = _find_dataset(state, b.get("dataset") or "")
        if not ds:
            return {"ok": False, "error": f"links[{i}] 数据集不存在: {b.get('dataset')}"}
        for side in ("fromColumn", "toColumn"):
            if not b.get(side) or b[side] not in ds["columns"]:
                return {"ok": False, "error": f"links[{i}] 列缺失: {b.get(side)}"}
        norm_links.append({"ds": ds, "lt": lt,
                           "fromColumn": b["fromColumn"], "toColumn": b["toColumn"]})
    return {"ok": True, "objects": norm_objs, "links": norm_links}


def _pk_index(state: State, type_name: str, pk_prop: str) -> dict[str, State]:
    idx: dict[str, State] = {}
    for o in state["data"]["objects"]:
        if o["__type"] == type_name:
            idx[js_str(o["props"].get(pk_prop))] = o
    return idx


def _validate_rows(state: State, norm: State) -> Result:
    """逐行校验 + 预解析:返回 {"ok", "plans": [...], "linkPlans": [...], "counts": {...}}。

    plans:   {"type", "pk", "props", "existing": 对象或 None}
    linkPlans: {"lt", "fromId", "toId"}(物化前 fromId/toId 先用主键值占位,
    落数据阶段再换成 __id —— 因为新建对象的 __id 此时还不存在)
    """
    errors: list[State] = []
    plans: list[State] = []
    indexes: dict[str, dict[str, State]] = {}
    for b in norm["objects"]:
        t, ds, key = b["type"], b["ds"], b["key"]
        idx = indexes.setdefault(t["name"], _pk_index(state, t["name"], t["primaryKey"]))
        seen: set[str] = set()
        for ri, row in enumerate(ds["rows"]):
            raw_pk = row.get(key)
            pk = js_str(raw_pk).strip() if raw_pk is not None else ""
            if not pk:
                _err(errors, ri, f"{t['name']} 主键列为空(列 {key})")
                continue
            if pk in seen:
                _err(errors, ri, f"{t['name']} 批内主键重复: {pk}")
                continue
            seen.add(pk)
            props: State = {}
            row_bad = False
            for pname, spec in b["props"].items():
                col = spec.get("column") if isinstance(spec, dict) else spec
                raw = row.get(col)
                if raw is None or (isinstance(raw, str) and raw == ""):
                    continue  # 空单元格:不写该属性
                try:
                    v = _apply_transform(spec, raw)
                except (ValueError, TypeError):
                    _err(errors, ri, f"{t['name']}.{pname} transform 失败: {js_str(raw)}")
                    row_bad = True
                    continue
                pd = b["pdefs"][pname]
                msg = _check_base(v, pd["baseType"], pd.get("enumValues"))
                if msg:
                    _err(errors, ri, f"{t['name']}.{pname} {msg}")
                    row_bad = True
                    continue
                props[pname] = v
            if not row_bad:
                # 主键属性始终写入(保持主键可查)
                props[t["primaryKey"]] = pk
                plans.append({"type": t["name"], "pkProp": t["primaryKey"], "pk": pk,
                              "props": props, "existing": idx.get(pk)})
    # 链接:端点按"既有对象 + 本批 plans"解析(值 = 主键字符串)
    new_pks: dict[str, set[str]] = {}
    for p in plans:
        new_pks.setdefault(p["type"], set()).add(p["pk"])
    link_plans: list[State] = []
    link_errors: list[State] = []
    for b in norm["links"]:
        lt, ds = b["lt"], b["ds"]
        ft, tt = lt["from"], lt["to"]
        ftype = type_by_name(state, ft)
        ttype = type_by_name(state, tt)
        fidx = _pk_index(state, ft, ftype["primaryKey"] if ftype and ftype.get("primaryKey") else "")
        tidx = _pk_index(state, tt, ttype["primaryKey"] if ttype and ttype.get("primaryKey") else "")
        for ri, row in enumerate(ds["rows"]):
            fv = js_str(row.get(b["fromColumn"])).strip() if row.get(b["fromColumn"]) is not None else ""
            tv = js_str(row.get(b["toColumn"])).strip() if row.get(b["toColumn"]) is not None else ""
            if not fv or not tv:
                continue  # 空端点列:跳过该行,不算错误
            f_ok = fv in fidx or fv in new_pks.get(ft, set())
            t_ok = tv in tidx or tv in new_pks.get(tt, set())
            if not f_ok:
                _err(link_errors, ri, f"链接 {lt['name']} from 端点无法解析: {ft} 主键 {fv}")
            if not t_ok:
                _err(link_errors, ri, f"链接 {lt['name']} to 端点无法解析: {tt} 主键 {tv}")
            if f_ok and t_ok:
                link_plans.append({"lt": lt, "fromPk": fv, "toPk": tv})
    errors.extend(link_errors)
    # cardinality 预检(既有链接 + 批内)
    existing = state["data"]["links"]
    for lp in link_plans:
        lt = lp["lt"]
        # fromId/toId 此时未知,用 (type, pk) 对比较
        def _side(l: State, side: str) -> tuple[str, str] | None:
            oid = l["from"] if side == "from" else l["to"]
            o = next((x for x in state["data"]["objects"] if x["__id"] == oid), None)
            if not o:
                return None
            t = type_by_name(state, o["__type"])
            pk = t.get("primaryKey") if t else ""
            return (o["__type"], js_str(o["props"].get(pk)))
        if lt["cardinality"] in ("1:1", "N:1"):
            for l in existing:
                if l["__type"] != lt["id"]:
                    continue
                sd = _side(l, "from")
                if sd and sd == (lt["from"], lp["fromPk"]) and _side(l, "to") != (lt["to"], lp["toPk"]):
                    _err(errors, None, f"基数约束:{lt['name']} from 侧 {lp['fromPk']} 已有关联")
        if lt["cardinality"] in ("1:1", "1:N"):
            for l in existing:
                if l["__type"] != lt["id"]:
                    continue
                sd = _side(l, "to")
                if sd and sd == (lt["to"], lp["toPk"]) and _side(l, "from") != (lt["from"], lp["fromPk"]):
                    _err(errors, None, f"基数约束:{lt['name']} to 侧 {lp['toPk']} 已有关联")
    # 批内 cardinality 冲突(同一批两条链接抢占同一侧)
    batch_from: dict[tuple[str, str], str] = {}   # (ltId, fromPk) -> toPk
    batch_to: dict[tuple[str, str], str] = {}     # (ltId, toPk) -> fromPk
    for lp in link_plans:
        lt = lp["lt"]
        if lt["cardinality"] in ("1:1", "N:1"):
            k = (lt["id"], lp["fromPk"])
            if k in batch_from and batch_from[k] != lp["toPk"]:
                _err(errors, None, f"基数约束:{lt['name']} from 侧 {lp['fromPk']} 批内冲突")
            batch_from[k] = lp["toPk"]
        if lt["cardinality"] in ("1:1", "1:N"):
            k = (lt["id"], lp["toPk"])
            if k in batch_to and batch_to[k] != lp["fromPk"]:
                _err(errors, None, f"基数约束:{lt['name']} to 侧 {lp['toPk']} 批内冲突")
            batch_to[k] = lp["fromPk"]
    if errors:
        return {"ok": False, "errors": errors}
    would_create = sum(1 for p in plans if p["existing"] is None)
    would_update = sum(1 for p in plans if p["existing"] is not None)
    return {"ok": True, "plans": plans, "linkPlans": link_plans,
            "counts": {"wouldCreate": would_create, "wouldUpdate": would_update,
                       "wouldLink": len(link_plans)}}


# ---------- 执行 ----------

def run_pipeline(state: State, mapping: State, *, dry_run: bool = False) -> Result:
    """两阶段物化:校验(映射结构 + 全量行)→ 一次性落数据 + 记血缘。

    dry_run=True 只跑校验,返回预览 counts,不写 state、不记血缘。
    """
    state.setdefault("datasets", {})
    state.setdefault("pipelineRuns", [])
    started = now_iso()
    norm = _validate_mapping(state, mapping)
    if not norm["ok"]:
        return norm
    checked = _validate_rows(state, norm)
    if not checked["ok"]:
        errs = checked["errors"]
        state["pipelineRuns"].append({
            "__id": uid("run"), "mapping": mapping.get("name") or "<anonymous>",
            "datasets": sorted({b["ds"]["name"] for b in norm["objects"] + norm["links"]}),
            "startedAt": started, "finishedAt": now_iso(), "status": "failed",
            "errors": errs[:10], "errorCount": len(errs)})
        return {"ok": False, "error": errs[0]["message"], "errors": errs}
    counts = checked["counts"]
    if dry_run:
        return {"ok": True, "dryRun": True, "counts": counts}
    created = updated = 0
    object_ids: list[str] = []
    pk_to_id: dict[tuple[str, str], str] = {}
    for p in checked["plans"]:
        if p["existing"] is not None:
            p["existing"]["props"].update(p["props"])
            oid = p["existing"]["__id"]
            updated += 1
        else:
            oid = uid("obj")
            state["data"]["objects"].append(
                {"__id": oid, "__type": p["type"], "props": dict(p["props"])})
            created += 1
        object_ids.append(oid)
        pk_to_id[(p["type"], p["pk"])] = oid
    links_created = skipped = 0
    seen_pairs: set[tuple[str, str, str]] = set()
    for lp in checked["linkPlans"]:
        lt = lp["lt"]
        fid = pk_to_id.get((lt["from"], lp["fromPk"]))
        tid = pk_to_id.get((lt["to"], lp["toPk"]))
        if fid is None:
            fo = _pk_index(state, lt["from"],
                           type_by_name(state, lt["from"]).get("primaryKey") or "")
            fid = fo[lp["fromPk"]]["__id"]
        if tid is None:
            to = _pk_index(state, lt["to"],
                           type_by_name(state, lt["to"]).get("primaryKey") or "")
            tid = to[lp["toPk"]]["__id"]
        pair = (lt["id"], fid, tid)
        if pair in seen_pairs or any(
                l["__type"] == lt["id"] and l["from"] == fid and l["to"] == tid
                for l in state["data"]["links"]):
            skipped += 1
            continue
        seen_pairs.add(pair)
        state["data"]["links"].append({"__id": uid("lk"), "__type": lt["id"],
                                       "from": fid, "to": tid})
        links_created += 1
    run = {"__id": uid("run"), "mapping": mapping.get("name") or "<anonymous>",
           "datasets": sorted({b["ds"]["name"] for b in norm["objects"] + norm["links"]}),
           "startedAt": started, "finishedAt": now_iso(), "status": "success",
           "counts": {"created": created, "updated": updated,
                      "linksCreated": links_created, "skipped": skipped},
           "objectIds": object_ids}
    state["pipelineRuns"].append(run)
    return {"ok": True, "runId": run["__id"], "counts": run["counts"], "objectIds": object_ids}
