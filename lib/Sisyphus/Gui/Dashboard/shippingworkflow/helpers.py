from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from Sisyphus.Configuration import config
from Sisyphus import RestApiV1 as ra
from Sisyphus.Gui import DataModel as dm
from Sisyphus.Gui.Shipping.Tasks.ShippingLabel import ShippingLabel
from Sisyphus.RestApiV1 import whoami
import Sisyphus.RestApiV1.Utilities as rau

logger = config.getLogger(__name__)


def _safe_strip(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _get_authenticated_user_info() -> dict[str, str]:
    raw: dict[str, Any] = {}
    try:
        resp = whoami()
        if isinstance(resp, dict) and isinstance(resp.get("data"), dict):
            raw = dict(resp["data"])
        elif isinstance(resp, dict):
            raw = dict(resp)
    except Exception:
        logger.exception("whoami() failed while resolving the authenticated Dashboard user")
        raw = {}

    username = _safe_strip(raw.get("username"))
    full_name = _safe_strip(raw.get("full_name"))
    email = _safe_strip(raw.get("email"))

    try:
        users = (config.active_profile.profile_data or {}).get("users", {}) or {}
        if username and isinstance(users.get(username), dict):
            profile_user = users[username]
            full_name = _safe_strip(profile_user.get("full_name")) or full_name
            email = _safe_strip(profile_user.get("email")) or email
    except Exception:
        logger.exception("Failed to overlay active-profile user metadata for username=%s", username)

    return {
        "username": username,
        "full_name": full_name,
        "email": email,
    }


def _coerce_workdir_path(value: Any) -> Path | None:
    text = _safe_strip(value)
    if not text:
        return None
    return Path(text).expanduser()


def _get_dashboard_workdir_from_preferences() -> Path | None:
    pref_file = Path(config.active_profile.profile_dir) / "dash_user_preferences.txt"
    try:
        if pref_file.exists():
            saved = pref_file.read_text(encoding="utf-8").strip()
            if saved:
                return Path(saved).expanduser()
    except Exception:
        logger.exception("Failed reading Dashboard working directory preference from %s", pref_file)
    return None


def _get_dashboard_workdir_from_profile_user() -> Path | None:
    try:
        auth = _get_authenticated_user_info()
        username = auth.get("username") or ""
        users = (config.active_profile.profile_data or {}).get("users", {}) or {}
        if username and isinstance(users.get(username), dict):
            path_text = _safe_strip(users[username].get("working_directory"))
            if path_text:
                return Path(path_text).expanduser()
    except Exception:
        logger.exception("Failed reading user-specific working_directory from active profile")
    return None


def _component_type_from_record(record: dict[str, Any]) -> str:
    ws = record.get("workflow_state") or {}
    part = ws.get("part_info") or {}
    for key in ("part_type_id", "type_id", "component_type_id"):
        value = _safe_strip(part.get(key))
        if value:
            return value

    pid = _safe_strip(record.get("pid")) or _safe_strip(part.get("part_id"))
    if pid and "-" in pid:
        return pid.split("-", 1)[0]
    return pid


def _ensure_workdir(record: dict[str, Any]) -> Path:
    # Always prefer the current Dashboard preference/profile configuration first,
    # so stale values saved in dash_shipping_conf.json do not keep pointing to ~/.sisyphus/.
    base_path = (
        _get_dashboard_workdir_from_preferences()
        or _get_dashboard_workdir_from_profile_user()
        or _coerce_workdir_path(record.get("working_directory"))
        or Path.cwd()
    )

    type_id = _component_type_from_record(record)
    path = base_path / type_id if type_id else base_path

    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("Failed to create/access working directory %s; falling back to profile dir", path)
        fallback_base = Path(config.active_profile.profile_dir)
        path = fallback_base / type_id if type_id else fallback_base
        path.mkdir(parents=True, exist_ok=True)

    record["working_directory"] = str(base_path)
    record["resolved_working_directory"] = str(path)
    logger.info(
        "Shipping workflow working directory resolved to base=%s, final=%s",
        base_path,
        path,
    )
    return path


def is_surf_route(record: dict[str, Any]) -> bool:
    state = ((record.get("workflow_state") or {}).get("SelectPID") or {})
    return bool(state.get("confirm_surf"))



def _artifact_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H-%M")


def _artifact_filename(part_id: str, stem: str, original_filename: str) -> str:
    ext = Path(original_filename).suffix or ""
    return f"{part_id}-{stem}-{_artifact_timestamp()}{ext}"


def _content_type_from_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in {".png"}:
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "application/octet-stream"


def save_uploaded_artifact(record: dict[str, Any], file_storage: Any, stem: str) -> dict[str, str]:
    if not getattr(file_storage, "filename", ""):
        raise ValueError("No file was selected.")
    part_id = ((record.get("workflow_state") or {}).get("part_info") or {}).get("part_id") or record.get("pid") or "shipment"
    original_name = Path(file_storage.filename).name
    filename = _artifact_filename(part_id, stem, original_name)
    full_path = _ensure_workdir(record) / filename
    file_storage.save(full_path)
    return {
        "filename": filename,
        "full_filename": str(full_path),
        "original_filename": original_name,
        "content_type": _content_type_from_suffix(original_name),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }


def generate_shipping_email_html(record: dict[str, Any]) -> str:
    ws = record["workflow_state"]
    p3 = ws.get("PreShipping3", {})
    auth = _get_authenticated_user_info()
    sender_name = auth["full_name"] or auth["username"] or ""
    sender_email = auth["email"] or ""
    from_html = f"{sender_name} &lt;{sender_email}&gt;" if sender_email else sender_name
    part_id = ws["part_info"]["part_id"]
    poc_name = p3.get("approver_name", "")
    poc_email = p3.get("approver_email", "")
    return (
        "<table>"
        f"<tr><td width='100'>From:</td><td>{from_html}</td></tr>"
        "<tr><td>To:</td><td>FD Logistics Team &lt;sdshipments@fnal.gov&gt;</td></tr>"
        f"<tr><td>Subject:</td><td>Request for the final approval for shipment PID = {part_id}</td></tr>"
        "<tr><td colspan='2'>&nbsp;</td></tr>"
        "<tr><td colspan='2'>"
        "Dear FD Logistics team,<br/><br/>"
        "I would like to request a new shipment.<br/><br/>"
        "Should there be any issue with this shipment, email to:"
        f"<ul><li>{poc_name} &lt;{poc_email}&gt;</li></ul>"
        "Sincerely,<br/><br/>"
        f"{sender_name}<br/>{sender_email}<br/>"
        "</td></tr></table>"
    )


def upload_shipping_artifacts(record: dict[str, Any]) -> dict[str, Any]:
    ws = record["workflow_state"]
    part_id = ws["part_info"]["part_id"]
    s2 = ws.get("Shipping2", {})
    s4 = ws.get("Shipping4", {})
    uploaded: dict[str, Any] = {}

    def _post_saved_file(info: dict[str, Any], comments: str) -> dict[str, Any]:
        path = info.get("full_filename")
        if not path or not os.path.exists(path):
            raise FileNotFoundError(path or "missing file path")
        resp = ra.post_hwitem_image(part_id, {"comments": comments}, path)
        return {
            "filename": info.get("filename"),
            "full_filename": path,
            "image_id": resp["image_id"],
            "uploaded_at": datetime.now().isoformat(timespec="seconds"),
        }

    bol = s2.get("bol_file")
    if bol and bol.get("full_filename"):
        uploaded["bol_info"] = _post_saved_file(bol, "shipping_bol")

    proforma = s2.get("proforma_file")
    if proforma and proforma.get("full_filename"):
        uploaded["proforma_info"] = _post_saved_file(proforma, "shipping_proforma")

    approval = s4.get("approval_file")
    if approval and approval.get("full_filename"):
        uploaded["approval_info"] = _post_saved_file(approval, "shipping_final_approval")

    ws.setdefault("Shipping2", {}).update({k: v for k, v in uploaded.items() if k in {"bol_info", "proforma_info"}})
    ws.setdefault("Shipping4", {}).update({k: v for k, v in uploaded.items() if k == "approval_info"})
    return uploaded


def patch_shipping_to_hwdb(record: dict[str, Any]) -> dict[str, Any]:
    ws = record["workflow_state"]
    part = ws["part_info"]
    part_id = part["part_id"]

    if is_surf_route(record):
        upload_shipping_artifacts(record)

    s2 = ws.get("Shipping2", {})
    s4 = ws.get("Shipping4", {})
    checklist = {
        "POC name": ws.get("PreShipping3", {}).get("approver_name"),
        "POC Email": [s.strip() for s in ws.get("PreShipping3", {}).get("approver_email", "").split(",") if s.strip()],
        "System Name (ID)": f"{part.get('system_name')} ({part.get('system_id')})",
        "Subsystem Name (ID)": f"{part.get('subsystem_name')} ({part.get('subsystem_id')})",
        "Component Type Name (ID)": f"{part.get('part_type_name')} ({part.get('part_type_id')})",
        "DUNE PID": part_id,
    }
    if is_surf_route(record):
        checklist.update({
            "Image ID for BoL": s2.get("bol_info", {}).get("image_id"),
            "Image ID for Proforma Invoice": s2.get("proforma_info", {}).get("image_id"),
            "Image ID for the final approval message": s4.get("approval_info", {}).get("image_id"),
            "FD Logistics team final approval (name)": s4.get("approved_by"),
            "FD Logistics team final approval (date in CST)": s4.get("approved_time"),
            "DUNE Shipping Sheet has been attached": s4.get("confirm_attached_sheet"),
            "This shipment has been adequately insured for transit": s4.get("confirm_insured"),
        })

    item = dm.HWItem(part_id=part_id).data
    specs = item["specifications"][-1]
    if not isinstance(specs.get("DATA"), dict):
        specs["DATA"] = {}
    specs["DATA"]["Shipping Checklist"] = [{k: v} for k, v in checklist.items()]

    manufacturer = item.get("manufacturer")
    manufacturer_node = {"id": manufacturer["id"]} if manufacturer is not None else None
    update_data = {
        "part_id": part_id,
        "comments": item.get("comments"),
        "manufacturer": manufacturer_node,
        "serial_number": item.get("serial_number"),
        "specifications": specs,
    }
    resp = ra.patch_hwitem(part_id, update_data)
    ws.setdefault("Shipping4", {})["patched_at"] = datetime.now().isoformat(timespec="seconds")
    return resp


def update_shipping_location(record: dict[str, Any]) -> bool:
    ws = record["workflow_state"]
    part_id = ws["part_info"]["part_id"]
    s5 = ws.get("Shipping5", {})
    data = {
        "location": {"id": 0},
        "arrived": s5.get("shipment_time"),
        "comments": s5.get("comments", ""),
    }
    ra.post_hwitem_location(part_id, data)
    s5["location"] = {"institution_id": 0, "institution_name": "In-Transit", "country_code": "--"}
    s5["location_posted_at"] = datetime.now().isoformat(timespec="seconds")
    return True


def generate_shipping_csv(record: dict[str, Any]) -> dict[str, str]:
    ws = record["workflow_state"]
    part_id = ws["part_info"]["part_id"]
    filename = f"{part_id}-shipping-{_artifact_timestamp()}.csv"
    full_path = _ensure_workdir(record) / filename

    with full_path.open("w", newline="", encoding="utf-8") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=",")
        part = ws.get("part_info", {})
        rows = [
            ["POC name", ws.get("PreShipping3", {}).get("approver_name", "")],
            ["POC Email", ws.get("PreShipping3", {}).get("approver_email", "")],
            ["System Name (ID)", f"{part.get('system_name', '')} ({part.get('system_id', '')})"],
            ["Subsystem Name (ID)", f"{part.get('subsystem_name', '')} ({part.get('subsystem_id', '')})"],
            ["Component Type Name (ID)", f"{part.get('part_type_name', '')} ({part.get('part_type_id', '')})"],
            ["DUNE PID", part_id],
        ]
        if is_surf_route(record):
            rows.extend([
                ["Image ID for BoL", ws.get("Shipping2", {}).get("bol_info", {}).get("image_id", "")],
                ["Image ID for Proforma Invoice", ws.get("Shipping2", {}).get("proforma_info", {}).get("image_id", "")],
                ["Image ID for the final approval message", ws.get("Shipping4", {}).get("approval_info", {}).get("image_id", "")],
                ["FD Logistics team final approval (name)", ws.get("Shipping4", {}).get("approved_by", "")],
                ["FD Logistics team final approval (date in CT)", ws.get("Shipping4", {}).get("approved_time", "")],
                ["DUNE Shipping Sheet has been attached", ws.get("Shipping4", {}).get("confirm_attached_sheet", False)],
                ["This shipment has been adequately insured for transit", ws.get("Shipping4", {}).get("confirm_insured", False)],
            ])
        rows.append(["SubPIDs:"])
        for sc in part.get("subcomponents", {}).values():
            rows.append([f"{sc.get('Component Type Name', '')} ({sc.get('Functional Position Name', '')}),{sc.get('Sub-component PID', '')}"])
        csvwriter.writerows(rows)

    info = {
        "csv_filename": filename,
        "csv_full_filename": str(full_path),
        "csv_generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    record.setdefault("workflow_state", {})["Shipping6"] = {
        **record.setdefault("workflow_state", {}).get("Shipping6", {}),
        **info,
    }
    return info


