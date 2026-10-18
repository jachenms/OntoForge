"""OntoForge 领域核心 —— ontoforge.html `<script id="core">` + `<script id="seed">` 的 Python 移植。

与 JS CORE 保持同一契约:函数第一参数为 state(JSON 兼容 dict),返回
`{"ok": True, ...}` / `{"ok": False, "error": ...}` 结果字典;错误文案一致。
"""
from ._common import (BASE_TYPES, CARDINALITIES, EDIT_OPS, RULE_OPS, clone, uid)
from .state import (create_empty_state, deserialize, schema_of, serialize, validate_state)
from .schema import (add_object_type, add_property, add_shared_prop, attach_shared_prop,
                     delete_object_type, delete_property, delete_shared_prop, detach_shared_prop,
                     update_object_type, update_property)
from .links import (add_link_type, create_link, delete_link, delete_link_type, links_of,
                    update_link_type)
from .actions import (add_action_type, delete_action_type, describe_edits, render_template,
                      run_action, update_action_type)
from .queries import (audit_for, linked_objects, mark_notices_read, object_label,
                      objects_of_type, search_objects, unread_notices, usage_by_day)
from .branches import (create_branch, diff_empty, diff_schemas, merge_proposal, propose_merge,
                       reject_proposal, switch_branch)
from .pipeline import (delete_dataset, list_datasets, pipeline_runs, register_dataset,
                       run_pipeline)
from .ai import invoke_logic, list_logic, register_logic
from . import seed

__version__ = "1.1.0"

__all__ = [
    "BASE_TYPES", "CARDINALITIES", "EDIT_OPS", "RULE_OPS", "clone", "uid",
    "create_empty_state", "deserialize", "schema_of", "serialize", "validate_state",
    "add_object_type", "add_property", "add_shared_prop", "attach_shared_prop",
    "delete_object_type", "delete_property", "delete_shared_prop", "detach_shared_prop",
    "update_object_type", "update_property",
    "add_link_type", "create_link", "delete_link", "delete_link_type", "links_of", "update_link_type",
    "add_action_type", "delete_action_type", "describe_edits", "render_template",
    "run_action", "update_action_type",
    "audit_for", "linked_objects", "mark_notices_read", "object_label",
    "objects_of_type", "search_objects", "unread_notices", "usage_by_day",
    "create_branch", "diff_empty", "diff_schemas", "merge_proposal", "propose_merge",
    "reject_proposal", "switch_branch",
    "delete_dataset", "list_datasets", "pipeline_runs", "register_dataset", "run_pipeline",
    "invoke_logic", "list_logic", "register_logic",
    "seed",
]
