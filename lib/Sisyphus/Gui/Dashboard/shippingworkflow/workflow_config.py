from __future__ import annotations

from copy import deepcopy
from typing import Any

WORKFLOWS = {
    "preshipping": {
        "label": "Pre-Shipping",
        "scenes": [
            {"index": 1, "key": "PreShipping1", "title": "Pre-Shipping Workflow (1)", "short_title": "Pre-Ship (1)"},
            {"index": 2, "key": "PreShipping2", "title": "Pre-Shipping Workflow (2)", "short_title": "Pre-Ship (2)"},
            {"index": 3, "key": "PreShipping3", "title": "Pre-Shipping Workflow (3)", "short_title": "Pre-Ship (3)"},
            {"index": 4, "key": "PreShipping4a", "title": "Pre-Shipping Workflow (4a)", "short_title": "Pre-Ship (4a)"},
            {"index": 5, "key": "PreShipping4b", "title": "Pre-Shipping Workflow (4b)", "short_title": "Pre-Ship (4b)"},
            {"index": 6, "key": "PreShipping5", "title": "Pre-Shipping Workflow (5)", "short_title": "Pre-Ship (5)"},
            {"index": 7, "key": "PreShipping6", "title": "Pre-Shipping Workflow (6)", "short_title": "Pre-Ship (6)"},
            {"index": 8, "key": "PreShipping7", "title": "Pre-Shipping Workflow (7)", "short_title": "Pre-Ship (7)"},
        ],
    },
    "shipping": {
        "label": "Shipping",
        "scenes": [
            {"index": 1, "key": "Shipping1", "title": "Shipping Workflow (1)", "short_title": "Ship (1)"},
            {"index": 2, "key": "Shipping2", "title": "Shipping Workflow (2)", "short_title": "Ship (2)"},
            {"index": 3, "key": "Shipping3", "title": "Shipping Workflow (3)", "short_title": "Ship (3)"},
            {"index": 4, "key": "Shipping4", "title": "Shipping Workflow (4)", "short_title": "Ship (4)"},
            {"index": 5, "key": "Shipping5", "title": "Shipping Workflow (5)", "short_title": "Ship (5)"},
            {"index": 6, "key": "Shipping6", "title": "Shipping Workflow (6)", "short_title": "Ship (6)"},
        ],
    },
    "transit": {"label": "Updating Location", "scenes": [{"index": 1, "key": "Transit1", "title": "Updating Location", "short_title": "Update Loc"}]},
    "receiving": {"label": "Receiving", "scenes": [{"index": 1, "key": "Receiving1", "title": "Receiving Workflow (1)", "short_title": "Recv (1)"}, {"index": 2, "key": "Receiving2", "title": "Receiving Workflow (2)", "short_title": "Recv (2)"}, {"index": 3, "key": "Receiving3", "title": "Receiving Workflow (3)", "short_title": "Recv (3)"}]},
}


def get_workflow_definition(workflow_type: str) -> dict[str, Any]:
    return deepcopy(WORKFLOWS.get(workflow_type, {}))


def get_scene(workflow_type: str, scene_index: int) -> dict[str, Any] | None:
    wf = WORKFLOWS.get(workflow_type)
    if not wf:
        return None
    scenes = wf.get("scenes", [])
    if 1 <= scene_index <= len(scenes):
        return deepcopy(scenes[scene_index - 1])
    return None


def get_scene_count(workflow_type: str) -> int:
    wf = WORKFLOWS.get(workflow_type)
    return len((wf or {}).get("scenes", []))
