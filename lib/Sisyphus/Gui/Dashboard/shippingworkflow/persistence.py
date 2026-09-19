from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from Sisyphus.Configuration import config

CONF_FILENAME = 'dash_shipping_conf.json'


def get_persistence_path() -> Path:
    return Path(config.active_profile.profile_dir) / CONF_FILENAME


def load_all_progress() -> dict[str, Any]:
    path = get_persistence_path()
    if not path.exists():
        return {"shipments": {}}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {"shipments": {}}
    if not isinstance(data, dict):
        return {"shipments": {}}
    if not isinstance(data.get('shipments'), dict):
        data['shipments'] = {}
    return data


def save_all_progress(data: dict[str, Any]) -> None:
    path = get_persistence_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')
    tmp.replace(path)


def get_workflow_progress(pid: str) -> dict[str, Any] | None:
    data = load_all_progress()
    shipments = data.get('shipments', {})
    record = shipments.get(pid)
    if isinstance(record, dict):
        return deepcopy(record)
    return None


def save_workflow_progress(pid: str, record: dict[str, Any]) -> None:
    data = load_all_progress()
    data.setdefault('shipments', {})[pid] = deepcopy(record)
    save_all_progress(data)
