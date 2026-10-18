# OntoForge Pipeline 参考手册

批量数据 → 声明式映射 → 全量校验 → 原子物化 → 批次血缘。

> 范围说明:v1 为**批量**引擎。增量列、cron 调度、streaming 见 [roadmap](roadmap.md),不在本版。

## API 一览

```python
import ontoforge as of

of.register_dataset(state, name, source)  # source: rows 列表 | .csv 路径 | .json 路径
of.delete_dataset(state, dataset_id)
of.list_datasets(state)                    # 不含行数据的元信息视图
of.run_pipeline(state, mapping, dry_run=False)
of.pipeline_runs(state, limit=20)          # 血缘,最新在后
```

## Dataset

`register_dataset` 把数据源**快照**进 `state["datasets"]`:

```json
{"__id": "ds_...", "name": "segments", "kind": "csv|json|rows",
 "sourceRef": "路径或 <memory>", "columns": [...], "rowCount": 3,
 "registeredAt": "...", "rows": [...]}
```

- CSV 一律读出为字符串列(用 transform 归一类型);JSON/rows 保留原生类型。
- name 蛇形、唯一;列集合为所有行键的并集(按出现顺序)。

## Mapping

```python
{
  "name": "daily_sync",            # 可选,进血缘
  "objects": [{                    # 对象物化块,可多个
    "dataset": "segments",         # dataset 的 id 或 name
    "objectType": "road_segment",  # 必须已存在且设了 primaryKey
    "key": "seg_id",               # 源列名;其值 ↔ 对象类型主键
    "properties": {                # 属性名 → 列名 或 {"column": c, "transform": t}
      "name": "seg_name",
      "length_km": {"column": "km", "transform": "float"},
    },
  }],
  "links": [{                      # 链接物化块:数据集的每一行 = 一条候选链接
    "linkType": "inc_on_seg",      # 按 name 引用;端点类型取自链接类型的 from/to
    "dataset": "incidents",
    "fromColumn": "inc_id",        # 列值 = from 端对象的主键值
    "toColumn": "seg_id",
  }],
}
```

### 内建 transform

| transform | 语义 |
|---|---|
| `str` | `js_str`(None→""、true/false 小写) |
| `int` | `int(float(x))`,容忍 `"3.0"` |
| `float` | `float(x)` |
| `bool` | true/false/1/0/yes/no(大小写不敏感) |
| `trim` | 去首尾空白 |

空单元格(缺失列值或空字符串)**跳过该属性**,不覆盖已有值;主键列空 → 行错误。

## 执行语义

1. **结构校验**:dataset/对象类型/属性/链接类型/列/transform 全部存在;对象类型必须已设 `primaryKey`。
2. **逐行校验**:主键非空、批内主键唯一、transform 可解析、baseType 与 enum 合法、链接端点可解析(既有对象 + 本批将建对象)、cardinality(既有链接 + 批内)不冲突。
3. **原子物化**:任一错误 → 不写任何对象/链接,返回 `{"ok": False, "error": 首条, "errors": [{row, message}, ...]}`;全部通过才落数据。
4. **upsert**:同类型同主键 → 更新 `props`(`__id` 稳定,未映射属性保留);否则新建。重复运行幂等(第二次 0 created / N updated)。
5. **链接**:按 `(linkType, fromId, toId)` 去重;已存在的边计入 `skipped`。

`dry_run=True` 只跑前两阶段,返回 `{"wouldCreate", "wouldUpdate", "wouldLink"}` 预览,不写 state、不记血缘。

## 血缘

每次运行(含失败)追加 `state["pipelineRuns"]`:

```json
{"__id": "run_...", "mapping": "daily_sync", "datasets": ["segments", "incidents"],
 "startedAt": "...", "finishedAt": "...", "status": "success",
 "counts": {"created": 5, "updated": 1, "linksCreated": 3, "skipped": 0},
 "objectIds": ["obj_..."]}
```

失败条目:`"status": "failed"`, `errors`(前 10 条), `errorCount`。
粒度为**批次级**:run → datasets → 产出对象 id 列表。列级血缘在 roadmap。

## 完整示例

见仓库 `examples/traffic_pipeline.py`(`python3 examples/traffic_pipeline.py` 直接可跑)。
