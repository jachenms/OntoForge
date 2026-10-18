#!/usr/bin/env python3
"""端到端示例:CSV 数据源 → 声明式映射 → 物化进本体 → 血缘。

跑法(免安装,仓库根目录或 python/ 下均可):
    PYTHONPATH=python/src python3 examples/traffic_pipeline.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python", "src"))

import ontoforge as of  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "data")


def main() -> None:
    # 1. 从种子本体开始:5 对象类型 / 3 链接类型 / 20 实例(schema 即"本体模型")
    state = of.seed.traffic()
    print(f"本体:{state['meta']['ontologyName']},既有对象 {len(state['data']['objects'])} 个")

    # 2. 注册两个 CSV 数据源(快照进 state,列结构自动推断)
    of.register_dataset(state, "segments", os.path.join(DATA, "segments.csv"))
    of.register_dataset(state, "incidents", os.path.join(DATA, "incidents.csv"))
    for d in of.list_datasets(state):
        print(f"数据集 {d['name']}: {d['rowCount']} 行,列 {d['columns']}")

    # 3. 声明式映射:列 → 属性,主键 upsert;事件按行建"发生于"链接
    mapping = {
        "name": "daily_traffic_sync",
        "objects": [
            {"dataset": "segments", "objectType": "road_segment", "key": "seg_id",
             "properties": {"name": "seg_name",
                            "length_km": {"column": "km", "transform": "float"},
                            "status": "seg_status"}},
            {"dataset": "incidents", "objectType": "incident", "key": "inc_id",
             "properties": {"title": "title", "type": "inc_type", "severity": "severity"}},
        ],
        "links": [
            {"linkType": "inc_on_seg", "dataset": "incidents",
             "fromColumn": "inc_id", "toColumn": "seg_id"},
        ],
    }

    # 4. dry-run 预览,再正式物化
    preview = of.run_pipeline(state, mapping, dry_run=True)
    print(f"dry-run 预览: {preview['counts']}")
    r = of.run_pipeline(state, mapping)
    assert r["ok"], r.get("error")
    print(f"物化完成: {r['counts']}")

    # 5. 血缘:每次运行的批次级记录
    for run in of.pipeline_runs(state):
        print(f"血缘 run {run['__id']}: {run['mapping']} [{run['status']}] "
              f"{run.get('counts', run.get('errorCount'))} ← {run['datasets']}")

    # 6. 物化结果即可被 CORE 查询/动作层使用
    inc = next(o for o in of.objects_of_type(state, "incident")
               if o["props"].get("inc_id") == "INC-2001")
    linked = of.linked_objects(state, inc["__id"])
    seg = next(x["object"] for x in linked if x["linkType"]["name"] == "inc_on_seg")
    print(f"INC-2001 发生于 → {seg['props']['name']}({seg['props']['status']})")


if __name__ == "__main__":
    main()
