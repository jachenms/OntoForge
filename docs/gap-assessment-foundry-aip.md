# OntoForge × Foundry / AIP 差距评估

日期:2026-11-08。对照基线:仓库 `1.1.0`(`python/pyproject.toml`、`ontoforge.__version__`)。本文只记录**已经在代码或已入库设计稿里能核对到的事实**。Foundry / AIP 的概念名称来自 [research/逆向分析-Foundry-Ontology.md](research/逆向分析-Foundry-Ontology.md)(公开文档逆向,非运行时观测);每一条「有 / 没有」都回指本仓库的模块。

## English summary

OntoForge already implements a readable ontology loop: object / link / action types, a guarded `run_action` engine, schema branches with proposal diffs, and a Python-only batch pipeline that validates then upserts by primary key and records batch lineage. The AIP surface is a process-local function registry (`register_logic` / `invoke_logic` / `list_logic`) with no model calls.

It is not an enterprise Foundry or AIP. There is no server package (the 2026-10-24 FastAPI design is a spec only), no auth, no scheduler, no streaming, no column lineage, no incremental sync, no Workshop runtime, and no agent tool protocol that includes parameter types. Stated non-goals — zero runtime dependencies on the engine, no bundled LLM, no multitenant or role model — cap how far “parity” can go. The next three PRs should stay inside that cap: (1) a JSON tool catalog over actions, queries, and logic; (2) column-level lineage and honest pipeline run records; (3) a narrow optional server extra, not the full v2 milestone.

## 1. 核对范围

| 读过 | 用来判断什么 |
|---|---|
| `ontoforge.html` 的 CORE / SEED / UI | 工坊实际视图与 JS 契约 |
| `python/src/ontoforge/*.py` | 引擎、pipeline、AI 的真实 API |
| `python/tests/`、`smoke.mjs`、`.github/workflows/ci.yml` | 测试覆盖边界 |
| `docs/roadmap.md`、`docs/architecture.md`、`docs/pipeline.md` | 已承诺与明确不做 |
| `docs/superpowers/specs/2026-10-18-pipeline-repositioning-design.md` | pipeline v1 的裁剪 |
| `docs/superpowers/specs/2026-10-24-server-architecture-design.md` | **已确认、未实现**的服务端方案 |
| `examples/traffic_pipeline.py`、`docs/guides/finance-risk.md` | 对外示例是否与 API 一致 |

未把设计稿里的 `server/`、cron、Docker、双模式 UI 算作已交付。仓库里没有 `python/src/ontoforge/server/`、没有 `Dockerfile`、版本号仍是 `1.1.0`。

根 README 的 Python 快速开始曾把动作 **name** 当成 `run_action` 的 id,并把 `confirmed` 写成关键字参数。函数签名是 `run_action(state, action_id, input)`,`action_id` 是类型 id,`confirmed` 在 `input` 字典里。该示例已按 `python/README.md` 与 `actions.py` 改对。

测试规模(与代码一致,不是 README 口号):`smoke.mjs` 39 条断言只打 JS CORE;`verify_ui.mjs` 21 条只打工坊;`pytest` 为 `test_core.py` 29 + `test_pipeline.py` 14 + `test_ai.py` 3。CI 的 Python 步骤注释仍写「29 tests」,实际命令是 `pytest python`,46 条都会跑。JS 与 Python 之间**没有**自动契约测试(服务端设计稿 §11 提议过 `tests/contract/`,目录不存在)。

## 2. 明确不做,以及它如何卡住「企业级对等」

[roadmap.md](roadmap.md) 的「明确不做」和两份已批准设计稿,比功能清单更硬:

