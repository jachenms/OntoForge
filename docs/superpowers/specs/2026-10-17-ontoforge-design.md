# OntoForge 本体工坊 — 设计规格(Palantir Foundry/Ontology Manager 概念模仿原型)

日期:2026-10-17 · 状态:已获用户批准
依据:`research/逆向分析-Foundry-Ontology.md`(公开文档证据驱动,观测/推断/未知分离)

## 0. 定位与红线

- **用途**:可操作产品原型 —— 浏览器里真建 object/link/action type、真跑 action 写回数据,localStorage 持久化
- **形态**:单文件 vanilla HTML(`ontoforge.html`),file:// 直开,零依赖,与 workbench.html 形态一致
- **法律红线**:不用 Palantir 商标/Logo/截图/品牌视觉/文案;只模仿概念与交互模式;不声称兼容或官方
- **UI 语言**:中文;视觉为企业工作台风(深色侧边栏+浅色主区),自有配色

## 1. 四大能力域(全量)

1. **Ontology Manager 建模**(语义层)
2. **Action 设计与执行闭环**(动力层)
3. **Object Explorer 探索**(消费层)
4. **分支/提案/评审治理**(schema 级)

## 2. 界面骨架(OMA 同构)

```
┌──────────────── Top bar ────────────────────────────────┐
│ 资源搜索 ⌕   ＋新建(类型/属性/动作)   🌿分支切换/新建    │
├──────────┬──────────────────────────────────────────────┤
│ Sidebar  │  主视图区                                     │
│ Discover │  Discover / ObjectType / Property / LinkType /│
│ 对象类型  │  ActionType / Explorer / ObjectView / 分支中心 │
│ 链接类型  │                                              │
│ 动作类型  │                                              │
│ 共享属性  │                                              │
│ Explorer │                                              │
│ 分支中心  │                                              │
└──────────┴──────────────────────────────────────────────┘
```

- **Discover**:收藏/最近查看 object types;新用户引导
- **ObjectType view**(OMA 7-section Overview):① 元数据 ② Properties ③ Action types ④ Link type graph(Canvas 关系图,可点击进 LinkType view)⑤ Dependents ⑥ Data(实例预览)⑦ Usage(调用统计)
- **Property editor**:baseType/必填/格式化/枚举值/共享属性挂载
- **LinkType view**:Overview(基数、两端类型)+ Datasources(外键映射)
- **ActionType view**:Overview / Logic(参数→规则→提交条件→edits→副作用 流水线编辑器)/ Observability(近30天调用柱状图,源自审计日志)
- **Object Explorer**:左类型列表+搜索;中结果表(列可配);右 Object View(属性卡、链接对象 chips 跳转、可用 actions 直接 apply、该对象编辑历史)
- **分支中心**:分支列表、提案 diff(新增/修改/删除的类型)、评审接受/拒绝、合并

## 3. 数据模型(STATE 单例树)

```js
state = {
  meta: { ontologyName, createdAt, rev },
  branch: { current: "main", list: [{ name, baseRev, status }] },
  proposals: [{ id, branch, changeset, status: open|merged|rejected }],
  schema: {
    objectTypes: [{ id, name, label, icon, color, primaryKey,
                    properties: [{ id, name, label, baseType: string|number|boolean|date|enum,
                                   enumValues?, required?, formatting? }],
                    sharedPropRefs: [] }],
    linkTypes:   [{ id, name, label, from, to, cardinality: "1:N"|"M:N",
                    keyMapping: { fromKey, toKey } }],
    actionTypes: [{ id, name, label, targetTypes: [],
                    params:  [{ name, label, type, required, enumValues? }],
                    rules:   [{ field, op, value, message }],
                    submissionCriteria: { requireConfirm, note? },
                    edits:   [{ op: set|create|delete|addLink|removeLink,
                                target, field?, valueTemplate? }],
                    sideEffects: [{ type: notify|webhookLog, config }] }],
    sharedProps: [{ id, name, label, baseType }]
  },
  data: {
    objects: [{ __id, __type, props: {} }],     // 实例数据全局共享(见 §5 简化)
    links:   [{ __id, __type, from, to }]
  },
  audit: [{ ts, branch, actor, actionId, summary, diff }],
  ui:   { view, selection, favorites, recent }
}
```

- **STORE**:localStorage 防抖持久化;导入/导出 JSON(带 schema 校验);损坏时从备份键恢复
- **CORE 为纯函数集**,置于 `<script id="core">`,Node 可提取单测

## 4. Action 执行引擎(闭环核心)

```
runAction(actionType, paramValues, targets):
 1 参数校验(类型/必填/枚举)
 2 rules 逐条校验(field op value,失败即返回规则 message)
 3 submissionCriteria(需确认则弹确认框)
 4 依序应用 edits:valueTemplate 支持 {{param.x}} / {{target.prop}}
 5 副作用:notify → 通知中心;webhookLog → 审计日志标记
 6 写审计(前后 diff)
 7 持久化 + 重渲染
```

- 任一步失败:返回结构化错误,UI 内联展示,不产生半提交(先模拟应用,全过才落)
- **Function 简化(明确 YAGNI)**:不做代码编辑器;edits 仅支持模板表达式与枚举映射

## 5. 分支治理(简化声明)

- 分支仅隔离 **schema**(object/link/action types 及共享属性)
- 实例数据(data.objects/links)全局共享,不随分支 —— 诚实简化,UI 中注明
- 流程:建分支 → 改 schema → 提案(diff 视图)→ 评审(接受/拒绝)→ 合并回 main

## 6. 种子数据(交通应急)

- **ObjectTypes**:路段 RoadSegment、交通事件 Incident、应急队伍 RescueTeam、车辆 Vehicle、枢纽 Hub
- **LinkTypes**:Incident `occurredOn` RoadSegment(N:1)、RescueTeam `assignedTo` Incident(M:N)、Vehicle `belongsTo` RescueTeam(N:1)
- **ActionTypes**:
  - 上报事件(create Incident + addLink occurredOn)
  - 派遣队伍(set team.status → create assignedTo link → notify)
  - 关闭事件(rule:仅 status=处理中 可关;submissionCriteria 需确认;notify 副作用)
- ~20 个对象实例,中文 label
- 首页可切换:**交通应急种子 / 空白本体**

## 7. 错误处理

- 表单校验内联(主键唯一、属性名冲突、外键指向存在类型)
- action 失败给规则级 message;半提交防护(§4)
- localStorage 损坏 → 备份键恢复 + toast
- 导入 JSON → schema 校验,拒绝给可操作错误信息

## 8. 测试

- `smoke.mjs`(oag_eval 同款):Node 提取 `<script id="core">` 段直接断言
- 覆盖:action 引擎全路径(参数/规则/确认/edits/副作用/审计)、分支 diff/merge、查询过滤、种子完整性(类型/链接/实例引用一致)
- 目标:smoke 全绿后方可交付;headless 浏览器验证交互路径(上传/建模/跑 action/合并)

## 9. 交付物

- `ontoforge.html`(单文件,含 CORE/VIEWS/CSS)
- `smoke.mjs`
- `research/`(已完成,逆向分析证据)
