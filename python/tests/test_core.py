"""镜像 smoke.mjs 的 S0–S7 行为断言(29 项)。

S8–S14 为 HTML 静态检查,保留在 JS 侧 smoke.mjs,不在此重复。
编号与 smoke.mjs 对齐,便于双端对照。
"""
import re

import ontoforge as C
from ontoforge import seed


# ── S0 序列化 ──

def test_s0_1_空状态序列化往返():
    s = C.create_empty_state()
    r = C.deserialize(C.serialize(s))
    assert r["ok"], r.get("error")
    assert r["state"]["meta"]["ontologyName"] == s["meta"]["ontologyName"]
    assert r["state"]["schemas"]["main"]


def test_s0_2_非法输入拒绝():
    assert not C.deserialize("not json")["ok"]
    assert not C.deserialize('{"app":"other"}')["ok"]


# ── S1 对象类型/属性/共享属性 ──

def test_s1_1_建对象类型_name校验():
    s = C.create_empty_state()
    assert not C.add_object_type(s, {"name": "Bad Name"})["ok"]
    assert C.add_object_type(s, {"name": "road_segment", "label": "路段", "primaryKey": ""})["ok"]
    assert not C.add_object_type(s, {"name": "road_segment"})["ok"]


def test_s1_2_属性CRUD与主键保护():
    s = C.create_empty_state()
    tid = C.add_object_type(s, {"name": "incident", "label": "事件"})["id"]
    assert C.add_property(s, tid, {"name": "inc_id", "baseType": "string", "required": True})["ok"]
    assert not C.add_property(s, tid, {"name": "inc_id", "baseType": "string"})["ok"]
    assert not C.add_property(s, tid, {"name": "x", "baseType": "enum"})["ok"]
    assert C.add_property(s, tid, {"name": "status", "baseType": "enum",
                                   "enumValues": ["待处置", "已关闭"]})["ok"]
    assert C.update_object_type(s, tid, {"primaryKey": "inc_id"})["ok"]
    assert not C.delete_property(s, tid, "inc_id")["ok"]
    assert not C.update_property(s, tid, "status", {"name": "st"})["ok"]


def test_s1_3_删除保护():
    s = C.create_empty_state()
    a = C.add_object_type(s, {"name": "a"})["id"]
    C.add_object_type(s, {"name": "b"})
    s["data"]["objects"].append({"__id": "o1", "__type": "a", "props": {}})
    assert not C.delete_object_type(s, a)["ok"]          # 有实例拒绝
    s["data"]["objects"] = []
    C.schema_of(s)["linkTypes"].append(
        {"id": "lt1", "name": "ab", "from": "a", "to": "b", "cardinality": "N:1", "keyMapping": {}})
    assert not C.delete_object_type(s, a)["ok"]          # 被 linkType 引用拒绝


def test_s1_4_共享属性挂载():
    s = C.create_empty_state()
    tid = C.add_object_type(s, {"name": "x"})["id"]
    sp = C.add_shared_prop(s, {"name": "region", "label": "区域", "baseType": "string"})
    assert sp["ok"]
    assert C.attach_shared_prop(s, tid, sp["id"])["ok"]
    assert not C.attach_shared_prop(s, tid, sp["id"])["ok"]   # 重复挂载拒绝
    assert not C.delete_shared_prop(s, sp["id"])["ok"]        # 挂载中删除拒绝
    assert C.detach_shared_prop(s, tid, sp["id"])["ok"]
    assert C.delete_shared_prop(s, sp["id"])["ok"]
    assert not C.delete_shared_prop(s, "sp_none")["ok"]


# ── S2 链接类型/链接实例 ──

def _two_types():
    s = C.create_empty_state()
    C.add_object_type(s, {"name": "team"})
    C.add_object_type(s, {"name": "incident"})
    s["data"]["objects"] += [
        {"__id": "t1", "__type": "team", "props": {}},
        {"__id": "t2", "__type": "team", "props": {}},
        {"__id": "i1", "__type": "incident", "props": {}},
    ]
    return s


def test_s2_1_建链接类型_端点校验():
    s = _two_types()
    assert not C.add_link_type(s, {"name": "x", "from": "team", "to": "ghost", "cardinality": "M:N"})["ok"]
    assert not C.add_link_type(s, {"name": "x", "from": "team", "to": "incident", "cardinality": "9:9"})["ok"]
    assert C.add_link_type(s, {"name": "assigned", "label": "派遣", "from": "team", "to": "incident",
                               "cardinality": "M:N",
                               "keyMapping": {"fromKey": "team_id", "toKey": "inc_id"}})["ok"]


