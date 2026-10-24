# OntoForge 服务端架构设计(v2.0.0)

日期:2026-10-24
状态:已与用户逐节确认(形态/技术策略/范围/权限/UI 策略/架构选型)

## 1. 目标与定位

把 OntoForge 从「单文件原型 + Python 库」升级为**可部署的服务端产品**:开源的 Palantir Foundry 式企业本体系统。一次到位覆盖:REST API 全量(ontology/actions/queries/branches/pipeline/AI logic)、SQLite 持久化、轻量 token 认证、UI 双模式、调度、Docker 交付。

边界(明确不做):用户表/角色/对象级权限、多租户;不绑定 LLM 供应商。

## 2. 已确认的决策

| 决策点 | 结论 |
|---|---|
| 产品形态 | 升级为服务端架构(可部署产品) |
| 技术策略 | 允许服务端依赖:FastAPI + SQLite(可切 Postgres 留接口) + pytest;核心引擎保持 zero-dep,server 为可选 extra |
| M1 范围 | 全量一次到位:ontology/actions/branches/pipeline/调度/AI logic/UI 改造 |
| 权限模型 | 轻量 token:`ONTOFORGE_TOKEN` 环境变量,未设则开放 |
| UI 演进 | 双模式适配:服务端托管走 REST,file:// 走 JS CORE + localStorage |
| 总体架构 | 方案 A:状态文档服务(FastAPI 包纯函数引擎 + SQLite 状态文档 + rev 乐观锁) |

## 3. 总体架构

新增 `python/src/ontoforge/server/` 子包,**引擎现有代码零改动**:

```
ontoforge.html ──┐ (file:// 离线: JS CORE + localStorage)
                 │ (由服务端托管: REST adapter)
浏览器 UI ───────┤
                 ▼
FastAPI app ──── server/app.py        (路由、OpenAPI、静态托管 ontoforge.html)
   ├─ server/auth.py                  (可选 Bearer token 中间件)
   ├─ server/store.py                 (SQLite 状态文档 + rev 乐观锁 + ops 日志)
   ├─ server/jobs.py                  (pipeline 运行器: 后台线程 + 任务状态)
   └─ server/scheduler.py             (cron 式计划, 触发 run_pipeline)
                 ▼
ontoforge 引擎 (state.py/actions.py/schema.py/... 现有代码, 不改)
```

数据流:每个 API 写请求 = 进程内锁串行化 → 加载 state → 调引擎函数 → 原子写回(rev+1,记 ops 日志)。

## 4. REST API 面

前缀 `/api/v1`,动词与引擎函数一一对应:

| 资源 | 端点 | 引擎映射 |
|---|---|---|
| state | `GET /api/v1/state`、`GET /api/v1/state/export`、`POST /api/v1/state/import` | `serialize` / `validate_state` |
| schema | `POST /api/v1/schema/{objectTypes,linkTypes,actionTypes,sharedProps}`、`PUT/DELETE .../{name}` | schema.py 各函数 |
| branches | `POST /api/v1/branches`、`POST /api/v1/branches/{name}/checkout`、`/proposals`、`/proposals/{id}/merge` | branches.py |
| objects/links | `GET /api/v1/objects?type=&q=`、`GET /api/v1/objects/{id}`、`GET /api/v1/links` | queries.py |
| actions | `POST /api/v1/actions/{name}/run`(`confirmed:false` 返回预览,`true` 提交) | `run_action` |
| pipeline | `POST /api/v1/datasets`(multipart 上传)、`POST /api/v1/pipelines/run`、`GET /api/v1/jobs/{id}`、`GET /api/v1/pipelines/runs` | pipeline.py |
| ai | `GET /api/v1/logic`、`POST /api/v1/logic/{name}/invoke` | ai.py |
| schedules | `PUT /api/v1/schedules`、`DELETE /api/v1/schedules/{name}` | scheduler.py |
| 系统 | `GET /api/v1/health`、`GET /api/v1/notices` | — |

**错误契约**:统一 `{ ok: false, error: { code, message, details } }`;HTTP 状态码语义化(400 校验、401 未认证、404 资源、409 rev 冲突、422 规则闸门拒绝)。

## 5. 持久化与并发(store.py)

SQLite,单本体实例 per 部署(如 Foundry 每个 enrollment 一个本体):

- `ontology_state(id=1, rev INTEGER, state TEXT)` — 整文档 JSON,rev 单调递增
- `ops(rev, ts, actor, verb, summary)` — 每次变更的审计日志(通知/历史的数据源)
- `jobs(id, kind, status, payload, result, ts)` — pipeline 后台任务

写路径:进程内 `threading.Lock` 串行化 → `BEGIN IMMEDIATE` → 引擎函数 → `UPDATE ... WHERE rev=?`。客户端写请求可带 `If-Rev: n` 头;不匹配返回 `409`(响应带最新 rev)。UI 启动 `GET /state` 拿 rev,之后每次写带回。