| 约束 | 出处 | 对「对等 Foundry / AIP」的含义 |
|---|---|---|
| 核心引擎零运行时依赖(`dependencies = []`) | roadmap; `pyproject.toml`; pipeline 设计稿「YAGNI」 | 调度器、数据库、HTTP 客户端、LLM SDK 都不能进 `ontoforge` 核心包。企业能力只能是可选 extra,或文档化的外部调用方式。 |
| 不绑定任何 LLM 供应商;AI 层零模型调用 | roadmap; `ai.py` 模块文档; pipeline 设计稿 | AIP Logic / Agent Studio 式体验不会在本仓库里「接上一个模型」就出现。调用方自备模型,本仓库只提供可校验的工具面。 |
| 不做多租户,不做角色 / 对象级权限 | roadmap; 服务端设计稿 §1、§10 | 即使按设计稿做出可选 Bearer token,那也只是部署口令。Foundry 的 Roles、object security、marking、restricted views **不在产品边界内**,不能写成下一阶段的默认目标。 |
| 单文件工坊 + `localStorage`,pipeline 不进 UI | `ontoforge.html`; pipeline 设计稿「明确不做」 | 浏览器原型的状态体量、协作和运维上限是原型上限。工坊里看不到 dataset、mapping、血缘。 |
| pipeline v1 不做增量、调度、streaming | `pipeline.py` 模块文档; `docs/pipeline.md` | 这三项是路线图项,不是漏做的 v1 缺陷。评估把它们放在 P1/P2,而不是把 v1 说成「差一个开关」。 |

服务端设计稿(2026-10-24)在「零依赖」上开了一道**尚未落地**的口子:核心保持 zero-dep,`server` extra 允许 FastAPI / SQLite。这和 roadmap 里绝对的「不引入运行时依赖」字面冲突;本评估以「核心零依赖,服务端依赖只存在于尚未编写的 extra」为准,并在 roadmap 里改成了这句。

因此「企业级」在接下来几个 PR 里的可操作定义是:**单本体、单写者、引擎仍是纯函数,外面可以包一个可选进程**。多租户、对象级权限、自带大模型,都要先改「明确不做」,而不是在评估清单里排期。

另一条体量约束不在 roadmap 里,但代码如此:一份本体是一个 JSON 兼容 dict。`serialize` 把整个 state 交出去; `register_dataset` 把全部行放进 `state["datasets"][id]["rows"]`。浏览器侧落 `localStorage`。这不是调优问题,是「整库即文档」的架构选择。服务端设计稿自己也写了:对象量到十万级再在文档旁边加只读投影,不改契约。

## 3. 相对 Foundry 四个平面,现在已经成立的部分

### 3.1 Ontology(语义层)

已有,并且 JS CORE(`ontoforge.html` `<script id="core">`)与 `python/src/ontoforge/` 按同一 `{ok, error}` 契约各写了一份:

- 对象类型、属性、主键。`BASE_TYPES = string | number | boolean | date | enum`(`_common.py`)。主键只能在属性建成后用 `update_object_type` 设置。
- 链接类型与基数 `1:1 | 1:N | N:1 | M:N`。`create_link`、动作里的 `addLink`、pipeline 物化都会拒绝违反基数的边。
- 共享属性注册表,以及按 id 挂到类型上的 `sharedPropRefs`。工坊有独立视图。
- 删除保护:类型仍有实例、被链接或动作引用时 `delete_object_type` 拒绝;链接类型仍有实例时不可删;主键属性不可删。
- 工坊信息架构贴近 Ontology Manager 的对象类型页:元数据、属性、引用它的动作、链接图、依赖、前 20 条数据、用量计数(`APP.VIEWS.objectType`)。动作类型有 Overview / Logic / Observability 三页;Observability 用 `usage_by_day` 画近 30 天审计次数。
- Object Explorer(按类型子串搜索,表格最多画 50 行)+ Object View(属性、一跳链接、就地跑动作、最近 10 条审计)。顶栏全局搜索命中**第一个**类型、动作或对象后直接跳转,不是结果列表。
- 种子 `seed.traffic()`:5 个对象类型、3 个链接类型、3 个动作、20 个对象。金融风控指南是文档演练,不是第二个种子包。

还不是 Foundry 语义层的部分,见 §4。这里先标三个容易误读的「有字段、没语义」:

- `property.required` 会存、工坊能改,但 `pipeline.py` 不读它,动作 edits 也不按属性 required 校验。必填只对**动作参数**生效(`_validate_params`)。
- `property.formatting` 在 schema 里有键,属性编辑器没有入口,展示层也不使用。
- `linkType.keyMapping`(`fromKey` / `toKey`)只被链接类型页保存。`create_link` 与 `run_pipeline` 都不读它。pipeline 的链接端点来自 mapping 里显式的 `fromColumn` / `toColumn`,解析靠对象主键字符串,不靠 keyMapping。
- 共享属性**不会**变成对象类型的 `properties` 条目。pipeline 只认 `t["properties"]`。挂上共享属性不等于可以物化同名列,除非另建一个同名本地属性(对象类型页的 🧩 标记就是这个名字巧合)。

没有 interface、function type、derived property、struct / value type、object set 类型。研究笔记把这些列为 Foundry 概念;本仓库没有对应模块。

### 3.2 Actions(动力层)

`run_action`(`actions.py`,JS 同名 `runAction`)的顺序是确定的:动作 id 查找 → 参数校验 → target 解析(角色、类型)→ 规则 → `requireConfirm` → 在 `data` 的深拷贝上应用 edits → 成功才整块换上 → 副作用 → 写 `state["audit"]`。

- 规则运算符:`eq neq in notIn gt lt ge le contains`。`in` 的右值按 `|` 拆。
- Edits:`set | create | delete | addLink | removeLink`,模板 `{{param.*}}`、`{{targets.role.*}}`、`{{now}}`、`{{auto}}`。
- 提交条件只有 `requireConfirm` 布尔值。未确认时返回 `{ok: false, needConfirm: true, preview}`。
- 副作用两种:`notify` 往 `state["notices"]` 追加一条;`webhookLog` 追加一条效果说明,文案固定为「已记录 webhook 调用(原型不落网)」。没有 HTTP。
- 审计含时间、当前分支名、`actor`(缺省「本地用户」)、diff 文本、副作用摘要。`audit_for` 可按 `actionId` 过滤;按 `objectId` 过滤是在 diff **字符串**里找 id 或类型名,不是结构化外键。

这覆盖了 Foundry action 流水线里「参数 → 校验 → 提交条件 → 一次事务编辑 → 通知」的形状。它没有覆盖:谁可以跑、写回源系统、函数型逻辑、按对象集批量、以及失败规则的类型安全(见 §4.2)。

### 3.3 Pipeline(批量物化)

只存在于 Python(`pipeline.py`)。JS 工坊没有 dataset / mapping / 血缘界面,CORE 也没有对等函数。

已实现且有测试:

- `register_dataset`:内存行、`.csv`(全字符串列)、`.json`(dict 数组)。同名拒绝。`list_datasets` 去掉 `rows`。
- `run_pipeline`:先做结构校验,再逐行校验,全部通过才写对象和链接。任一行错误则不改 `data`(失败运行仍会追加 `pipelineRuns`,见下)。
- 按主键 upsert,`__id` 稳定;未出现在本次 `properties` 里的已有属性保留;空单元格跳过该属性,不把旧值清掉。
- 链接按 `(linkType, fromId, toId)` 去重;基数与既有边、批内边一起预检。
- `dry_run=True` 只返回 `wouldCreate / wouldUpdate / wouldLink`,不写 state、不记血缘。
- 成功血缘:`pipelineRuns[]` 含 mapping 名、dataset 名列表、时间、counts、`objectIds`。行级失败记 `status: "failed"`、前 10 条错误和 `errorCount`。

`examples/traffic_pipeline.py` 与 `docs/pipeline.md` 描述的就是这套行为。`docs/guides/finance-risk.md` 的 mapping 形状(`fromColumn` / `toColumn`)与代码一致;2026-10-18 设计稿里的 `from: {dataset, key}` 嵌套形状**没有**实现,以代码和 `docs/pipeline.md` 为准。

