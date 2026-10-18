# OntoForge 重定位 + Pipeline 引擎 v1 设计

日期:2026-10-18
状态:已获用户批准(ok)

## 背景

OntoForge 目前是单文件本体工坊原型(`ontoforge.html`,CORE/SEED/UI 三段)+ 同仓库 Python 移植包(`python/`,CORE+SEED 七模块,29 项 pytest)。本轮把项目重新定位为**企业全流程本体开源项目**:ontology builder + ontology pipeline,参考 `~/.hermes/skills/palantir-foundry` 与 `~/.hermes/skills/palantir-foundry-aip`(含金融风控指南)。

### 已确认的决策(AskUserQuestion,2026-10-18)

1. 交付实质:**文档重构 + pipeline 引擎 v1**(不做 monorepo 大重构,不做"仅文档")。
2. Pipeline v1 范围:**批量物化 + 血缘**;增量/调度/streaming 进 roadmap。
3. 商标策略:**README/文档可提 "Palantir Foundry" 作为灵感参照**(nominative fair use);`ontoforge.html` 内部零字样红线与 CI 检查保持不动。
4. AIP 层:**预留接口骨架**(Logic Function 注册表),不接真实 LLM。

## 定位叙事

README 一句话:

> OntoForge — the open-source ontology layer for the enterprise: build, materialize and operate a full-lifecycle ontology. Inspired by Palantir Foundry's ontology-centric architecture.

数据流:

```
数据源(CSV/JSON) → Pipeline(声明式映射·校验·物化) → Ontology(对象/链接) → Actions(业务操作) → AI(roadmap)
```

README 内置「概念对照表」,诚实标注现状:

| Foundry 概念 | OntoForge 对应 | 状态 |
|---|---|---|
| Ontology Manager | `ontoforge.html` workbench + Python 引擎 | 已有 |
| Actions / 分支治理 | runAction 引擎 / branches+proposals | 已有 |
| Pipeline Builder | `ontoforge.pipeline`(批量物化+血缘) | 本轮新增 |
| Workshop / AIP / Streaming / 调度 | — | roadmap |

## Pipeline 引擎 v1(`python/src/ontoforge/pipeline.py`)

### 概念

- **Dataset**:注册进 `state["datasets"]` 的数据源快照 `{__id, name, kind: "csv"|"json"|"rows", sourceRef, rowCount, columns, registeredAt}`。
- **Mapping**:声明式 dict(不落库,作为 `run_pipeline` 入参;调用方自行管理/版本化):
  ```python
  {
    "name": "traffic_segments",
    "objects": [{
      "dataset": "<dataset_id 或 name>",
      "objectType": "road_segment",
      "key": "seg_id",                       # 源列名,映射到对象类型主键
      "properties": {                         # 属性名 → 列名 或 {"column": c, "transform": t}
        "name": "seg_name",
        "length_km": {"column": "km", "transform": "float"},
      },
    }],
    "links": [{
      "linkType": "inc_on_seg",
      "from": {"dataset": "incidents", "key": "inc_id"},
      "to":   {"dataset": "segments",  "key": "seg_id"},
    }],
  }
  ```
- 内建 transform:`str` / `int` / `float` / `bool` / `trim`(对 CSV 全字符串输入做类型归一);date 列原样保留字符串(与 baseType date 的 ISO 字符串约定一致)。

### 执行语义

- **两阶段、原子**:先对全部行做校验(列存在、主键非空、批内主键去重、transform 可解析、对象类型/属性/链接类型存在、enum 值合法、链接端点可解析);任一错误 → 不写任何对象/链接,返回 `{"ok": False, "error": 首条, "errors": [{row, message}...]}`。
- **物化**:upsert by primaryKey —— `state["data"]["objects"]` 中同类型、主键属性值相同者更新 `props`(对象 `__id` 稳定),否则新建 `{"__id", "__type", "props"}`。链接按 (linkType, fromId, toId) 去重建边,遵守 cardinality 约束(违反即校验期报错)。
- **血缘**:每次成功运行追加 `state["pipelineRuns"]` 一条 `{__id, mapping, datasets:[...], startedAt, finishedAt, counts:{created, updated, linksCreated, skipped}, objectIds:[...]}`;失败运行也记录(status:"failed" + errors 摘要)。血缘为批次级:run → datasets → 产出的对象 id 列表。
- **契约不变**:state dict 首参;`{"ok"/"error"}` 结果;中文错误文案;uid 复用 `_common.uid`。

