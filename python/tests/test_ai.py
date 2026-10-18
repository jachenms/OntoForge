"""AI 接口骨架(Logic Function 注册表)测试。"""
import pytest

import ontoforge as of
from ontoforge.ai import _reset_registry


@pytest.fixture(autouse=True)
def clean_registry():
    _reset_registry()
    yield
    _reset_registry()


def test_register_list_invoke():
    def open_incidents(state, params):
        return {"count": sum(1 for o in of.objects_of_type(state, "incident")
                             if o["props"].get("status") != "已关闭")}

    r = of.register_logic("open_incidents", open_incidents,
                          description="未关闭事件数", params_schema={})
    assert r["ok"]
    lst = of.list_logic()
    assert lst == [{"name": "open_incidents", "description": "未关闭事件数", "params": []}]
    s = of.seed.traffic()
    res = of.invoke_logic(s, "open_incidents")
    assert res["ok"] and res["result"] == {"count": 4}


def test_params_validation_and_dup():
    def fn(state, params):
        return params["n"] * 2

    assert of.register_logic("double", fn, params_schema={
        "n": {"type": "number", "required": True}})["ok"]
    assert "重名" in of.register_logic("double", fn)["error"]
    s = of.seed.blank()
    assert "缺参数" in of.invoke_logic(s, "double")["error"]
    assert "须为 number" in of.invoke_logic(s, "double", {"n": "x"})["error"]
    assert of.invoke_logic(s, "double", {"n": 3})["result"] == 6
    assert not of.register_logic("Bad Name", fn)["ok"]


def test_invoke_wraps_exceptions_and_passthrough():
    def boom(state, params):
        raise RuntimeError("炸了")

    def with_ok(state, params):
        return {"ok": False, "error": "业务错误"}

    of.register_logic("boom", boom)
    of.register_logic("with_ok", with_ok)
    s = of.seed.blank()
    r = of.invoke_logic(s, "boom")
    assert not r["ok"] and "炸了" in r["error"]
    r2 = of.invoke_logic(s, "with_ok")
    assert r2 == {"ok": False, "error": "业务错误"}  # 含 ok 的结果原样透传
    assert not of.invoke_logic(s, "missing")["ok"]