def test_s2_2_链接实例_类型匹配_去重_基数():
    s = _two_types()
    lt = C.add_link_type(s, {"name": "assigned", "from": "team", "to": "incident",
                             "cardinality": "M:N"})["id"]
    assert not C.create_link(s, lt, "i1", "t1")["ok"]    # 端点方向错
    assert C.create_link(s, lt, "t1", "i1")["ok"]
    assert not C.create_link(s, lt, "t1", "i1")["ok"]    # 重复对
    assert C.create_link(s, lt, "t2", "i1")["ok"]        # M:N 多方允许
    assert not C.delete_link_type(s, lt)["ok"]           # 有实例时删 linkType 拒绝


def test_s2_3_n比1_唯一性():
    s = _two_types()
    lt = C.add_link_type(s, {"name": "on", "from": "incident", "to": "team",
                             "cardinality": "N:1"})["id"]
    assert C.create_link(s, lt, "i1", "t1")["ok"]
    assert not C.create_link(s, lt, "i1", "t2")["ok"]    # N:1 from 侧重复
    assert C.delete_link(s, C.links_of(s, lt)[0]["__id"])["ok"]
    assert C.create_link(s, lt, "i1", "t2")["ok"]        # 删后可重建


# ── S3 动作类型定义/模板 ──

def test_s3_1_动作类型CRUD_结构校验():
    s = C.create_empty_state()
    C.add_object_type(s, {"name": "incident"})
    C.add_object_type(s, {"name": "team"})
    bad = C.add_action_type(s, {"name": "a1", "targets": [{"role": "t", "type": "ghost"}],
                                "params": [], "rules": [], "edits": [], "sideEffects": []})
    assert not bad["ok"]
    defn = {"name": "dispatch", "label": "派遣",
            "targets": [{"role": "team", "type": "team"}, {"role": "inc", "type": "incident"}],
            "params": [{"name": "note", "type": "string", "required": False}],
            "rules": [{"target": "team", "field": "status", "op": "eq", "value": "待命",
                       "message": "仅待命可派遣"}],
            "submissionCriteria": {"requireConfirm": True},
            "edits": [{"op": "set", "target": "team", "field": "status", "value": "出动"}],
            "sideEffects": [{"type": "notify", "config": {"to": "调度中心", "text": "已派遣"}}]}
    r = C.add_action_type(s, defn)
    assert r["ok"], r.get("error")
    assert not C.add_action_type(s, defn)["ok"]           # 重名拒绝
    assert C.update_action_type(s, r["id"], {"label": "派遣队伍"})["ok"]
    assert C.delete_action_type(s, r["id"])["ok"]


def test_s3_2_模板渲染():
    ctx = {"param": {"title": "追尾"}, "targets": {"inc": {"props": {"status": "处理中"}}},
           "now": "2026-10-17", "auto": "x_1"}
    assert C.render_template("上报:{{param.title}}/{{targets.inc.props.status}}", ctx) == "上报:追尾/处理中"
    assert C.render_template("{{missing.deep}}", ctx) == ""
    assert C.render_template("{{now}}#{{auto}}", ctx) == "2026-10-17#x_1"


# ── S4 runAction 引擎 ──

def _engine_world():
    s = C.create_empty_state()
    C.add_object_type(s, {"name": "team"})
    C.add_object_type(s, {"name": "incident"})
    tid = next(t for t in C.schema_of(s)["objectTypes"] if t["name"] == "team")["id"]
    C.add_property(s, tid, {"name": "status", "baseType": "enum", "enumValues": ["待命", "出动"]})
    C.add_link_type(s, {"name": "assigned", "from": "team", "to": "incident", "cardinality": "M:N"})
    s["data"]["objects"] += [
        {"__id": "t1", "__type": "team", "props": {"status": "待命"}},
        {"__id": "t2", "__type": "team", "props": {"status": "出动"}},
        {"__id": "i1", "__type": "incident", "props": {"status": "处理中"}},
    ]
    return s