### 3.4 Branching(schema 治理)

`branches.py` / 工坊「分支中心」:

- 分支隔离的是 `state["schemas"][branch]`。实例 `data.objects` / `data.links` 全局共享。工坊文案写明这是原型简化。
- `create_branch` **总是克隆 main**,然后切过去。没有从当前分支再分叉。
- `diff_schemas` 按 name 对齐,比较时去掉 `id`。提案在 main 上发起,同一分支同时只能有一个 `open` 提案。
- 合并:`merge_proposal` 把该分支的 schema **整份克隆覆盖** `schemas["main"]`,再 `_bump`。评审时看到的 `proposal.diff` 不参与合并计算。
- 拒绝只改提案状态。没有评论、没有评审人、没有保护分支。

对单用户本地工坊,这条链路是通的:`smoke` 与分支中心 E2E 覆盖创建、diff、合并。它不是 Foundry 的本体 Git(没有三方合并,也没有「main 在提案打开后继续前进」的冲突检测)。

## 4. 相对 Foundry 的缺口

下面每条都是「代码里缺这块」,不是平台功能菜单的逐项翻译。

### 4.1 运行形态、身份、运维

| 缺口 | 代码事实 |
|---|---|
| 没有可部署进程 | 无 `server/` 包、无 CLI `serve`、无 Docker。设计稿 §4 的 `/api/v1/*` 一个都没有。 |
| 没有认证 | 无用户、无 token 中间件。`actor` 是调用方传入的字符串。 |
| 没有多租户 / 权限 | 与「明确不做」一致。一份 state 就是整个本体。 |
| 没有健康检查、指标、告警 | 动作用量来自内存审计计数;pipeline 只有 `pipelineRuns` 列表。没有独立于业务 state 的运维通道。 |
| 双实现靠人工同步 | 改 CORE 必须同时改 HTML 与 Python。pipeline 与 `ai.py` 只有 Python。没有字节级契约测试。 |
| 写路径不封闭 | 引擎函数就地改 dict。`create_link` / `delete_link` 和 `run_pipeline` 都不写 `audit`。调用方也可以直接改 `state["data"]`。只有 `run_action` 留审计。 |

### 4.2 Ontology 与 Actions 的语义缺口

- **查询面**只有列表扫描:`objects_of_type`、`search_objects`(当前类型、仅字符串属性的子串)、`linked_objects`(一跳)、`audit_for`、`usage_by_day`。没有过滤 AST、聚合、排序、分页游标、对象集、保存的探索。Explorer 的「前 50 行」是 UI 切片,不是 API。
- **属性系统**停在五种 base type。没有条件格式、edit-only、derived、struct、value type、type class。`date` 在 pipeline 里只要求「是字符串」,不解析日期。
- **共享属性与外键映射**是建模装饰,不参与物化(§3.1)。
- **动作规则的数值比较**在 `_check_rules` 里直接 `float(left)`。左值不是数值时抛出 `ValueError` 或 `TypeError`(例如字符串 `"nope"`),而 `run_action` 没有接住,于是破坏了「一律返回 `{ok, error}`」的契约。字符串比较那几支是安全的。
- **副作用**不到达外部系统。Foundry 文档里的 write-back dataset,这里不存在;用户编辑和 pipeline upsert 写进同一份 `data`,没有「用户编辑 vs 下次同步」的冲突策略。pipeline 对已映射属性是后写覆盖。
- **对象存储**是数组扫描。没有索引、没有 Object Storage 式的编辑历史(历史只存在于动作 diff 文本)。`delete` edit 会拆掉相关链接,但不会记一条可重放的编辑日志。

### 4.3 Pipeline

路线图已经列了增量、调度、streaming、列级血缘、更多数据源。对照代码,还要补上路线图没写清楚的行为缺口:

| 行为 | 现在 |
|---|---|
| 列级血缘 | 运行记录只有 dataset **名字**和产出对象 id。列、transform、属性名留在当次入参 mapping 里,不写入 `pipelineRuns`。mapping 本身不落 state。 |
| 结构校验失败 | `_validate_mapping` 失败直接返回,不追加 run。只有行级失败才记 `status: "failed"`。 |
| 源端消失的行 | upsert only。批次里没出现的主键不会删除,也没有计数。空单元格不清空旧值。不能表达「以本次快照为准」。 |
| 增量 | 无 watermark、无变更列。每次全表读入 state。 |
| 调度 | 无 cron、无作业表。设计稿里的 `scheduler.py` 未建。roadmap 的原意是外部调度器调用 `run_pipeline`。 |
| 流 | 无事件入口、无微批。 |
| 数据源 | 仅 csv / json / rows。无 JSONL、数据库游标、HTTP。注册时整表复制进 state。 |
| 失败原子性的例外 | 行级失败不改对象,但会改 `pipelineRuns`。`dry_run` 连血缘也不写。结构错误连血缘都没有。 |
| 工坊 | 无 UI。血缘无法在 `ontoforge.html` 里查看。 |

### 4.4 分支治理

- 合并是整 schema 替换。main 在分支创建之后的修改会被盖掉;提案保存的 diff 只供展示。
- 实例全局共享,所以「在分支上删除一个类型」会被**所有分支可见的实例**挡住(`delete_object_type` 查的是 `state["data"]`)。schema 分支表达不了「这批实例只在本分支存在」。
- 没有迁移、没有跨本体、没有场景(what-if)对象。研究笔记里的 Ontology scenarios 无对应实现。

### 4.5 Workshop 与应用层

工坊是 Ontology Manager 式建模器,不是可发布的业务应用。没有页面/组件模型,没有只读仪表板,没有可嵌入的图表(动作 Observability 的柱是内联 HTML)。`docs/guides/finance-risk.md` 是一篇指南。roadmap 里的「只读仪表板」「场景模板市场」都未开始。

Foundry 文档导航里的 Object Views 配置、Workshop、Quiver、Contour、Map、Slate、Marketplace,本仓库都没有应用运行时。Object View 只有上面那一个固定布局。

## 5. 相对 AIP 的缺口

`ontoforge.ai`(v1.1.0)是进程内注册表:

- `register_logic(name, fn, description=, params_schema=)`:蛇形名、不可重名、`params_schema` 的 type 只能是 `string | number | boolean | object | list`。
- `invoke_logic`:校验 required 与类型,异常收成 `{ok: false, error}`;函数若返回带 `ok` 的 dict 则原样透传。
- `list_logic`:只返回 `name`、`description`、**参数名列表**。类型、是否必填、描述都不在清单里。
- 注册表是模块全局 `_REGISTRY`,不在 state 里,`serialize` 带不走,进程重启即失。测试靠 `_reset_registry`。
- 函数拿到的是活的 state,可以随便改对象。这条路径不经 `run_action`,没有确认门槛,没有审计,也没有「只读」标记。

路线图上的三项都还没有落地,而且每一项都缺一块前置,而不是缺一个 LLM:

| 路线图项 | 现在缺的前置(仍可不接模型) |
|---|---|
| Agent 工具协议:把 actions / queries / logic 暴露成标准工具描述 | 动作和查询没有描述函数。`list_logic` 丢掉类型。没有稳定的 JSON 工具清单(名称、参数 schema、只读还是写入、是否要确认)。 |
| 自然语言 → 结构化本体查询 | 没有可翻译的目标。查询 API 是四个 Python 函数,不是过滤表达式。翻译层会无处落地。 |
| 多步 Logic 编排 | `invoke_logic` 是一次调用。没有链、没有中间态、没有步骤审计。 |
| (评估补上的)AI 动作治理 | `run_action` 的 `actor` 可写成任意字符串,包括「某个 agent」。没有允许列表、没有「logic 只能提议、人确认后才 `confirmed: true`」的绑定,也没有把 logic 调用写进 `audit`。`requireConfirm` 只在动作自己的定义上,调用方传 `confirmed: true` 就跳过。 |

