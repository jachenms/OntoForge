# OntoForge

**The open-source ontology layer for the enterprise** — model your business as objects, links and actions; materialize data into the ontology with a declarative pipeline; operate it through guarded actions and branch governance. Inspired by Palantir Foundry's ontology-centric architecture ("run your business as code"), built from scratch with zero runtime dependencies.

> 中文摘要:OntoForge 是开源的企业本体层——对象/链接/动作建模 + 声明式数据物化管线 + 动作治理与分支协作,概念上对标 Foundry 的本体架构。浏览器直接打开 `ontoforge.html` 即可使用建模工坊;Python 包提供领域引擎与 pipeline;`npm test` 冒烟,`npm run test:e2e` 端到端,`cd python && python3 -m pytest` 跑 Python 测试。详见下文与 [文档索引](docs/README.md)。

```
数据源 (CSV / JSON / rows)
        │
        ▼
   Pipeline ───────────── 声明式映射 · 全量校验 · 原子物化 · 批次血缘
        │
        ▼
   Ontology ───────────── 对象类型 / 链接类型 / 共享属性(分支隔离 · 提案合并)
        │
        ▼
   Actions ────────────── 参数校验 · 规则闸门 · 确认预览 · 原子编辑 · 审计/通知
        │
        ▼
   AI (roadmap) ───────── Logic Function 协议骨架已预留(ontoforge.ai)
```

## Why OntoForge

Enterprise data only becomes operational when it is bound to a **semantic model of the business** — not tables, but the objects people actually work with, the links between them, and the actions that change them. OntoForge implements that loop end to end, in a form you can read in an afternoon:

- **Ontology Builder** — a zero-build, single-file workbench (`ontoforge.html`): object/link/action type modeling, object explorer, global search, notifications, branches with proposal diffs and merge. All state in `localStorage`; works offline from `file://`.
- **Ontology Pipeline** — a declarative batch engine (`ontoforge.pipeline`): register CSV/JSON/row sources as datasets, map columns to properties, validate everything, then atomically upsert objects and links by primary key — with batch-level lineage recorded on every run.
- **Domain engine as a library** — the same CORE that powers the workbench is a typed, zero-dependency Python package (`python/`), so your backend, notebook or agent can drive the exact same contract.

## Concept map

| Foundry concept | OntoForge counterpart | Status |
|---|---|---|
| Ontology Manager | `ontoforge.html` workbench + `ontoforge` Python engine | ✅ shipped |
| Actions (write-back, governance) | `run_action` engine: params → rules → confirm → atomic edits → audit | ✅ shipped |
| Branch / proposal workflow | schema branches, diff, merge proposals | ✅ shipped |
| Pipeline Builder (batch) | `ontoforge.pipeline`: declarative mapping, validation, upsert, lineage | ✅ shipped |
| AI Logic / Agents (AIP) | `ontoforge.ai` Logic Function registry (protocol skeleton, no LLM calls) | 🔩 skeleton |
| Workshop apps, streaming, scheduling | — | 🧭 [roadmap](docs/roadmap.md) |

## Quick start

### 1. The workbench (no install)

```bash
open ontoforge.html          # or double-click; file:// works fine
```

Load the built-in **traffic-emergency** seed (5 object types, 3 link types, 3 action types, 20 objects) from Settings, then explore: run a guarded `dispatch_team` action, create a branch, propose a schema change, merge it back.

### 2. The Python engine

```bash
cd python && pip install -e ".[dev]"   # or: PYTHONPATH=src python3
```

```python
import ontoforge as of

state = of.seed.traffic()
r = of.run_action(state, "dispatch_team",
                  {"team": team_id, "inc": inc_id}, {}, confirmed=True)
```

### 3. The pipeline (end to end)

```bash
python3 examples/traffic_pipeline.py
```

```python
of.register_dataset(state, "segments", "segments.csv")
of.run_pipeline(state, {
    "name": "daily_sync",
    "objects": [{"dataset": "segments", "objectType": "road_segment",
                 "key": "seg_id",
                 "properties": {"length_km": {"column": "km", "transform": "float"}}}],
    "links": [{"linkType": "inc_on_seg", "dataset": "incidents",
               "fromColumn": "inc_id", "toColumn": "seg_id"}],
})
# → atomic upsert by primary key + per-run lineage in state["pipelineRuns"]
```

Full mapping reference: [docs/pipeline.md](docs/pipeline.md). Industry walkthrough (financial risk-control): [docs/guides/finance-risk.md](docs/guides/finance-risk.md).

## Testing

```bash
npm test            # CORE smoke: 39 Node assertions
npm run test:e2e    # Playwright E2E: 21 assertions (needs npx playwright install chromium)
cd python && python3 -m pytest   # 46 tests: engine + pipeline + AI skeleton
```

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs all three suites plus a trademark red-line check on every push.

## Project layout

```
ontoforge.html       the workbench (CORE / SEED / UI sections, zero build)
smoke.mjs            CORE smoke tests
verify_ui.mjs        Playwright E2E
python/              typed, zero-dep Python package: engine + pipeline + AI skeleton
examples/            end-to-end pipeline example with sample CSV data
docs/
  architecture.md    the three planes and the state contract
  pipeline.md        pipeline mapping reference
  guides/            industry walkthroughs
  roadmap.md         what comes next (and what deliberately doesn't)
  research/          reverse-engineering notes behind the concept
  superpowers/       design specs and implementation plans
```

## Trademark note

OntoForge is an independent open-source project. "Palantir" and "Foundry" are referenced solely to attribute conceptual inspiration; no affiliation or endorsement is implied. The product file `ontoforge.html` contains no third-party trademarks (enforced in CI).

## License

[MIT](LICENSE) © 2026 OntoForge contributors
