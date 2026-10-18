"""AI 接口骨架(AIP 预留):Logic Function 注册表。

对齐 AIP Logic 的概念:具名、可校验参数、可被未来的 Agent/编排层调用的
领域函数。v1 只做进程内注册表与调用协议,不含任何 LLM 调用;
Assist / Agents / 自然语言查询见 docs/roadmap.md。

契约:logic 函数收 state 首参与 params dict,返回 JSON 兼容 dict;
若返回 dict 含 "ok" 键则原样透传,否则包装为 {"ok": True, "result": ...}。
"""
from __future__ import annotations

from typing import Any, Callable

from ._common import NAME_RE, State, Result

_REGISTRY: dict[str, State] = {}

_PARAM_TYPES = {"string": str, "number": (int, float), "boolean": bool,
                "object": dict, "list": list}


def register_logic(name: str, fn: Callable[[State, State], Any], *,
                   description: str = "", params_schema: State | None = None) -> Result:
    """注册一个 logic 函数。params_schema: {参数名: {"type": ..., "required": bool}}。"""
    if not NAME_RE.match(name or ""):
        return {"ok": False, "error": "logic name 需为蛇形标识"}
    if name in _REGISTRY:
        return {"ok": False, "error": "logic 重名: " + name}
    if not callable(fn):
        return {"ok": False, "error": "fn 不可调用"}
    if params_schema is not None:
        if not isinstance(params_schema, dict):
            return {"ok": False, "error": "params_schema 须为对象"}
        for pname, spec in params_schema.items():
            if not isinstance(spec, dict) or spec.get("type") not in _PARAM_TYPES:
                return {"ok": False, "error": f"params_schema.{pname} 非法 type"}
    _REGISTRY[name] = {"fn": fn, "description": description,
                       "params_schema": params_schema or {}}
    return {"ok": True, "name": name}


def list_logic() -> list[State]:
    return [{"name": n, "description": r["description"],
             "params": sorted(r["params_schema"].keys())}
            for n, r in sorted(_REGISTRY.items())]


def _check_params(schema: State, params: State) -> str | None:
    for pname, spec in schema.items():
        if spec.get("required") and pname not in params:
            return "缺参数: " + pname
        if pname in params:
            v = params[pname]
            t = spec["type"]
            if t == "number" and isinstance(v, bool):
                return f"参数 {pname} 须为 number"
            if not isinstance(v, _PARAM_TYPES[t]):
                return f"参数 {pname} 须为 {t}"
    return None


def invoke_logic(state: State, name: str, params: State | None = None) -> Result:
    """调用已注册的 logic;异常一律包装为 {"ok": False, "error": ...}。"""
    entry = _REGISTRY.get(name)
    if not entry:
        return {"ok": False, "error": "logic 不存在: " + str(name)}
    params = params or {}
    if not isinstance(params, dict):
        return {"ok": False, "error": "params 须为对象"}
    msg = _check_params(entry["params_schema"], params)
    if msg:
        return {"ok": False, "error": msg}
    try:
        ret = entry["fn"](state, params)
    except Exception as e:  # noqa: BLE001 —— 骨架层统一兜底,契约即错误字典
        return {"ok": False, "error": f"logic {name} 执行异常: {e}"}
    if isinstance(ret, dict) and "ok" in ret:
        return ret
    return {"ok": True, "result": ret}


def _reset_registry() -> None:
    """测试专用:清空注册表。"""
    _REGISTRY.clear()
