"""Pipeline 引擎 v1 测试:dataset 注册 / 映射校验 / 原子失败 / upsert / 链接物化 / 血缘 / dry_run。

镜像 spec 2026-10-18-pipeline-repositioning-design.md 的语义;schema 复用 seed.traffic()。
"""
import json

import ontoforge as of


def _world():
    """seed 世界 + 两个 rows 数据集:segments(含 1 条既有 SEG-001 + 1 条新 SEG-100)、incidents。"""
    s = of.seed.traffic()
    seg_rows = [
        {"seg_id": "SEG-001", "seg_name": "成渝立交段(改)", "km": "13.0", "seg_status": "缓行"},
        {"seg_id": "SEG-100", "seg_name": "新开通试验段", "km": "2.5", "seg_status": "畅通"},
    ]
    inc_rows = [
        {"inc_id": "INC-2001", "title": "新事故一", "seg_id": "SEG-001"},
        {"inc_id": "INC-2002", "title": "新事故二", "seg_id": "SEG-100"},
    ]
    assert of.register_dataset(s, "segments", seg_rows)["ok"]
    assert of.register_dataset(s, "incidents", inc_rows)["ok"]
    return s


def _seg_mapping(**over):
    m = {
        "name": "seg_sync",
        "objects": [{
            "dataset": "segments", "objectType": "road_segment", "key": "seg_id",
            "properties": {
                "name": "seg_name",
                "length_km": {"column": "km", "transform": "float"},
                "status": "seg_status",
            },
        }],
    }
    m.update(over)
    return m


# ---------- dataset 注册 ----------

def test_register_rows_and_list():
    s = of.seed.blank()
    r = of.register_dataset(s, "d1", [{"a": "1", "b": "x"}, {"a": "2", "c": "y"}])
    assert r["ok"]
    lst = of.list_datasets(s)
    assert len(lst) == 1 and lst[0]["name"] == "d1"
    assert lst[0]["rowCount"] == 2 and lst[0]["columns"] == ["a", "b", "c"]
    assert "rows" not in lst[0]  # 列表视图不带行数据


def test_register_csv_and_json(tmp_path):
    s = of.seed.blank()
    csv_p = tmp_path / "d.csv"
    csv_p.write_text("a,b\n1,x\n2,y\n", encoding="utf-8")
    r = of.register_dataset(s, "from_csv", str(csv_p))
    assert r["ok"] and s["datasets"][r["id"]]["rowCount"] == 2
    json_p = tmp_path / "d.json"
    json_p.write_text(json.dumps([{"a": 1}]), encoding="utf-8")
    r2 = of.register_dataset(s, "from_json", str(json_p))
    assert r2["ok"] and s["datasets"][r2["id"]]["kind"] == "json"


def test_register_rejects_dup_and_bad_source():
    s = of.seed.blank()
    assert of.register_dataset(s, "d1", [])["ok"]
    assert not of.register_dataset(s, "d1", [])["ok"]
    assert of.register_dataset(s, "d2", [])["ok"]  # 不同名可注册
    assert not of.register_dataset(s, "d3", "/nonexistent/x.csv")["ok"]
    assert not of.register_dataset(s, "bad name!", [])["ok"]


# ---------- 物化 ----------

def test_run_upsert_counts_and_stable_ids():
    s = _world()
    before = {o["__id"] for o in s["data"]["objects"]}
    r = of.run_pipeline(s, _seg_mapping())
    assert r["ok"], r.get("error")
    assert r["counts"] == {"created": 1, "updated": 1, "linksCreated": 0, "skipped": 0}
    seg1 = next(o for o in s["data"]["objects"] if o["props"].get("seg_id") == "SEG-001")
    assert seg1["__id"] in before  # upsert 保持 __id 稳定
    assert seg1["props"]["name"] == "成渝立交段(改)"
    assert seg1["props"]["length_km"] == 13.0  # float transform 生效
    new = next(o for o in s["data"]["objects"] if o["props"].get("seg_id") == "SEG-100")
    assert new["props"]["status"] == "畅通"


def test_run_idempotent_second_time():
    s = _world()
    of.run_pipeline(s, _seg_mapping())
    r2 = of.run_pipeline(s, _seg_mapping())
    assert r2["ok"] and r2["counts"]["created"] == 0 and r2["counts"]["updated"] == 2
    assert len(of.objects_of_type(s, "road_segment")) == 6  # 5 既有 + 1 新增


def test_run_with_links_materialized_and_deduped():
    s = _world()
    m = _seg_mapping()
    m["objects"].append({
        "dataset": "incidents", "objectType": "incident", "key": "inc_id",
        "properties": {"title": "title"},
    })
    m["links"] = [{"linkType": "inc_on_seg", "dataset": "incidents",
                   "fromColumn": "inc_id", "toColumn": "seg_id"}]
    r = of.run_pipeline(s, m)
    assert r["ok"], r.get("error")
    assert r["counts"]["created"] == 3 and r["counts"]["linksCreated"] == 2
    lt = next(l for l in of.schema_of(s)["linkTypes"] if l["name"] == "inc_on_seg")
    links = of.links_of(s, lt["id"])
    assert len(links) == 5 + 2  # seed 5 条 + 新 2 条
    # 再跑一次:链接全部 skipped,不重复建边
    r2 = of.run_pipeline(s, m)
    assert r2["ok"] and r2["counts"]["linksCreated"] == 0 and r2["counts"]["skipped"] == 2
    assert len(of.links_of(s, lt["id"])) == 7