AIP 产品面里同样不存在、且与「不绑定供应商」一致所以不应排进近期 PR 的:模型注册、评估、托管、embedding、Ontology Augmented Generation、Agent Studio UI。研究笔记把它们标为平台域,不是本仓库的半成品。

## 6. 优先级与接下来 2–3 个 PR

工作量用改动面表示,不用日历:**S** = 一个模块加测试;**M** = 跨 pipeline/文档/测试,仍不动工坊大改;**L** = 新进程或工坊双模式。风险指行为兼容与范围膨胀。

### P0 — 在现有非目标内,把已宣称的闭环补到「可被外部调用方依赖」

**PR 1(P0,S,风险低)— 工具清单,不接模型**

- 新增只读描述函数(建议 `describe_tools(state)`):从当前分支 schema 导出动作(id、name、targets、params 含类型与 required、`requireConfirm`、edits 的 op 列表),导出固定查询原语(`objects_of_type`、`search_objects`、`linked_objects`、`audit_for`)的参数形状,并导出 logic 的完整 `params_schema`(补上 `list_logic` 今天丢掉的类型)。
- 文档写明:可调用对象仍是进程内函数,不进 `serialize`。不要假装能把 Python callable 放进 JSON。
- 给 logic 增加 `effects: "read" | "write"`(默认 `write` 以保持诚实)。本 PR 可以只记录标记并在文档中要求写逻辑走 `run_action`;强制拦截放到 PR 3 有了进程边界再做。
- 测试镜像 `test_ai.py` 的风格。不改 `ontoforge.html`。
- 为什么先做:路线图已经把「工具协议」列为 AI 平面第一项;今天的骨架外部 agent 无法消费。

**PR 2(P0,M,风险低到中)— 血缘写全,upsert 语义写明**

- `pipelineRuns` 成功条目增加列级来源:每个对象块的 `property ← column ← transform`,每个链接块的 `fromColumn` / `toColumn` / `linkType`。只追加字段,旧读者可忽略。
- `_validate_mapping` 失败也追加一条 `failed` run(今天直接 return,运维上看不到这次尝试)。
- 在 counts 里报告「本类型已存在、本批未触及」的对象数,并在 `docs/pipeline.md` 写死默认同步模式是 **upsert**:不删除缺席主键,空单元格不清空。不要在这个 PR 里做增量或删除模式。
- 顺手把数值规则的 `float()` 包进 `{ok: false}`(动作契约漏洞,几行,与「可依赖」同一目标)。若不想混进 pipeline PR,就单独一个极小提交,仍属于这一档。
- 为什么第二:金融指南把 `pipelineRuns` 称为审计追溯,粒度却到不了列;这是 roadmap 已点名的列级血缘,而且不用引入依赖。

**PR 3(P1,但属于这三步的第三步;M 到 L 的下沿,风险中)— 服务端设计稿的窄切片**

不要按设计稿 §2 的「M1 全量一次到位」做。那一版同时包含全量 REST、调度、作业线程、UI 双模式和契约测试,设计稿 §13 自己把 UI 适配列为最大风险。

本 PR 只做:

- `pyproject` 可选 extra `server`(FastAPI、uvicorn、python-multipart),核心 `dependencies` 仍为空。
- SQLite 单文档 + `rev` 乐观锁,对应设计稿 §5 的写路径,先不做 `ops` 表以外的投影。
- 端点:`GET /api/v1/health`、`GET/POST` state 导入导出、`POST /api/v1/actions/{id}/run`、`POST /api/v1/pipelines/run`(同步即可,后台 job 可后置)、`GET /api/v1/logic`(直接返回 PR 1 的工具清单)、`POST /api/v1/logic/{name}/invoke`。
- 可选 `ONTOFORGE_TOKEN`。文档重复「这不是权限模型」。
- 引擎函数不改语义。工坊继续 file:// + localStorage,本 PR 不抽 `Backend` 接口。

