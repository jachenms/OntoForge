# OntoForge Roadmap

原则:本体闭环(建模 → 物化 → 运营)先行,每步都保持 zero-dep、单契约、可离线。

## Pipeline 平面

- [ ] **增量物化** — watermark/增量列,只处理变更行;血缘记录增量窗口
- [ ] **调度** — cron 式计划运行(外部调度器触发 `run_pipeline` 即可,仓库提供参考封装)
- [ ] **列级血缘** — 属性值 ← 源列 的细粒度追溯(当前为批次级)
- [ ] **更多数据源** — JSONL/数据库游标/HTTP 拉取
- [ ] **Streaming 接入** — 事件流 → 物化的微批桥

## Builder 平面

- [ ] 单文件拆分为 ES modules(`src/core` / `src/seed` / `src/ui`),保持免构建开发流
- [ ] pipeline 的 UI 化(工坊内注册数据集、编辑 mapping、查看血缘)
- [ ] 更宽的 E2E 覆盖(设置页边角、提案冲突)
- [ ] i18n 脚手架(UI 文案目前中文优先)

## AI 平面(AIP 方向)

- [x] Logic Function 协议骨架(`ontoforge.ai`,v1.1.0)
- [ ] Logic 编排:多步 Logic 链 + 中间态
- [ ] 自然语言查询 → 结构化本体查询的翻译层(接入方自备 LLM)
- [ ] Agent 工具协议:把 actions/queries/logic 暴露为标准工具描述

## 应用层(Workshop 方向)

- [ ] 只读仪表板视图(按对象类型聚合指标 + 链接图)
- [ ] 场景模板市场(finance-risk / traffic-emergency 之外的行业包)

## 明确不做

- 不引入运行时依赖;不绑定任何特定 LLM 供应商
- 不做多租户/权限体系(单文件原型的边界;有需求的企业可自行在其外层包)