def test_link_endpoint_unresolvable_fails_atomically():
    s = _world()
    m = _seg_mapping()
    m["links"] = [{"linkType": "inc_on_seg", "dataset": "incidents",
                   "fromColumn": "inc_id", "toColumn": "seg_id"}]
    # incidents 没作为 objects 块物化,inc 端点解析不到 → 整个运行失败,零写入
    n_obj, n_links = len(s["data"]["objects"]), len(s["data"]["links"])
    r = of.run_pipeline(s, m)
    assert not r["ok"] and "无法解析" in r["error"]
    assert len(s["data"]["objects"]) == n_obj and len(s["data"]["links"]) == n_links
    runs = of.pipeline_runs(s)
    assert runs and runs[-1]["status"] == "failed" and runs[-1]["errorCount"] >= 1


def test_row_level_validation_atomic_failure():
    s = _world()
    rows = [
        {"seg_id": "SEG-200", "seg_name": "好行", "km": "1.0", "seg_status": "畅通"},
        {"seg_id": "SEG-201", "seg_name": "坏行", "km": "abc", "seg_status": "畅通"},
    ]
    assert of.register_dataset(s, "bad_segments", rows)["ok"]
    m = _seg_mapping()
    m["objects"][0]["dataset"] = "bad_segments"
    n = len(s["data"]["objects"])
    r = of.run_pipeline(s, m)
    assert not r["ok"] and "transform 失败" in r["error"]
    assert r["errors"][0]["row"] == 1
    assert len(s["data"]["objects"]) == n  # 原子:一行坏,全部不写


def test_enum_and_pk_validation():
    s = _world()
    rows = [
        {"seg_id": "", "seg_name": "空主键", "km": "1", "seg_status": "畅通"},
        {"seg_id": "SEG-300", "seg_name": "非法枚举", "km": "1", "seg_status": "起飞"},
    ]
    assert of.register_dataset(s, "bad2", rows)["ok"]
    m = _seg_mapping()
    m["objects"][0]["dataset"] = "bad2"
    r = of.run_pipeline(s, m)
    assert not r["ok"]
    msgs = " ".join(e["message"] for e in r["errors"])
    assert "主键列为空" in msgs and "非法枚举值" in msgs


def test_batch_pk_duplicate_rejected():
    s = _world()
    rows = [{"seg_id": "SEG-9", "seg_name": "a", "km": "1", "seg_status": "畅通"},
            {"seg_id": "SEG-9", "seg_name": "b", "km": "2", "seg_status": "畅通"}]
    assert of.register_dataset(s, "dup", rows)["ok"]
    m = _seg_mapping()
    m["objects"][0]["dataset"] = "dup"
    r = of.run_pipeline(s, m)
    assert not r["ok"] and "批内主键重复" in r["error"]


def test_mapping_structure_errors():
    s = _world()
    assert not of.run_pipeline(s, {})["ok"]
    m = _seg_mapping()
    m["objects"][0]["objectType"] = "nope"
    assert "对象类型不存在" in of.run_pipeline(s, m)["error"]
    m = _seg_mapping()
    m["objects"][0]["properties"]["nope_prop"] = "seg_name"
    assert "属性不存在" in of.run_pipeline(s, m)["error"]
    m = _seg_mapping()
    m["links"] = [{"linkType": "nope_lt", "dataset": "incidents",
                   "fromColumn": "inc_id", "toColumn": "seg_id"}]
    assert "链接类型不存在" in of.run_pipeline(s, m)["error"]


def test_cardinality_conflict_within_batch():
    s = _world()
    # veh_belongs N:1(vehicle→rescue_team):同一辆车批内配给两支队 → 冲突
    rows = [{"veh_id": "VH-09", "team_id": "TM-01"},
            {"veh_id": "VH-09", "team_id": "TM-02"}]
    assert of.register_dataset(s, "veh_assign", rows)["ok"]
    veh_rows = [{"veh_id": "VH-09", "plate": "渝X·TEST", "kind": "巡逻车", "status": "可用"}]
    assert of.register_dataset(s, "vehicles", veh_rows)["ok"]
    m = {"name": "veh",
         "objects": [{"dataset": "vehicles", "objectType": "vehicle", "key": "veh_id",
                      "properties": {"plate": "plate", "kind": "kind", "status": "status"}}],
         "links": [{"linkType": "veh_belongs", "dataset": "veh_assign",
                    "fromColumn": "veh_id", "toColumn": "team_id"}]}
    r = of.run_pipeline(s, m)
    assert not r["ok"] and "基数约束" in r["error"]


def test_dry_run_writes_nothing():
    s = _world()
    n_obj = len(s["data"]["objects"])
    r = of.run_pipeline(s, _seg_mapping(), dry_run=True)
    assert r["ok"] and r["dryRun"]
    assert r["counts"] == {"wouldCreate": 1, "wouldUpdate": 1, "wouldLink": 0}
    assert len(s["data"]["objects"]) == n_obj
    assert of.pipeline_runs(s) == []  # dry_run 不记血缘


def test_lineage_recorded():
    s = _world()
    r = of.run_pipeline(s, _seg_mapping())
    runs = of.pipeline_runs(s)
    assert len(runs) == 1 and runs[0]["__id"] == r["runId"]
    assert runs[0]["status"] == "success" and runs[0]["mapping"] == "seg_sync"
    assert runs[0]["datasets"] == ["segments"]
    assert runs[0]["counts"]["created"] == 1
    assert len(runs[0]["objectIds"]) == 2