做完这三步,外部调度器才能用 HTTP 触发 `run_pipeline`(roadmap 对调度的原话),agent 才能拉工具清单。再往下才有资格谈编排和自然语言。

### P1 — 三步之后,仍遵守非目标

| 项 | 工作量 / 风险 | 说明 |
|---|---|---|
| 提案合并检测 main 漂移 | S / 低 | `merge_proposal` 在覆盖前比较 `proposal` 创建后的 main `rev` 或重新 diff;冲突则拒绝并要求重新提案。单用户本地影响小,但是「治理」从展示变为真实约束的最小改动。 |
| 属性 `required` 在物化时生效;共享属性要么能被 mapping 引用,要么文档标明「仅元数据」 | S / 低 | 二选一,避免建模器上的勾选没有执行语义。建议先写进 `docs/pipeline.md` 与工坊提示,再决定是否执行。 |
| `keyMapping` 要么驱动链接物化的默认列,要么从「Datasources」文案改成「备注」 | S / 低 | 今天保存了但 pipeline 忽略,示例种子却填了 keyMapping,读代码的人会以为它参与解析。 |
| 外部调度的参考封装 | S / 低 | 一个脚本或文档化的 curl / HTTP 调用(依赖 PR 3)。不要先手写 cron 解析器;设计稿已说生产应用外部调度器。 |
| 增量物化 | M / 中 | watermark 列 + 血缘记下窗口。仍是批,仍零依赖。在列级血缘之后做,否则增量窗口无可审计。 |
| 查询过滤 AST | M / 中 | 例如按属性 eq/范围/枚举过滤的纯函数,返回对象列表。这是自然语言查询的落地类型。没有它就不要做翻译层。 |
| pipeline 与链接写入补审计或明确「非动作写入不进 audit」 | S / 低 | 现在两种说法都容易过度承诺。建议单独的 `pipelineRuns` 保持为数据追溯,`audit` 保持为动作追溯,在架构文档写清,而不是把 pipeline 硬塞进动作审计。 |

### P2 — 有意靠后

- Streaming 微批桥、JSONL / 数据库游标 / HTTP 数据源。
- 只读仪表板视图、行业模板包(Workshop 方向的第一级,仍然不是应用搭建器)。
- 多步 logic 链与中间态。前置是 PR 1 的工具清单和 PR 3 的进程。
- 自然语言到过滤 AST 的翻译层,模型由调用方注入,仓库不选供应商。
- AI 发起的 `run_action` 必须带人确认:logic `effects=write` 默认不得传 `confirmed: true`,或单独的提议对象。这是治理,不是模型。
- 工坊里的 pipeline 页(注册数据集、编辑 mapping、看血缘)。等 Python 语义在 PR 2 稳定后再移植,避免双实现同时改。
- 工坊拆 ES modules、i18n、更宽 E2E。与对等 Foundry 无关,保持在原 roadmap。
- 对象量上来之后的只读索引投影(设计稿 §5)。
- interface、function type、derived properties、scenarios、真实 webhook、写回源系统。

### 不要排进「对等」路线,除非先改非目标

- 多租户、角色、对象级权限、marking。
- 仓库内置某个 LLM、Agent Studio、自动 OAG。
- 把 2026-10-24 设计稿整包(全量 REST + cron + UI 双模式 + 契约测试)打成一个 PR。

## 7. 建议的阅读顺序

1. 本文 §2(边界)→ §6 的三个 PR。
2. [roadmap.md](roadmap.md) 看同一批事项的勾选状态。
3. [pipeline.md](pipeline.md) 看 v1 已经保证的语义;列级血缘与缺席行仍以该文和 `pipeline.py` 为准。
4. [superpowers/specs/2026-10-24-server-architecture-design.md](superpowers/specs/2026-10-24-server-architecture-design.md) 只作为 PR 3 的上限草稿,不是现状。