def _extract_checklist_value(checklist_entries: Any, key_name: str) -> Any:
    if not isinstance(checklist_entries, list):
        return None
    for entry in checklist_entries:
        if isinstance(entry, dict) and key_name in entry:
            return entry.get(key_name)
    return None


def get_shipping_service_type_from_hwdb(record: dict[str, Any], refresh: bool = False) -> str:
    ws = record.setdefault("workflow_state", {})
    cache = ws.get("ShippingInfoFromHWDB")
    if isinstance(cache, dict) and cache.get("shipping_service_type") and not refresh:
        return str(cache.get("shipping_service_type"))

    part_id = ((ws.get("part_info") or {}).get("part_id")) or record.get("pid")
    shipping_service_type = "Domestic"
    hts_value = None

    try:
        item = dm.HWItem(part_id=part_id, refresh=refresh).data
        specs = item.get("specifications") or []
        data_block = {}
        if specs:
            latest = specs[-1] or {}
            data_block = latest.get("DATA") or {}
        checklist_entries = data_block.get("Pre-Shipping Checklist")
        hts_value = _extract_checklist_value(checklist_entries, "HTS code")
        if hts_value is not None and str(hts_value).strip() not in {"", "None", "null"}:
            shipping_service_type = "International"
    except Exception:
        logger.exception("Failed to read Pre-Shipping Checklist / HTS code from HWDB for %s", part_id)

    ws["ShippingInfoFromHWDB"] = {
        "shipping_service_type": shipping_service_type,
        "hts_code": hts_value,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    return shipping_service_type




def get_institution_options(use_cache: bool = True) -> list[dict[str, Any]]:
    try:
        if hasattr(rau, "get_institutions"):
            institutions = rau.get_institutions(use_cache=use_cache)
        else:
            institutions = ra.get_institutions()
    except Exception:
        logger.exception("Failed to load institution options from HWDB")
        return []

    options: list[dict[str, Any]] = []
    for node in institutions or []:
        if not isinstance(node, dict):
            continue
        country = node.get("country") or {}
        country_code = _safe_strip(country.get("code"))
        name = _safe_strip(node.get("name"))
        label = f"({node.get('id')}) {name}"
        if country_code:
            label += f" [{country_code}]"
        options.append({
            "id": node.get("id"),
            "name": name,
            "country_code": country_code,
            "label": label,
        })
    options.sort(key=lambda x: (str(x.get("name", "")).lower(), str(x.get("id", ""))))
    return options




def get_country_options(use_cache: bool = True) -> list[dict[str, str]]:
    seen: dict[str, str] = {}
    for opt in get_institution_options(use_cache=use_cache):
        code = _safe_strip(opt.get("country_code"))
        if code and code not in seen:
            seen[code] = code
    return [{"code": code, "label": code} for code in sorted(seen)]


def get_location_history_rows(part_id: str) -> list[dict[str, str]]:
    try:
        resp = ra.get_hwitem_locations(part_id)
    except Exception:
        logger.exception("Failed to load location history from HWDB for %s", part_id)
        return []

    rows: list[dict[str, str]] = []
    data = []
    if isinstance(resp, dict):
        data = resp.get("data") or []

    for eachloc in data:
        if not isinstance(eachloc, dict):
            continue
        location = eachloc.get("location") or {}
        location_id = location.get("id")
        location_name = _safe_strip(location.get("name"))
        arrived = _safe_strip(eachloc.get("arrived"))
        comments = _safe_strip(eachloc.get("comments"))
        if location_name:
            if location_id is not None:
                location_label = f"({location_id}) {location_name}"
            else:
                location_label = location_name
        else:
            location_label = "—"
        rows.append({
            "location": location_label,
            "arrived": arrived or "—",
            "comments": comments or "",
        })
    return rows


def update_transit_location(record: dict[str, Any]) -> bool:
    ws = record["workflow_state"]
    part_id = ws["part_info"]["part_id"]
    t1 = ws.get("Transit1", {})
    location_id = t1.get("location_id")
    data = {
        "location": {"id": int(location_id)},
        "arrived": t1.get("arrived"),
        "comments": t1.get("comments", ""),
    }
    ra.post_hwitem_location(part_id, data)
    selected_name = ""
    for opt in get_institution_options():
        if str(opt.get("id")) == str(location_id):
            selected_name = opt.get("name") or ""
            break
    t1["location_posted_at"] = datetime.now().isoformat(timespec="seconds")
    t1["location_name"] = selected_name
    return True




def _post_location_for_pid(part_id: str, location_id: int, arrived: str, comments: str) -> Any:
    data = {
        "location": {"id": int(location_id)},
        "arrived": arrived,
        "comments": comments,
    }
    return ra.post_hwitem_location(part_id, data)


def _detach_all_subcomponents_exact(parent_pid: str) -> dict[str, Any]:
    hwitem = dm.HWItem(part_id=parent_pid)
    payload = {
        "component": {"part_id": parent_pid},
        "subcomponents": {s["functional_position"]: None for s in hwitem.subcomponents},
    }
    resp = ra.patch_subcomponents(parent_pid, payload)
    dm.HWItem(part_id=parent_pid, refresh=True)
    return {
        "response": resp,
        "detached_part_ids": [s["part_id"] for s in hwitem.subcomponents],
    }


def generate_receiving_email_html(record: dict[str, Any]) -> str:
    ws = record["workflow_state"]
    part_id = ws["part_info"]["part_id"]
    r2 = ws.get("Receiving2", {})
    p3 = ws.get("PreShipping3", {})
    auth = _get_authenticated_user_info()
    sender_name = auth["full_name"] or auth["username"] or ""
    sender_email = auth["email"] or ""
    from_html = f"{sender_name} &lt;{sender_email}&gt;" if sender_email else sender_name

    to_name = p3.get("approver_name", "")
    to_email = p3.get("approver_email", "")
    loc_name = r2.get("location_name") or r2.get("location_display") or ""
    arrived = r2.get("arrived", "")
    comments = r2.get("comments", "")
    return (
        "<table>"
        f"<tr><td width='100'>From:</td><td>{from_html}</td></tr>"
        f"<tr><td>To:</td><td>{to_name} &lt;{to_email}&gt;</td></tr>"
        f"<tr><td>Subject:</td><td>Shipment received: {part_id}</td></tr>"
        "<tr><td colspan='2'>&nbsp;</td></tr>"
        "<tr><td colspan='2'>"
        f"Dear {to_name or 'colleague'},<br/><br/>"
        f"This shipment box has been received.<br/>"
        f"PID: {part_id}<br/>"
        f"Location: {loc_name or 'n/a'}<br/>"
        f"Received at: {arrived or 'n/a'}<br/>"
        f"Comments: {comments or 'n/a'}<br/><br/>"
        "Sincerely,<br/><br/>"
        f"{sender_name}<br/>{sender_email}"
        "</td></tr></table>"
    )


def update_receiving_location(record: dict[str, Any]) -> dict[str, Any]:
    ws = record["workflow_state"]
    part = ws["part_info"]
    parent_pid = part["part_id"]
    r2 = ws.get("Receiving2", {})
    location_id = int(r2.get("location_id"))
    arrived = r2.get("arrived")
    comments = r2.get("comments", "")
    transshipping = bool((ws.get("SelectPID") or {}).get("confirm_transshipping"))

    result = {
        "parent_updated": False,
        "subcomponents_updated": [],
        "subcomponents_unlinked": [],
        "subcomponents_unlink_failures": [],
        "transshipping": transshipping,
    }

    _post_location_for_pid(parent_pid, location_id, arrived, comments)
    result["parent_updated"] = True

    selected_name = ""
    for opt in get_institution_options():
        if str(opt.get("id")) == str(location_id):
            selected_name = opt.get("name") or ""
            r2["location_name"] = selected_name
            r2["location_display"] = opt.get("label") or ""
            r2["country_code"] = opt.get("country_code") or r2.get("country_code", "")
            break

    if not transshipping:
        hwitem = dm.HWItem(part_id=parent_pid)
        subcomponents = list(hwitem.subcomponents)
        for subcomponent in subcomponents:
            child_pid = subcomponent["part_id"]
            _post_location_for_pid(child_pid, location_id, arrived, comments)
            result["subcomponents_updated"].append(child_pid)

        detach_info = _detach_all_subcomponents_exact(parent_pid)
        result["subcomponents_unlinked"] = detach_info.get("detached_part_ids", [])
        result["detach_response"] = detach_info.get("response")
        result["subcomponents_unlink_failures"] = []
    else:
        result["subcomponents_unlinked"] = []
        result["subcomponents_unlink_failures"] = []

    r2["location_posted_at"] = datetime.now().isoformat(timespec="seconds")
    ws["Receiving2"] = r2
    ws["ReceivingResult"] = result
    return result



def _get_hwitem_image_list(part_id: str) -> list[dict[str, Any]]:
    getter = getattr(ra, "get_hwitem_image_list", None)
    if getter is None:
        return []
    try:
        resp = getter(part_id)
    except Exception:
        logger.exception("Failed to get image list for %s", part_id)
        return []
    if isinstance(resp, dict):
        return resp.get("data") or []
    return []


def get_preshipping_gate_status(record: dict[str, Any] | None = None, pid: str | None = None) -> dict[str, Any]:
    part_id = pid or (((record or {}).get("workflow_state") or {}).get("part_info") or {}).get("part_id") or ((record or {}).get("part_info") or {}).get("part_id")
    if not part_id:
        return {
            "status_id": None,
            "status_name": "",
            "certified": False,
            "uploaded": False,
            "qaqc_ready": False,
            "executive_summary_found": False,
            "executive_summary_image_name": "",
            "executive_summary_uploader_name": "",
            "executive_summary_created": "",
        }

    item = dm.HWItem(part_id=part_id, refresh=True).data
    status = item.get("status") or {}
    status_id = status.get("id")
    status_name = _safe_strip(status.get("name"))
    certified = bool(item.get("certified_qaqc"))
    uploaded = bool(item.get("qaqc_uploaded"))
    qaqc_ready = certified and uploaded and status_id in {120, 140}

    pattern = re.compile(rf"^ExecutiveSummary_{re.escape(part_id)}_.+\.pdf$", re.IGNORECASE)
    latest_match = None
    latest_created = ""
    for node in _get_hwitem_image_list(part_id):
        image_name = _safe_strip(node.get("image_name"))
        if not pattern.match(image_name):
            continue
        created = _safe_strip(node.get("created"))
        if latest_match is None or created > latest_created:
            latest_match = node
            latest_created = created

    if latest_match:
        creator = latest_match.get("creator") or {}
        exec_found = True
        exec_name = _safe_strip(latest_match.get("image_name"))
        uploader_name = _safe_strip(creator.get("name"))
        created = _safe_strip(latest_match.get("created"))
    else:
        exec_found = False
        exec_name = ""
        uploader_name = ""
        created = ""

    return {
        "status_id": status_id,
        "status_name": status_name,
        "certified": certified,
        "uploaded": uploaded,
        "qaqc_ready": qaqc_ready,
        "executive_summary_found": exec_found,
        "executive_summary_image_name": exec_name,
        "executive_summary_uploader_name": uploader_name,
        "executive_summary_created": created,
    }


def route_label(record: dict[str, Any]) -> str:
    state = ((record.get("workflow_state") or {}).get("SelectPID") or {})
    if state.get("confirm_surf"):
        return "Shipping to SURF"
    if state.get("confirm_transshipping"):
        return "Transshipping to SURF"
    if state.get("confirm_non_surf"):
        return "Shipping to non-SURF"
    return "Shipping to SURF"


def generate_preshipping_csv(record: dict[str, Any]) -> dict[str, str]:
    ws = record["workflow_state"]
    part_id = ws["part_info"]["part_id"]
    now = datetime.now().strftime("%Y-%m-%d-%H-%M")
    filename = f"{part_id}-preshipping-{now}.csv"
    full_path = _ensure_workdir(record) / filename

    with full_path.open("w", newline="", encoding="utf-8") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=",")
        p4a = ws.get("PreShipping4a", {})
        p4b = ws.get("PreShipping4b", {})
        part = ws.get("part_info", {})

        rows = []
        if is_surf_route(record):
            rows.extend([
                ["Dimension", p4a.get("dimension", "")],
                ["Weight", p4a.get("weight", "")],
                ["Freight Forwarder name", p4b.get("freight_forwarder", "")],
                ["Mode of Transportation", p4b.get("mode_of_transportation", "")],
                ["Expected Arrival Date (CT)", p4b.get("expected_arrival_time", "")],
                ["Shipment's origin", p4a.get("shipment_origin", "")],
                ["HTS code", p4a.get("hts_code", "")],
                [],
            ])

        rows.extend([
            ["System Name (ID)", f"{part.get('system_name', '')} ({part.get('system_id', '')})"],
            ["Subsystem Name (ID)", f"{part.get('subsystem_name', '')} ({part.get('subsystem_id', '')})"],
            ["Component Type Name (ID)", f"{part.get('part_type_name', '')} ({part.get('part_type_id', '')})"],
            ["DUNE PID", part_id],
            [],
            ["Sub-component PID", "Component Type Name", "Func. Pos. Name"],
        ])
        for sc in part.get("subcomponents", {}).values():
            rows.append([
                sc.get("Sub-component PID", ""),
                sc.get("Component Type Name", ""),
                sc.get("Functional Position Name", ""),
            ])
        csvwriter.writerows(rows)

    info = {
        "csv_filename": filename,
        "csv_full_filename": str(full_path),
        "csv_generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    record.setdefault("workflow_state", {})["PreShipping5"] = {
        **record.setdefault("workflow_state", {}).get("PreShipping5", {}),
        **info,
    }
    return info


