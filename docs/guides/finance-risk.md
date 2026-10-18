# 指南:用 OntoForge 构建金融风控本体

把"本体驱动的风控"落到 OntoForge 的三件武器上:**Builder 建模 → Pipeline 物化 → Actions 运营**。场景概念参考自公开的风控本体实践(客户/账户/交易/设备四实体),代码全部可直接在 OntoForge 上运行。

数据流:

```
核心系统/支付网关导出 (CSV) → Pipeline(校验+物化+血缘) → 风控本体 → 处置动作(冻结/放行/复核) → 审计
```

## 1. 建模(Builder 平面)

四个对象类型 + 三条链接,用 Python 引擎建(等同于在工坊 UI 里点出来):

```python
import ontoforge as of

s = of.create_empty_state()
s["meta"]["ontologyName"] = "金融风控本体"

def T(n, l, icon, color):
    return of.add_object_type(s, {"name": n, "label": l, "icon": icon, "color": color})["id"]

cust = T("customer", "客户", "👤", "#2563eb")
acct = T("account", "账户", "💳", "#0891b2")
txn  = T("transaction", "交易", "💸", "#dc2626")
dev  = T("device", "设备", "📱", "#7c3aed")

def P(tid, n, l, bt, ev=None, req=None):
    of.add_property(s, tid, {"name": n, "label": l, "baseType": bt,
                             "enumValues": ev, "required": req})

P(cust, "customer_id", "客户号", "string", None, True)
P(cust, "risk_profile", "风险等级", "enum", ["低", "中", "高"])
P(cust, "kyc_status", "实名状态", "enum", ["已认证", "待认证", "已冻结"])
P(cust, "credit_score", "信用分", "number")

P(acct, "account_id", "账号", "string", None, True)
P(acct, "account_type", "账户类型", "enum", ["储蓄", "信用卡", "投资"])
P(acct, "balance", "余额", "number")
P(acct, "daily_limit", "日限额", "number")
P(acct, "status", "状态", "enum", ["正常", "冻结", "销户"])

P(txn, "transaction_id", "交易号", "string", None, True)
P(txn, "amount", "金额", "number")
P(txn, "type", "交易类型", "enum", ["转账", "支付", "提现"])
P(txn, "channel", "渠道", "enum", ["网银", "APP", "柜台"])
P(txn, "timestamp", "时间", "date")
P(txn, "risk_score", "风险评分", "number")
P(txn, "status", "状态", "enum", ["待复核", "已放行", "已拦截"])

P(dev, "device_id", "设备号", "string", None, True)
P(dev, "device_type", "设备类型", "string")
P(dev, "risk_level", "设备风险", "enum", ["可信", "陌生", "可疑"])

for tid, pk in [(cust, "customer_id"), (acct, "account_id"),
                (txn, "transaction_id"), (dev, "device_id")]:
    of.update_object_type(s, tid, {"primaryKey": pk})

of.add_link_type(s, {"name": "cust_owns_acct", "label": "持有", "from": "customer",
                     "to": "account", "cardinality": "1:N",
                     "keyMapping": {"fromKey": "customer_id", "toKey": "account_id"}})
of.add_link_type(s, {"name": "txn_on_acct", "label": "发生于", "from": "transaction",
                     "to": "account", "cardinality": "N:1",
                     "keyMapping": {"fromKey": "transaction_id", "toKey": "account_id"}})
of.add_link_type(s, {"name": "txn_via_dev", "label": "发起于", "from": "transaction",
                     "to": "device", "cardinality": "N:1",
                     "keyMapping": {"fromKey": "transaction_id", "toKey": "device_id"}})
```

## 2. 物化(Pipeline 平面)

核心系统每晚导出 `accounts.csv`,支付网关导出 `transactions.csv`(含账户号与设备号两列外键):