_DISPATCH_DEF = {"name": "dispatch",
    "targets": [{"role": "team", "type": "team"}, {"role": "inc", "type": "incident"}],
    "params": [{"name": "prio", "type": "enum", "enumValues": ["高", "低"], "required": True}],
    "rules": [{"target": "team", "field": "status", "op": "eq", "value": "待命",
               "message": "仅待命队伍可派遣"}],
    "submissionCriteria": {"requireConfirm": True},
    "edits": [{"op": "set", "target": "team", "field": "status", "value": "出动"},
              {"op": "addLink", "linkType": "assigned", "from": "team", "to": "inc"}],
    "sideEffects": [{"type": "notify", "config": {"to": "调度", "text": "{{param.prio}}优先级派遣"}},
                    {"type": "webhookLog", "config": {"url": "http://hook"}}]}


def _world_with_dispatch():
    s = _engine_world()
    C.add_action_type(s, _DISPATCH_DEF)
    return s, C.schema_of(s)["actionTypes"][0]["id"]


def test_s4_1_参数校验():
    s, aid = _world_with_dispatch()
    r = C.run_action(s, aid, {"params": {}, "targets": {"team": "t1", "inc": "i1"}})
    assert not r["ok"] and not r.get("needConfirm")
    assert "prio" in r["error"]


def test_s4_2_规则校验():
    s, aid = _world_with_dispatch()
    r = C.run_action(s, aid, {"params": {"prio": "高"}, "targets": {"team": "t2", "inc": "i1"}})
    assert not r["ok"] and r["error"] == "仅待命队伍可派遣"


def test_s4_3_确认门槛_预览():
    s, aid = _world_with_dispatch()
    r = C.run_action(s, aid, {"params": {"prio": "高"}, "targets": {"team": "t1", "inc": "i1"}})
    assert not r["ok"] and r["needConfirm"] is True
    assert len(r["preview"]) >= 2
    assert len(s["audit"]) == 0                          # 未确认不写审计
    tm = next(o for o in s["data"]["objects"] if o["__id"] == "t1")
    assert tm["props"]["status"] == "待命"               # 未确认不改数据


def test_s4_4_成功路径_edits_副作用_审计():
    s, aid = _world_with_dispatch()
    r = C.run_action(s, aid, {"params": {"prio": "高"}, "targets": {"team": "t1", "inc": "i1"},
                              "confirmed": True, "actor": "张三"})
    assert r["ok"], r.get("error")
    tm = next(o for o in s["data"]["objects"] if o["__id"] == "t1")
    assert tm["props"]["status"] == "出动"               # set 生效
    assert len(s["data"]["links"]) == 1                  # addLink 生效
    assert len(s["notices"]) == 1                        # notify 进通知中心
    assert "高" in s["notices"][0]["text"]               # 通知文本模板渲染
    assert len(s["audit"]) == 1
    assert s["audit"][0]["actor"] == "张三"
    assert any(e["type"] == "webhookLog" for e in s["audit"][0]["effects"])


def test_s4_5_原子性_中途失败不留痕():
    s = _engine_world()
    C.add_action_type(s, {"name": "bad", "targets": [{"role": "team", "type": "team"}],
        "params": [], "rules": [], "submissionCriteria": {"requireConfirm": False},
        "edits": [{"op": "set", "target": "team", "field": "status", "value": "出动"},
                  {"op": "addLink", "linkType": "assigned", "from": "team", "to": "ghost_role"}],
        "sideEffects": []})
    aid = C.schema_of(s)["actionTypes"][0]["id"]
    r = C.run_action(s, aid, {"params": {}, "targets": {"team": "t1"}, "confirmed": True})
    assert not r["ok"]
    tm = next(o for o in s["data"]["objects"] if o["__id"] == "t1")
    assert tm["props"]["status"] == "待命"               # 数据回滚
    assert len(s["audit"]) == 0


def test_s4_6_create_edit_auto_now():
    s = _engine_world()
    C.add_action_type(s, {"name": "report", "targets": [],
        "params": [{"name": "title", "type": "string", "required": True}], "rules": [],
        "submissionCriteria": {"requireConfirm": False},
        "edits": [{"op": "create", "target": "inc", "objectType": "incident",
                   "props": {"title": "{{param.title}}", "reported": "{{now}}", "code": "{{auto}}"}}],
        "sideEffects": []})
    aid = C.schema_of(s)["actionTypes"][0]["id"]
    r = C.run_action(s, aid, {"params": {"title": "追尾"}, "targets": {}, "confirmed": True})
    assert r["ok"], r.get("error")
    inc = next(o for o in s["data"]["objects"] if o["props"].get("title") == "追尾")
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", inc["props"]["reported"])   # now 渲染为日期
    assert inc["props"]["code"] and inc["props"]["code"] != "{{auto}}"  # auto 渲染为新 id