def generate_preshipping_email_html(record: dict[str, Any]) -> str:
    ws = record["workflow_state"]
    p5 = ws.get("PreShipping5", {})
    csv_filename = p5.get("csv_filename") or generate_preshipping_csv(record)["csv_filename"]
    qarep_name = ws.get("PreShipping2", {}).get("qa_rep_name", "")
    qarep_email = ws.get("PreShipping2", {}).get("qa_rep_email", "")
    poc_name = ws.get("PreShipping3", {}).get("approver_name", "")
    poc_email = ws.get("PreShipping3", {}).get("approver_email", "")

    auth = _get_authenticated_user_info()
    sender_name = auth["full_name"] or auth["username"] or ""
    sender_email = auth["email"] or ""

    ws["user_name"] = sender_name
    ws["user_email"] = sender_email

    from_html = f"{sender_name} &lt;{sender_email}&gt;" if sender_email else sender_name

    return (
        "<table>"
        f"<tr><td width='100'>From:</td><td>{from_html}</td></tr>"
        "<tr><td>To:</td><td>FD Logistics Team &lt;sdshipments@fnal.gov&gt;</td></tr>"
        "<tr><td>Subject:</td><td>Request an acknowledgement for a new shipment</td></tr>"
        "<tr><td colspan='2'>&nbsp;</td></tr>"
        "<tr><td colspan='2'>"
        "Dear FD Logistics team,<br/><br/>"
        "I would like to request a new shipment.<br/>"
        f"This shipment has been approved by the Consortium QA Representative, {qarep_name} ({qarep_email}).<br/><br/>"
        f"Please find the attached csv file, {csv_filename}, that contains the required information for this shipment.<br/><br/>"
        "Should there be any issue with this shipment, email to:"
        f"<ul><li>{poc_name} &lt;{poc_email}&gt;</li></ul>"
        "Sincerely,<br/><br/>"
        f"{sender_name}<br/><br/>"
        f"Attachment: {csv_filename}"
        "</td></tr></table>"
    )