```python
of.register_dataset(s, "accounts", "accounts.csv")
of.register_dataset(s, "transactions", "transactions.csv")

mapping = {
    "name": "nightly_risk_sync",
    "objects": [
        {"dataset": "accounts", "objectType": "account", "key": "account_id",
         "properties": {
             "account_type": "acct_type",
             "balance": {"column": "balance", "transform": "float"},
             "daily_limit": {"column": "daily_limit", "transform": "float"},
             "status": "status"}},
        {"dataset": "transactions", "objectType": "transaction", "key": "transaction_id",
         "properties": {
             "amount": {"column": "amount", "transform": "float"},
             "type": "txn_type", "channel": "channel",
             "timestamp": "ts",
             "risk_score": {"column": "risk_score", "transform": "float"},
             "status": "status"}},
    ],
    "links": [
        {"linkType": "txn_on_acct", "dataset": "transactions",
         "fromColumn": "transaction_id", "toColumn": "account_id"},
        {"linkType": "txn_via_dev", "dataset": "transactions",
         "fromColumn": "transaction_id", "toColumn": "device_id"},
    ],
}

preview = of.run_pipeline(s, mapping, dry_run=True)   # 先预览
r = of.run_pipeline(s, mapping)                       # 全量校验 → 原子物化 → 血缘
```

要点:任何一行脏数据(金额无法解析、枚举越界、外键指向不存在的账户)都会让**整批**拒绝并逐行报错——脏数据永远进不了本体;每次运行的批次血缘留在 `state["pipelineRuns"]`,满足审计追溯。

## 3. 运营(Actions 平面)

高风险交易的处置动作:规则闸门(仅"待复核"可处置)+ 确认预览 + 原子编辑 + 审计/通知:

```python
of.add_action_type(s, {"name": "block_transaction", "label": "拦截交易",
    "targets": [{"role": "txn", "type": "transaction"},
                {"role": "acct", "type": "account"}],
    "params": [{"name": "reason", "label": "拦截原因", "type": "string", "required": True}],
    "rules": [{"target": "txn", "field": "status", "op": "eq", "value": "待复核",
               "message": "仅待复核交易可拦截"},
              {"target": "acct", "field": "status", "op": "eq", "value": "正常",
               "message": "账户非正常状态"}],
    "submissionCriteria": {"requireConfirm": True, "note": "拦截后账户将冻结"},
    "edits": [{"op": "set", "target": "txn", "field": "status", "value": "已拦截"},
              {"op": "set", "target": "acct", "field": "status", "value": "冻结"}],
    "sideEffects": [{"type": "notify", "config": {"to": "风控值班", "text": "交易已拦截:{{param.reason}}"}}]})
```

典型处置流:`search_objects` 找到高分交易 → `linked_objects` 沿链接查同设备/同账户的关联交易 → `run_action(..., confirmed=True)` 拦截 → `audit_for({"objectId": ...})` 回放完整处置历史。

## 4. AI 扩展(AIP 骨架)

风险评分这类"可复用的领域判断"注册为 Logic Function,未来由 Agent 层编排调用:

```python
def high_risk_open_txns(state, params):
    th = params["threshold"]
    return [o["props"]["transaction_id"]
            for o in of.objects_of_type(state, "transaction")
            if (o["props"].get("risk_score") or 0) >= th
            and o["props"].get("status") == "待复核"]

of.register_logic("high_risk_open_txns", high_risk_open_txns,
                  description="超过阈值的待复核交易",
                  params_schema={"threshold": {"type": "number", "required": True}})
of.invoke_logic(s, "high_risk_open_txns", {"threshold": 0.8})
```

## 最佳实践对应

| 风控实践 | OntoForge 落点 |
|---|---|
| 批量而非单条 | pipeline 一次一批,原子成败 |
| 审计与合规 | `audit` 动作留痕 + `pipelineRuns` 批次血缘 |
| 决策可追溯 | 对象/链接/动作全在一份可序列化 state,随时导出 |
| 模型/规则监控 | Logic Function 统一入口,便于外围挂监控 |
```

下一步:把"定时风险扫描"交给调度器(见 [roadmap](../roadmap.md) 的 pipeline 调度),把"实时反欺诈"交给 streaming 接入——两者都是 v1 之后的既定方向。