# ── S5 查询/搜索/审计统计 ──

def _query_world():
    s = C.create_empty_state()
    C.add_object_type(s, {"name": "seg"})
    C.add_object_type(s, {"name": "inc"})
    sid = next(t for t in C.schema_of(s)["objectTypes"] if t["name"] == "seg")["id"]
    C.add_property(s, sid, {"name": "name", "baseType": "string"})
    C.add_property(s, sid, {"name": "level", "baseType": "string"})
    C.update_object_type(s, sid, {"primaryKey": "name"})
    C.add_link_type(s, {"name": "on", "from": "inc", "to": "seg", "cardinality": "N:1"})
    s["data"]["objects"] += [
        {"__id": "g1", "__type": "seg", "props": {"name": "成渝立交", "level": "高速"}},
        {"__id": "g2", "__type": "seg", "props": {"name": "机场快速", "level": "主干"}},
        {"__id": "e1", "__type": "inc", "props": {"title": "两车追尾"}},
    ]
    C.create_link(s, C.schema_of(s)["linkTypes"][0]["id"], "e1", "g1")
    return s


def test_s5_1_查询与label():
    s = _query_world()
    assert len(C.objects_of_type(s, "seg")) == 2
    assert C.object_label(s, s["data"]["objects"][0]) == "成渝立交"     # name 优先


def test_s5_2_搜索大小写不敏感_跨属性():
    s = _query_world()
    assert len(C.search_objects(s, "seg", "高速")) == 1                 # 按 level 命中
    assert len(C.search_objects(s, "seg", "成渝")) == 1                 # 按 name 命中
    assert len(C.search_objects(s, "seg", "")) == 2                     # 空串全量


def test_s5_3_关联遍历():
    s = _query_world()
    r = C.linked_objects(s, "e1")
    assert len(r) == 1 and r[0]["direction"] == "out" and r[0]["object"]["__id"] == "g1"
    assert C.linked_objects(s, "g1")[0]["direction"] == "in"


def test_s5_4_审计过滤与用量柱状():
    s = _query_world()
    C.add_action_type(s, {"name": "ping", "targets": [{"role": "x", "type": "seg"}],
        "params": [], "rules": [], "submissionCriteria": {"requireConfirm": False},
        "edits": [{"op": "set", "target": "x", "field": "level", "value": "拥堵"}], "sideEffects": []})
    aid = C.schema_of(s)["actionTypes"][0]["id"]
    C.run_action(s, aid, {"params": {}, "targets": {"x": "g1"}, "confirmed": True})
    C.run_action(s, aid, {"params": {}, "targets": {"x": "g2"}, "confirmed": True})
    assert len(C.audit_for(s, {"actionId": aid})) == 2
    assert len(C.audit_for(s, {"objectId": "g1"})) == 1
    u = C.usage_by_day(s, aid, 30)
    assert len(u) == 30 and u[-1]["count"] == 2
    assert C.unread_notices(s) == 0


# ── S6 分支/diff/合并 ──

def test_s6_1_建分支_隔离schema():
    s = C.create_empty_state()
    C.add_object_type(s, {"name": "seg"})
    assert C.create_branch(s, "feature-x")["ok"]
    assert s["branch"]["current"] == "feature-x"
    C.add_object_type(s, {"name": "tunnel"})             # 分支上加类型
    assert len(C.schema_of(s)["objectTypes"]) == 2
    C.switch_branch(s, "main")
    assert len(C.schema_of(s)["objectTypes"]) == 1       # main 仍 1 类(隔离)


def test_s6_2_diff三类变更():
    s = C.create_empty_state()
    C.add_object_type(s, {"name": "seg", "label": "路段"})
    C.create_branch(s, "b1")
    C.add_object_type(s, {"name": "tunnel"})
    tid = next(t for t in C.schema_of(s)["objectTypes"] if t["name"] == "seg")["id"]
    C.update_object_type(s, tid, {"label": "路段v2"})
    C.switch_branch(s, "main")
    C.add_object_type(s, {"name": "temp_del"})
    # diff 是 main→branch;temp_del 在 branch 不存在 → removed
    d = C.diff_schemas(s["schemas"]["main"], s["schemas"]["b1"])
    assert any(t["name"] == "tunnel" for t in d["objectTypes"]["added"])
    assert any(c["name"] == "seg" for c in d["objectTypes"]["changed"])
    assert not C.diff_empty(d)