演进路径:对象量超十万级时,在 state 文档旁加只读索引投影表,不改契约。

## 6. Pipeline 服务端化(jobs.py)

- 数据集上传:`POST /api/v1/datasets` multipart,落盘 `data/datasets/{id}.csv`,路径注册进 state;引擎的 `_rows_from_source` 新增「文件路径」source 形态(约 3 行分支,不改契约)。
- 运行模式:`dry_run: true` 同步返回校验/预览报告(不落库);正式运行进后台线程,返回 `jobId`,UI 轮询 `GET /api/v1/jobs/{id}`(`queued → running → done/failed`,result 含血缘批次号)。
- 并发约束:同一时间至多一个正式运行(与 state 写锁天然一致),其余排队。
- 血缘:沿用批次级;`GET /api/v1/pipelines/runs` 列表 + 单批次详情。

## 7. 调度(scheduler.py)

- 自实现轻量调度:后台线程每分钟扫描 state 中 `schedules` 列表(`{name, cron, mapping, enabled, lastRunAt}`);手写 5 字段 cron 子集解析(`*/n`、数字、`,`、`-`),不引第三方调度库。
- 文档明确:生产建议外部调度器(k8s cronjob/systemd timer)直调 `POST /api/v1/pipelines/run`;内置调度仅为单机便利。

## 8. AI Logic 服务端化

- `GET /api/v1/logic` 返回注册表(名称、参数 schema、描述)——即 Agent 工具协议 v0,LLM 接入方直接消费。
- `POST /api/v1/logic/{name}/invoke` 走引擎 `invoke_logic`,参数校验失败 400。
- 多步 Logic 编排不在本期,OpenAPI 中预留路径形态。

## 9. UI 双模式适配(ontoforge.html)

- 抽象 `Backend` 接口(约 20 方法:`loadState / runAction / saveObjectType / ...`),两实现:
  - `LocalBackend`:现有 JS CORE + localStorage 原样收编,file:// 自动启用。
  - `RemoteBackend`:`fetch` 调 `/api/v1/*`,带 `If-Rev`;409 时重新加载 state 并提示(操作重放为后续增强项)。
- 启动探测:`file:` 协议 → Local;否则 `GET /api/v1/health` 通 → Remote,不通 → Local 且设置页提示「离线模式」。
- 设置页新增连接状态指示 + 手动切换;导入/导出两种模式均可(Remote 走 `/state/export|import`)。
- 所有写路径收敛到 Backend 方法(收编散落的 localStorage 直写点)——这是 UI 改造的主要工作量。
- token 输入:Remote 收到 401 弹出一次性输入框,存 `sessionStorage`。

## 10. 认证(auth.py)

- `ONTOFORGE_TOKEN` 未设置 → 开放(本地/内网默认);设置后除 `GET /api/v1/health` 与静态文件外全部要求 `Authorization: Bearer <token>`。
- 不做用户表/角色/对象级权限;README 写明边界,企业需求可在反向代理层实现。

## 11. 测试与契约保障(三级,全进 CI)

1. **API 测试**(`python/tests/test_server.py`,FastAPI `TestClient`):每端点正常/校验错误/409 路径,目标 ~40 项;复用现有引擎测试 fixture。
2. **契约一致性**(`tests/contract/`):语言无关 JSON 用例(操作序列 + 期望结果摘要),Python 引擎与 JS CORE(node 跑抽出的 CORE,沿用 smoke.mjs 机制)各跑一遍,输出逐字节一致——保证双模式行为不漂移。
3. **E2E**(playwright,hermes 1.62.1 + chromium-1234):起 `ontoforge serve`,Remote 模式跑通核心路径(加载 seed、跑 action、建分支合并、上传 CSV 跑 pipeline)。

## 12. 交付与部署

- `pyproject.toml`:`[project.optional-dependencies] server = ["fastapi", "uvicorn", "python-multipart"]`;CLI `ontoforge serve --host 0.0.0.0 --port 8000 --data ./data`。
- `Dockerfile`(`python:3.12-slim`,volume `/data`)+ `docker-compose.yml` 便利示例。
- 数据目录:`--data` 指定,含 `ontoforge.db` + `datasets/`,整个实例可打包拷走。
- 版本 v2.0.0;CHANGELOG 记录「zero-dep 边界:核心引擎零依赖不变,server 为可选 extra」。
- 文档:`docs/server.md`(部署/认证/API),README 概念图更新,`docs/roadmap.md` 勾对应项并新增「对象量索引投影」「操作重放」等后续项。

## 13. 风险与缓解

1. UI 适配层触碰面大 → 契约测试兜底;先抽 Local 接口跑通现有 smoke,再接 Remote。
2. 单写锁吞吐上限 → 文档写明团队级单实例定位;给出压测基线。
3. 手写 cron 子集 → 只支持常用 5 字段,解析器测试覆盖。
