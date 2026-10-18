# OntoForge 架构

OntoForge 由三个平面组成,共享同一份 JSON 兼容的 state 契约。

```
┌─────────────────────────────────────────────────────────────┐
│ Builder 平面        Pipeline 平面          AI 平面(骨架)    │
│ ontoforge.html      ontoforge.pipeline     ontoforge.ai     │
│ workbench + CORE    批量物化引擎           Logic 注册表      │
├─────────────────────────────────────────────────────────────┤
│                 同一份 state dict(JSON 兼容)                │
│ schemas / data / audit / notices / datasets / pipelineRuns  │
└─────────────────────────────────────────────────────────────┘
```

## Builder 平面

- **`ontoforge.html`** — 零构建单文件工坊,内含三段脚本:`CORE`(纯领域逻辑,无 DOM)、`SEED`(数据集)、UI。浏览器 `file://` 直开,状态落 `localStorage`。
- **`python/src/ontoforge/`(引擎模块)** — CORE+SEED 的逐函数 Python 移植,同一契约:state dict 首参、`{"ok"/"error"}` 结果、相同中文错误文案。

## Pipeline 平面

`pipeline.py`:数据源(CSV/JSON/rows)注册为 `state["datasets"]` 快照 → 声明式 mapping(列→属性/链接)→ 两阶段执行(全量校验 → 原子物化)→ 批次血缘写入 `state["pipelineRuns"]`。详见 [pipeline.md](pipeline.md)。

## AI 平面(骨架)

`ai.py`:Logic Function 注册表(`register_logic` / `invoke_logic` / `list_logic`),为未来的 Agent/编排层预留协议。零 LLM 调用。

## State 契约

- 一切函数第一参数为 state(JSON 兼容 dict),直接原地修改;返回 `{"ok": True, ...}` / `{"ok": False, "error": ...}`。
- 顶层键:`v / meta / branch / schemas / proposals / data / audit / notices / ui`,pipeline 附加 `datasets` 与 `pipelineRuns`(用 `setdefault` 写入,旧版导出文件无此二键也能工作)。
- schema 按分支隔离(`schemas[branch.current]`);实例数据(data.objects/links)全局共享。
- 序列化信封:`{"app": "ontoforge", "v": 1, "state": ...}`。
- id 形态:`<prefix>_<毫秒36进制>_<序号36><随机4位>`(`uid()`)。

## 红线

- `ontoforge.html` 内不得出现第三方商标字样(smoke S8.2 + CI `grep -ci` 强制为 0)。灵感归属声明只出现在 README/docs。
- 两个实现(JS CORE / Python 包)共用同一行为契约;改一边必须同步另一边并保持测试镜像。