### API

```python
register_dataset(state, name, source) -> Result   # source: csv路径 | json路径 | list[dict]
run_pipeline(state, mapping, *, dry_run=False)    -> Result  # counts + runId
list_datasets(state) -> list
pipeline_runs(state, limit=20) -> list
```

`dry_run=True` 只跑校验阶段并返回预览 counts(不写 state,不记血缘)。

## AI 接口骨架(`python/src/ontoforge/ai.py`)

Logic Function 注册表,为未来 AIP Logic/Agent 层预留协议:

```python
register_logic(name, fn, *, description="", params_schema=None) -> Result
invoke_logic(state, name, params=None) -> Result    # fn(state, params) -> dict
list_logic() -> list[{name, description}]
```

- 与领域函数同契约:`fn` 收 state 首参、返回 JSON 兼容 dict;invoke 包装异常为 `{"ok": False, "error": ...}`。
- 注册表为进程内模块级(不进 state),零 LLM 调用;docstring 注明 roadmap(AIP Logic Studio / Agents)。

## 文档与资源包

- **README.md** 重写:新定位、架构图(ASCII)、三个 quickstart(workbench / Python 引擎 / pipeline 端到端)、概念对照表、roadmap 指引;中文摘要保留。
- **docs/architecture.md** — 三平面(Builder / Pipeline / AI)+ state 契约 + 红线说明。
- **docs/pipeline.md** — 映射规范参考:dataset 注册、字段级 mapping 说明、transform 表、错误模型、血缘结构、dry_run。
- **docs/guides/finance-risk.md** — 将 FINANCE_RISK_GUIDE 改写为 OntoForge 实战:Customer/Account/Transaction/Device 建模 + CSV pipeline 映射 + 反欺诈 action;不含任何 Foundry 专有内容照搬。
- **docs/roadmap.md** — 分层:pipeline 增量/调度/streaming;Workshop 式应用层;AIP(Logic 已留骨架、Assist、Agents);HTML 模块化拆分。
- **examples/traffic_pipeline.py + examples/data/{segments,incidents}.csv** — 端到端可跑示例:seed 建 schema → 注册 CSV → mapping → run → 打印 counts 与血缘。
- docs/README.md 索引、CHANGELOG(python 1.1.0)同步。

## 测试

新增 `python/tests/test_pipeline.py`(约 12 项)与 `test_ai.py`(约 3 项):

- dataset 注册(csv/json/rows、列推断、重名)
- mapping 校验(对象类型不存在、属性不存在、主键列缺失、transform 失败、enum 非法、批内主键重复)
- 原子失败(任一行错 → state 零变化)
- upsert 幂等(二次运行 0 created / N updated,id 稳定)
- 链接物化(端点解析、去重、cardinality 违例)
- dry_run 不写 state
- 血缘记录(成功/失败 run 条目、counts、objectIds)
- AI:register/invoke/list、异常包装

质量门回归:`node smoke.mjs`(39)、`node verify_ui.mjs`(21)、`cd python && python3 -m pytest`(29+新增)、`grep -ci palantir ontoforge.html` = 0。

## 明确不做(YAGNI)

- 不动 `ontoforge.html` UI(pipeline 无界面,仅 Python API + 文档)
- 不做增量列/调度/streaming
- 不接真实 LLM
- 不拆 monorepo、不引入运行时依赖(保持 zero-dep)