def test_s6_3_提案_合并():
    s = C.create_empty_state()
    C.add_object_type(s, {"name": "seg"})
    C.create_branch(s, "b1")
    C.add_object_type(s, {"name": "tunnel"})
    C.switch_branch(s, "main")
    p = C.propose_merge(s, "b1")
    assert p["ok"], p.get("error")
    assert not C.propose_merge(s, "b1")["ok"]            # 重复 open 提案拒绝
    assert C.merge_proposal(s, p["proposalId"])["ok"]
    assert len(C.schema_of(s)["objectTypes"]) == 2       # main 拿到 tunnel
    assert s["proposals"][0]["status"] == "merged"


def test_s6_4_拒绝_空diff():
    s = C.create_empty_state()
    C.add_object_type(s, {"name": "seg"})
    C.create_branch(s, "b2")
    C.switch_branch(s, "main")
    assert not C.propose_merge(s, "b2")["ok"]            # 无变更提案拒绝
    C.switch_branch(s, "b2")
    C.add_object_type(s, {"name": "x"})
    C.switch_branch(s, "main")
    p = C.propose_merge(s, "b2")
    assert C.reject_proposal(s, p["proposalId"])["ok"]
    assert s["proposals"][0]["status"] == "rejected"
    assert len(C.schema_of(s)["objectTypes"]) == 1       # main 不变


# ── S7 种子完整性 ──

def test_s7_1_结构完整性():
    s = seed.traffic()
    assert C.validate_state(s) == []
    sch = s["schemas"]["main"]
    assert len(sch["objectTypes"]) == 5
    assert len(sch["linkTypes"]) == 3
    assert len(sch["actionTypes"]) == 3
    assert len(s["data"]["objects"]) == 20
    for t in sch["objectTypes"]:
        keys = [o["props"][t["primaryKey"]] for o in C.objects_of_type(s, t["name"])]
        assert len(set(keys)) == len(keys), t["name"] + " 主键唯一"
    for l in s["data"]["links"]:
        ids = {o["__id"] for o in s["data"]["objects"]}
        assert l["from"] in ids and l["to"] in ids, "link 端点存在"


def test_s7_2_空白种子():
    s = seed.blank()
    assert len(s["schemas"]["main"]["objectTypes"]) == 0
    assert len(s["data"]["objects"]) == 0


def test_s7_3_种子动作端到端_派遣_关闭():
    s = seed.traffic()
    sch = s["schemas"]["main"]
    dispatch = next(a for a in sch["actionTypes"] if a["name"] == "dispatch_team")
    idle = next(t for t in C.objects_of_type(s, "rescue_team") if t["props"]["status"] == "待命")
    open_inc = next(i for i in C.objects_of_type(s, "incident") if i["props"]["status"] == "待处置")
    r1 = C.run_action(s, dispatch["id"], {"params": {}, "targets": {"team": idle["__id"], "inc": open_inc["__id"]}})
    assert r1["needConfirm"]                             # 派遣需确认
    r2 = C.run_action(s, dispatch["id"], {"params": {}, "targets": {"team": idle["__id"], "inc": open_inc["__id"]},
                                          "confirmed": True})
    assert r2["ok"], r2.get("error")
    close = next(a for a in sch["actionTypes"] if a["name"] == "close_incident")
    r3 = C.run_action(s, close["id"], {"params": {}, "targets": {"inc": open_inc["__id"]}, "confirmed": True})
    assert r3["ok"], "处理中事件可关闭: " + str(r3.get("error", ""))
    inc = next(i for i in C.objects_of_type(s, "incident") if i["__id"] == open_inc["__id"])
    assert inc["props"]["status"] == "已关闭"            # 闭环完成
    assert len(s["audit"]) >= 2


def test_s7_4_上报事件动作():
    s = seed.traffic()
    sch = s["schemas"]["main"]
    report = next(a for a in sch["actionTypes"] if a["name"] == "report_incident")
    seg = C.objects_of_type(s, "road_segment")[0]
    before = len(C.objects_of_type(s, "incident"))
    r = C.run_action(s, report["id"], {
        "params": {"title": "三车追尾", "type": "事故", "severity": "较大"},
        "targets": {"seg": seg["__id"]}, "confirmed": True})
    assert r["ok"], r.get("error")
    assert len(C.objects_of_type(s, "incident")) == before + 1
    inc = next(i for i in C.objects_of_type(s, "incident") if i["props"]["title"] == "三车追尾")
    assert C.linked_objects(s, inc["__id"])[0]["object"]["__id"] == seg["__id"]
