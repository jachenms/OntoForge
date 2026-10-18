"""种子数据集(CORE 的 SEED 段):城市交通应急本体 + 空白本体。"""
from __future__ import annotations

from ._common import State, uid
from .state import create_empty_state
from .schema import add_object_type, add_property, update_object_type
from .links import add_link_type, create_link
from .actions import add_action_type


def traffic() -> State:
    """城市交通应急示例:5 对象类型 / 3 链接类型 / 3 动作类型 / 20 实例。"""
    s = create_empty_state()
    s["meta"]["ontologyName"] = "城市交通应急本体"

    def T(n, l, icon, color):
        return add_object_type(s, {"name": n, "label": l, "icon": icon, "color": color})["id"]

    seg = T("road_segment", "路段", "🛣️", "#2563eb")
    inc = T("incident", "交通事件", "⚠️", "#dc2626")
    team = T("rescue_team", "应急队伍", "🚒", "#ea580c")
    veh = T("vehicle", "车辆", "🚗", "#0891b2")
    hub = T("hub", "枢纽", "🏗️", "#7c3aed")

    def P(tid, n, l, bt, ev=None, req=None):
        add_property(s, tid, {"name": n, "label": l, "baseType": bt, "enumValues": ev, "required": req})

    # 路段
    P(seg, "seg_id", "编号", "string", None, True); P(seg, "name", "名称", "string")
    P(seg, "level", "等级", "enum", ["高速", "主干", "次干", "支路"]); P(seg, "length_km", "长度(km)", "number")
    P(seg, "status", "路况", "enum", ["畅通", "缓行", "拥堵", "中断"])
    # 事件
    P(inc, "inc_id", "编号", "string", None, True); P(inc, "title", "标题", "string")
    P(inc, "type", "类型", "enum", ["事故", "故障车", "恶劣天气", "占道施工", "其他"])
    P(inc, "severity", "严重度", "enum", ["一般", "较大", "重大", "特别重大"])
    P(inc, "status", "状态", "enum", ["待处置", "处理中", "已关闭"]); P(inc, "reported_at", "上报时间", "date")
    # 队伍
    P(team, "team_id", "编号", "string", None, True); P(team, "name", "名称", "string")
    P(team, "kind", "类型", "enum", ["交警", "消防", "医疗", "路政", "清障"])
    P(team, "status", "状态", "enum", ["待命", "出动", "休整"]); P(team, "members", "人数", "number")
    # 车辆
    P(veh, "veh_id", "编号", "string", None, True); P(veh, "plate", "车牌", "string")
    P(veh, "kind", "类型", "enum", ["巡逻车", "清障车", "救护车", "消防车"])
    P(veh, "status", "状态", "enum", ["可用", "任务中", "维修"])
    # 枢纽
    P(hub, "hub_id", "编号", "string", None, True); P(hub, "name", "名称", "string")
    P(hub, "kind", "类型", "enum", ["立交", "隧道", "桥梁", "收费站"]); P(hub, "district", "辖区", "string")
    for tid, pk in [(seg, "seg_id"), (inc, "inc_id"), (team, "team_id"), (veh, "veh_id"), (hub, "hub_id")]:
        update_object_type(s, tid, {"primaryKey": pk})

    # 链接类型
    add_link_type(s, {"name": "inc_on_seg", "label": "发生于", "from": "incident", "to": "road_segment",
                      "cardinality": "N:1", "keyMapping": {"fromKey": "inc_id", "toKey": "seg_id"}})
    add_link_type(s, {"name": "team_assigned", "label": "派遣至", "from": "rescue_team", "to": "incident",
                      "cardinality": "M:N", "keyMapping": {"fromKey": "team_id", "toKey": "inc_id"}})
    add_link_type(s, {"name": "veh_belongs", "label": "隶属于", "from": "vehicle", "to": "rescue_team",
                      "cardinality": "N:1", "keyMapping": {"fromKey": "veh_id", "toKey": "team_id"}})

    # 动作类型
    add_action_type(s, {"name": "report_incident", "label": "上报事件",
        "targets": [{"role": "seg", "type": "road_segment"}],
        "params": [{"name": "title", "label": "标题", "type": "string", "required": True},
                   {"name": "type", "label": "类型", "type": "enum",
                    "enumValues": ["事故", "故障车", "恶劣天气", "占道施工", "其他"], "required": True},
                   {"name": "severity", "label": "严重度", "type": "enum",
                    "enumValues": ["一般", "较大", "重大", "特别重大"], "required": True}],
        "rules": [], "submissionCriteria": {"requireConfirm": False},
        "edits": [{"op": "create", "target": "inc", "objectType": "incident",
                   "props": {"inc_id": "{{auto}}", "title": "{{param.title}}", "type": "{{param.type}}",
                             "severity": "{{param.severity}}", "status": "待处置", "reported_at": "{{now}}"}},
                  {"op": "addLink", "linkType": "inc_on_seg", "from": "inc", "to": "seg"}],
        "sideEffects": [{"type": "notify", "config": {"to": "调度中心", "text": "新事件上报:{{param.title}}"}}]})
    add_action_type(s, {"name": "dispatch_team", "label": "派遣队伍",
        "targets": [{"role": "team", "type": "rescue_team"}, {"role": "inc", "type": "incident"}],
        "params": [],
        "rules": [{"target": "team", "field": "status", "op": "eq", "value": "待命", "message": "仅待命队伍可派遣"},
                  {"target": "inc", "field": "status", "op": "neq", "value": "已关闭", "message": "已关闭事件不可派遣"}],
        "submissionCriteria": {"requireConfirm": True, "note": "派遣后队伍状态将变为出动"},
        "edits": [{"op": "set", "target": "team", "field": "status", "value": "出动"},
                  {"op": "set", "target": "inc", "field": "status", "value": "处理中"},
                  {"op": "addLink", "linkType": "team_assigned", "from": "team", "to": "inc"}],
        "sideEffects": [{"type": "notify", "config": {"to": "队伍负责人", "text": "你队已被派遣"}},
                        {"type": "webhookLog", "config": {"url": "https://example.internal/hook"}}]})
    add_action_type(s, {"name": "close_incident", "label": "关闭事件",
        "targets": [{"role": "inc", "type": "incident"}], "params": [],
        "rules": [{"target": "inc", "field": "status", "op": "eq", "value": "处理中", "message": "仅处理中事件可关闭"}],
        "submissionCriteria": {"requireConfirm": True},
        "edits": [{"op": "set", "target": "inc", "field": "status", "value": "已关闭"}],
        "sideEffects": [{"type": "notify", "config": {"to": "调度中心", "text": "事件已关闭"}}]})

    # 实例
    def O(type_, props):
        o = {"__id": uid("obj"), "__type": type_, "props": props}
        s["data"]["objects"].append(o)
        return o["__id"]

    g1 = O("road_segment", {"seg_id": "SEG-001", "name": "成渝立交段", "level": "高速", "length_km": "12.5", "status": "拥堵"})
    g2 = O("road_segment", {"seg_id": "SEG-002", "name": "机场快速路", "level": "主干", "length_km": "8.2", "status": "畅通"})
    g3 = O("road_segment", {"seg_id": "SEG-003", "name": "两江隧道连接线", "level": "主干", "length_km": "4.6", "status": "缓行"})
    g4 = O("road_segment", {"seg_id": "SEG-004", "name": "大学城南路", "level": "次干", "length_km": "3.1", "status": "畅通"})
    g5 = O("road_segment", {"seg_id": "SEG-005", "name": "北环大道", "level": "高速", "length_km": "15.0", "status": "中断"})
    e1 = O("incident", {"inc_id": "INC-1001", "title": "两车追尾", "type": "事故", "severity": "较大", "status": "处理中", "reported_at": "2026-10-16"})
    e2 = O("incident", {"inc_id": "INC-1002", "title": "货车故障占道", "type": "故障车", "severity": "一般", "status": "待处置", "reported_at": "2026-10-17"})
    e3 = O("incident", {"inc_id": "INC-1003", "title": "团雾预警", "type": "恶劣天气", "severity": "重大", "status": "待处置", "reported_at": "2026-10-17"})
    e4 = O("incident", {"inc_id": "INC-1004", "title": "夜间占道施工", "type": "占道施工", "severity": "一般", "status": "待处置", "reported_at": "2026-10-15"})
    e5 = O("incident", {"inc_id": "INC-1005", "title": "轻微刮擦", "type": "事故", "severity": "一般", "status": "已关闭", "reported_at": "2026-10-14"})
    t1 = O("rescue_team", {"team_id": "TM-01", "name": "交警一大队", "kind": "交警", "status": "待命", "members": "24"})
    t2 = O("rescue_team", {"team_id": "TM-02", "name": "消防特勤站", "kind": "消防", "status": "出动", "members": "30"})
    O("rescue_team", {"team_id": "TM-03", "name": "急救中心二组", "kind": "医疗", "status": "待命", "members": "12"})
    t4 = O("rescue_team", {"team_id": "TM-04", "name": "清障突击队", "kind": "清障", "status": "休整", "members": "8"})
    v1 = O("vehicle", {"veh_id": "VH-01", "plate": "渝A·D1023", "kind": "巡逻车", "status": "可用"})
    v2 = O("vehicle", {"veh_id": "VH-02", "plate": "渝A·Q2087", "kind": "清障车", "status": "任务中"})
    O("vehicle", {"veh_id": "VH-03", "plate": "渝B·J3301", "kind": "救护车", "status": "可用"})
    O("vehicle", {"veh_id": "VH-04", "plate": "渝A·X5566", "kind": "消防车", "status": "维修"})
    O("hub", {"hub_id": "HUB-01", "name": "成渝立交", "kind": "立交", "district": "九龙坡"})
    O("hub", {"hub_id": "HUB-02", "name": "两江隧道", "kind": "隧道", "district": "江北"})

    lt = lambda name: next(l["id"] for l in s["schemas"]["main"]["linkTypes"] if l["name"] == name)  # noqa: E731
    for e, g in [(e1, g1), (e2, g2), (e3, g5), (e4, g3), (e5, g4)]:
        create_link(s, lt("inc_on_seg"), e, g)
    create_link(s, lt("veh_belongs"), v1, t1)
    create_link(s, lt("veh_belongs"), v2, t4)
    create_link(s, lt("team_assigned"), t2, e1)
    return s


def blank() -> State:
    s = create_empty_state()
    s["meta"]["ontologyName"] = "空白本体"
    return s
