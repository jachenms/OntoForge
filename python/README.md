# ontoforge (Python)

Python port of the OntoForge **CORE + SEED** engine from `ontoforge.html` — the full domain layer with no UI and zero dependencies.

- **Same contract as the JS CORE**: every function takes the JSON-compatible `state` dict first and returns `{"ok": True, ...}` / `{"ok": False, "error": ...}`; error messages are identical (Chinese, matching the prototype's UI copy).
- **Modules**: `state` (serialization/validation) · `schema` (object types, properties, shared props) · `links` · `actions` (action types, template rendering, the `run_action` engine) · `queries` (search/audit/usage) · `branches` (branch isolation, schema diff, merge proposals) · `seed` (the traffic-emergency sample dataset) · `pipeline` (datasets → declarative mapping → atomic materialization + lineage) · `ai` (Logic Function registry — protocol skeleton for a future agent layer).

## Install & test

```bash
pip install -e ".[dev]"   # from this directory
pytest                    # 46 tests: engine + pipeline + AI skeleton
```

## Usage

```python
from ontoforge import seed, objects_of_type, run_action, schema_of

s = seed.traffic()                       # 5 types / 3 link types / 3 actions / 20 objects
dispatch = next(a for a in schema_of(s)["actionTypes"] if a["name"] == "dispatch_team")
idle = next(t for t in objects_of_type(s, "rescue_team") if t["props"]["status"] == "待命")
open_inc = next(i for i in objects_of_type(s, "incident") if i["props"]["status"] == "待处置")

r = run_action(s, dispatch["id"], {"params": {}, "targets": {"team": idle["__id"], "inc": open_inc["__id"]}})
assert r["needConfirm"]                  # guarded action asks for confirmation first
r = run_action(s, dispatch["id"], {"params": {}, "targets": {"team": idle["__id"], "inc": open_inc["__id"]}, "confirmed": True})
assert r["ok"]
```

State serializes to the exact same JSON envelope (`{"app": "ontoforge", "v": 1, "state": ...}`) the browser prototype exports, so files round-trip between the two implementations.

See the [repository root README](../README.md) for the whole project.