def generate_shipping_sheet(record: dict[str, Any]) -> dict[str, str]:
    ws = record["workflow_state"]
    part_id = ws["part_info"]["part_id"]
    filename = f"{part_id}-shipping-label.pdf"
    full_path = _ensure_workdir(record) / filename
    ShippingLabel(str(full_path), ws, show_logo=False, debug=False)
    info = {
        "pdf_filename": filename,
        "pdf_full_filename": str(full_path),
        "pdf_generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    record.setdefault("workflow_state", {})["PreShipping7"] = {
        **record.setdefault("workflow_state", {}).get("PreShipping7", {}),
        **info,
    }
    return info


def patch_preshipping_to_hwdb(record: dict[str, Any]) -> dict[str, Any]:
    ws = record["workflow_state"]
    part = ws["part_info"]
    part_id = part["part_id"]
    p7 = ws.get("PreShipping7", {})
    pdf_path = p7.get("pdf_full_filename")
    if not pdf_path or not os.path.exists(pdf_path):
        pdf_path = generate_shipping_sheet(record)["pdf_full_filename"]

    data = {"comments": "shipping sheet"}
    resp = ra.post_hwitem_image(part_id, data, pdf_path)
    image_id = resp["image_id"]

    p2 = ws.get("PreShipping2", {})
    p3 = ws.get("PreShipping3", {})
    p4a = ws.get("PreShipping4a", {})
    p4b = ws.get("PreShipping4b", {})
    p6 = ws.get("PreShipping6", {})

    if is_surf_route(record):
        checklist = {
            "QA Rep name": p2.get("qa_rep_name"),
            "QA Rep Email": [s.strip() for s in p2.get("qa_rep_email", "").split(",") if s.strip()],
            "POC name": p3.get("approver_name"),
            "POC Email": [s.strip() for s in p3.get("approver_email", "").split(",") if s.strip()],
            "System Name (ID)": f"{part.get('system_name')} ({part.get('system_id')})",
            "Subsystem Name (ID)": f"{part.get('subsystem_name')} ({part.get('subsystem_id')})",
            "Component Type Name (ID)": f"{part.get('part_type_name')} ({part.get('part_type_id')})",
            "DUNE PID": part_id,
            "HTS code": p4a.get("hts_code") if p4a.get("shipping_service_type") != "Domestic" else None,
            "Origin of this shipment": p4a.get("shipment_origin"),
            "Destination of this shipment": p4a.get("shipment_destination"),
            "Dimension of this shipment": p4a.get("dimension"),
            "Weight of this shipment": p4a.get("weight"),
            "Freight Forwarder name": p4b.get("freight_forwarder"),
            "Mode of Transportation": p4b.get("mode_of_transportation"),
            "Expected Arrival Date (CT)": p4b.get("expected_arrival_time"),
            "FD Logistics team acknoledgement (name)": p6.get("acknowledged_by"),
            "FD Logistics team acknoledgement (date in CT)": p6.get("acknowledged_time"),
            "Visual Inspection (YES = no damage)": "YES" if p6.get("damage_status") == "no damage" else "NO",
            "Visual Inspection Damage": p6.get("damage_description"),
            "Image ID for this Shipping Sheet": image_id,
        }
    else:
        checklist = {
            "POC name": p3.get("approver_name"),
            "POC Email": [s.strip() for s in p3.get("approver_email", "").split(",") if s.strip()],
            "System Name (ID)": f"{part.get('system_name')} ({part.get('system_id')})",
            "Subsystem Name (ID)": f"{part.get('subsystem_name')} ({part.get('subsystem_id')})",
            "Component Type Name (ID)": f"{part.get('part_type_name')} ({part.get('part_type_id')})",
            "DUNE PID": part_id,
            "Origin of this shipment": p4a.get("shipment_origin"),
            "Destination of this shipment": p4a.get("shipment_destination"),
            "Visual Inspection (YES = no damage)": "YES" if p6.get("damage_status") == "no damage" else "NO",
            "Visual Inspection Damage": p6.get("damage_description"),
            "Image ID for this Shipping Sheet": image_id,
        }

    sub_pids = []
    for v in part.get("subcomponents", {}).values():
        sub_pids.append({f"{v.get('Component Type Name')} ({v.get('Functional Position Name')})": v.get("Sub-component PID")})

    item_resp = {"Item": dm.HWItem(part_id=part_id).data}
    specs = item_resp["Item"]["specifications"][-1]
    if not isinstance(specs.get("DATA"), dict):
        specs["DATA"] = {}
    specs["DATA"]["Pre-Shipping Checklist"] = [{k: v} for k, v in checklist.items()]
    specs["DATA"]["SubPIDs"] = sub_pids

    manufacturer = item_resp["Item"].get("manufacturer")
    manufacturer_node = {"id": manufacturer["id"]} if manufacturer is not None else None
    update_data = {
        "part_id": part_id,
        "comments": item_resp["Item"].get("comments"),
        "manufacturer": manufacturer_node,
        "serial_number": item_resp["Item"].get("serial_number"),
        "specifications": specs,
    }
    logger.info(json.dumps(update_data, indent=2, default=str))
    patch_resp = ra.patch_hwitem(part_id, update_data)
    dm.HWItem(part_id=part_id, refresh=True)

    result = {
        "image_id": image_id,
        "pdf_full_filename": pdf_path,
        "patched": True,
        "patch_response": patch_resp,
        "patched_at": datetime.now().isoformat(timespec="seconds"),
    }
    record.setdefault("workflow_state", {})["PreShipping7"] = {
        **record.setdefault("workflow_state", {}).get("PreShipping7", {}),
        **result,
    }
    return result
