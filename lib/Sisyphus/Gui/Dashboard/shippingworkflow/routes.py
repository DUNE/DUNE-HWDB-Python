#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
from html import escape

from flask import Response, redirect, request

from Sisyphus.Configuration import config
from Sisyphus.Gui.Shipping.Tasks.Database import download_part_info

from .helpers import generate_receiving_email_html, get_institution_options, get_preshipping_gate_status, get_shipping_service_type_from_hwdb, patch_preshipping_to_hwdb, patch_shipping_to_hwdb, save_uploaded_artifact, update_receiving_location, update_shipping_location, update_transit_location
from .persistence import get_workflow_progress, save_workflow_progress
from .renderers import (
    base_query,
    render_complete,
    render_launcher,
    render_placeholder,
    render_preshipping1,
    render_preshipping2,
    render_preshipping3,
    render_preshipping4a,
    render_preshipping4b,
    render_preshipping5,
    render_preshipping6,
    render_preshipping7,
    render_shipping1,
    render_shipping2,
    render_shipping3,
    render_shipping4,
    render_shipping5,
    render_shipping6,
    render_transit1,
    render_receiving1,
    render_receiving2,
    render_receiving3,
)
from .workflow_config import get_scene_count

logger = config.getLogger(__name__)


def _new_record(pid: str, state: dict) -> dict:
    select_state = {
        "confirm_surf": True,
        "confirm_non_surf": False,
        "confirm_transshipping": False,
    }
    return {
        "pid": pid,
        "part_info": deepcopy((state or {}).get("part_info") or {}),
        "workflow_state": {**deepcopy(state or {}), "SelectPID": deepcopy(select_state)},
        "workflow_type": "",
        "current_scene": 0,
        "working_directory": str((config.active_profile.profile_dir)),
    }


def _load_or_init_record(pid: str) -> dict:
    record = get_workflow_progress(pid)
    if record:
        record.setdefault("workflow_state", {})
        record["workflow_state"].setdefault("SelectPID", {"confirm_surf": True, "confirm_non_surf": False, "confirm_transshipping": False})
        return record
    state = download_part_info(pid, refresh=True)
    record = _new_record(pid, state)
    save_workflow_progress(pid, record)
    return record


def _save_page_state(record: dict, page_key: str, page_state: dict) -> None:
    record.setdefault("workflow_state", {})
    record["workflow_state"][page_key] = deepcopy(page_state)
    save_workflow_progress(record["pid"], record)


def _scene_url(pid: str, workflow: str, scene: int, key: str | None) -> str:
    return "/shipping-workflow/scene?" + base_query(pid, workflow, scene, key)


def _normalize_text(name: str) -> str:
    return (request.form.get(name) or "").strip()


def _save_route_choice(record: dict) -> None:
    choice = (request.form.get("route_choice") or "").strip() or "confirm_surf"
    page_state = {
        "confirm_surf": choice == "confirm_surf",
        "confirm_non_surf": choice == "confirm_non_surf",
        "confirm_transshipping": choice == "confirm_transshipping",
    }
    _save_page_state(record, "SelectPID", page_state)


def _normalize_datetime_local(name: str) -> str:
    value = (request.form.get(name) or '').strip()
    return value


def _maybe_save_uploaded_file(record: dict, field_name: str, stem: str) -> dict | None:
    file_storage = request.files.get(field_name)
    if file_storage is None or not getattr(file_storage, 'filename', ''):
        return None
    return save_uploaded_artifact(record, file_storage, stem)

def _handle_preshipping_submit(record: dict, scene: int) -> tuple[bool, str]:
    if scene == 1:
        gate = get_preshipping_gate_status(record)
        page_state = {
            "confirm_list": bool(request.form.get("confirm_list")),
            "qaqc_ready": bool(gate.get("qaqc_ready")),
            "executive_summary_found": bool(gate.get("executive_summary_found")),
            "status_id": gate.get("status_id"),
            "status_name": gate.get("status_name"),
            "certified": bool(gate.get("certified")),
            "uploaded": bool(gate.get("uploaded")),
            "executive_summary_image_name": gate.get("executive_summary_image_name", ""),
            "executive_summary_uploader_name": gate.get("executive_summary_uploader_name", ""),
        }
        _save_page_state(record, "PreShipping1", page_state)
        p2 = dict((record.get("workflow_state") or {}).get("PreShipping2") or {})
        if gate.get("executive_summary_uploader_name"):
            p2["qa_rep_name"] = gate.get("executive_summary_uploader_name", "")
            _save_page_state(record, "PreShipping2", p2)
        return (bool(page_state["confirm_list"] and page_state["qaqc_ready"] and page_state["executive_summary_found"]), "")

    if scene == 2:
        page_state = {"qa_rep_name": _normalize_text("qa_rep_name"), "qa_rep_email": _normalize_text("qa_rep_email"), "test_info": _normalize_text("test_info")}
        if not page_state["qa_rep_name"]:
            gate = get_preshipping_gate_status(record)
            if gate.get("executive_summary_uploader_name"):
                page_state["qa_rep_name"] = gate.get("executive_summary_uploader_name", "")
        _save_page_state(record, "PreShipping2", page_state)
        ok = all(page_state.values())
        return (ok, "" if ok else "Please fill in all required fields before continuing.")

    if scene == 3:
        page_state = {"approver_name": _normalize_text("approver_name"), "approver_email": _normalize_text("approver_email")}
        _save_page_state(record, "PreShipping3", page_state)
        ok = all(page_state.values())
        return (ok, "" if ok else "Please provide both the POC name and email address.")

    if scene == 4:
        select_state = (record.get("workflow_state") or {}).get("SelectPID") or {}
        surf = bool(select_state.get("confirm_surf"))
        ship_type = _normalize_text("shipping_service_type") or "Domestic"
        page_state = {
            "shipping_service_type": ship_type,
            "hts_code": _normalize_text("hts_code"),
            "shipment_origin": _normalize_text("shipment_origin"),
            "shipment_destination": _normalize_text("shipment_destination"),
            "dimension": _normalize_text("dimension"),
            "weight": _normalize_text("weight"),
        }
        _save_page_state(record, "PreShipping4a", page_state)
        if not page_state["shipment_origin"] or not page_state["shipment_destination"]:
            return (False, "Please complete both shipment origin and shipment destination.")
        if surf:
            if not page_state["dimension"] or not page_state["weight"]:
                return (False, "Please complete dimension and weight for SURF shipments.")
            if ship_type == "International" and not page_state["hts_code"]:
                return (False, "HTS code is required for international shipments.")
        return (True, "")

    if scene == 5:
        select_state = (record.get("workflow_state") or {}).get("SelectPID") or {}
        surf = bool(select_state.get("confirm_surf"))
        page_state = {
            "freight_forwarder": _normalize_text("freight_forwarder"),
            "mode_of_transportation": _normalize_text("mode_of_transportation"),
            "expected_arrival_time": _normalize_datetime_local("expected_arrival_time"),
            "confirm_email_contents": bool((record.get("workflow_state") or {}).get("PreShipping5", {}).get("confirm_email_contents")),
        }
        _save_page_state(record, "PreShipping4b", page_state)
        if surf and (not page_state["freight_forwarder"] or not page_state["mode_of_transportation"] or not page_state["expected_arrival_time"]):
            return (False, "Please fill in all transportation detail fields for SURF shipments.")
        return (True, "")

    if scene == 6:
        select_state = (record.get("workflow_state") or {}).get("SelectPID") or {}
        surf = bool(select_state.get("confirm_surf"))
        existing = (record.get("workflow_state") or {}).get("PreShipping5", {})
        page_state = dict(existing)
        page_state["confirm_email_contents"] = bool(request.form.get("confirm_email_contents"))
        _save_page_state(record, "PreShipping5", page_state)
        if surf and not page_state["confirm_email_contents"]:
            return (False, "Please confirm that you have sent the email before continuing.")
        return (True, "")

    if scene == 7:
        select_state = (record.get("workflow_state") or {}).get("SelectPID") or {}
        surf = bool(select_state.get("confirm_surf"))
        page_state = {
            "received_acknowledgement": bool(request.form.get("received_acknowledgement")),
            "acknowledged_by": _normalize_text("acknowledged_by"),
            "acknowledged_time": _normalize_datetime_local("acknowledged_time"),
            "damage_status": _normalize_text("damage_status") or "no damage",
            "damage_description": _normalize_text("damage_description"),
        }
        _save_page_state(record, "PreShipping6", page_state)
        if surf:
            if not page_state["received_acknowledgement"]:
                return (False, "Please wait for and confirm FD Logistics acknowledgement.")
            if not page_state["acknowledged_by"] or not page_state["acknowledged_time"]:
                return (False, "Please provide acknowledgement name and time.")
        if page_state["damage_status"] == "damage" and not page_state["damage_description"]:
            return (False, "Please describe the visible damage before continuing.")
        return (True, "")

    if scene == 8:
        existing = (record.get("workflow_state") or {}).get("PreShipping7", {})
        page_state = dict(existing)
        page_state["confirm_patch_hwdb"] = bool(request.form.get("confirm_patch_hwdb"))
        _save_page_state(record, "PreShipping7", page_state)
        if not page_state["confirm_patch_hwdb"]:
            return (False, "Please confirm that you are ready to upload the shipping sheet and patch the HWDB.")
        try:
            patch_preshipping_to_hwdb(record)
            save_workflow_progress(record["pid"], record)
        except Exception as exc:
            logger.exception("Failed to patch pre-shipping workflow for %s", record.get("pid"))
            return (False, f"HWDB update failed: {type(exc).__name__}: {exc}")
        return (True, "")

    return (False, "Unsupported scene.")



def _handle_shipping_submit(record: dict, scene: int) -> tuple[bool, str]:
    ws = record.setdefault("workflow_state", {})
    surf = bool((ws.get("SelectPID") or {}).get("confirm_surf"))

    if scene == 1:
        page_state = {"confirm_list": bool(request.form.get("confirm_list"))}
        _save_page_state(record, "Shipping1", page_state)
        return (page_state["confirm_list"], "" if page_state["confirm_list"] else "Please confirm the component list before continuing.")

    if scene == 2:
        existing = dict(ws.get("Shipping2", {}))
        bol_info = _maybe_save_uploaded_file(record, "bol_file", "shipping-bol")
        proforma_info = _maybe_save_uploaded_file(record, "proforma_file", "shipping-proforma")
        if bol_info is not None:
            existing["bol_file"] = bol_info
        if proforma_info is not None:
            existing["proforma_file"] = proforma_info
        _save_page_state(record, "Shipping2", existing)
        if surf:
            ship_type = get_shipping_service_type_from_hwdb(record)
            if not existing.get("bol_file", {}).get("full_filename"):
                return (False, "Please select a Bill of Lading image/PDF file before continuing.")
            if ship_type == "International" and not existing.get("proforma_file", {}).get("full_filename"):
                return (False, "Please select a Proforma Invoice image/PDF file for this international shipment.")
        return (True, "")

    if scene == 3:
        existing = dict(ws.get("Shipping3", {}))
        existing["confirm_email_contents"] = bool(request.form.get("confirm_email_contents"))
        _save_page_state(record, "Shipping3", existing)
        if surf and not existing["confirm_email_contents"]:
            return (False, "Please confirm that you have sent the email before continuing.")
        return (True, "")

    if scene == 4:
        existing = dict(ws.get("Shipping4", {}))
        existing.update({
            "received_approval": bool(request.form.get("received_approval")),
            "approved_by": _normalize_text("approved_by"),
            "approved_time": _normalize_datetime_local("approved_time"),
            "confirm_attached_sheet": bool(request.form.get("confirm_attached_sheet")),
            "confirm_insured": bool(request.form.get("confirm_insured")),
        })
        approval_info = _maybe_save_uploaded_file(record, "approval_file", "shipping-final-approval")
        if approval_info is not None:
            existing["approval_file"] = approval_info
        _save_page_state(record, "Shipping4", existing)
        if surf:
            if not existing.get("received_approval"):
                return (False, "Please wait for and confirm final approval from the FD Logistics team.")
            if not existing.get("approved_by") or not existing.get("approved_time"):
                return (False, "Please provide the final approver name and approval time.")
            if not existing.get("approval_file", {}).get("full_filename"):
                return (False, "Please upload the final approval message image or PDF.")
            if not existing.get("confirm_attached_sheet") or not existing.get("confirm_insured"):
                return (False, "Please confirm that the shipping sheet is attached and the cargo is insured.")
            try:
                patch_shipping_to_hwdb(record)
                save_workflow_progress(record["pid"], record)
            except Exception as exc:
                logger.exception("Failed to patch Shipping checklist for %s", record.get("pid"))
                return (False, f"Shipping HWDB update failed: {type(exc).__name__}: {exc}")
        return (True, "")

    if scene == 5:
        page_state = {
            "shipment_time": _normalize_datetime_local("shipment_time"),
            "comments": _normalize_text("comments"),
            "affirm_shipment": bool(request.form.get("affirm_shipment")),
        }
        _save_page_state(record, "Shipping5", page_state)
        if not page_state["shipment_time"]:
            return (False, "Please provide the shipment date/time before continuing.")
        if not page_state["affirm_shipment"]:
            return (False, "Please confirm that you have shipped the cargo.")
        try:
            update_shipping_location(record)
            save_workflow_progress(record["pid"], record)
        except Exception as exc:
            logger.exception("Failed to update shipment location for %s", record.get("pid"))
            return (False, f"Location update failed: {type(exc).__name__}: {exc}")
        return (True, "")

    if scene == 6:
        existing = dict(ws.get("Shipping6", {}))
        _save_page_state(record, "Shipping6", existing)
        return (True, "")

    return (False, "Unsupported scene.")



def _handle_transit_submit(record: dict, scene: int) -> tuple[bool, str]:
    if scene == 1:
        page_state = {
            "country_code": _normalize_text("country_code"),
            "location_id": _normalize_text("location_id"),
            "arrived": _normalize_datetime_local("arrived"),
            "comments": _normalize_text("comments"),
            "confirm_update": bool(request.form.get("confirm_update")),
        }
        # resolve location label for redisplay
        for opt in get_institution_options():
            if str(opt.get("id")) == str(page_state["location_id"]):
                page_state["location_name"] = opt.get("name") or ""
                page_state["location_display"] = opt.get("label") or ""
                break
        _save_page_state(record, "Transit1", page_state)
        if not page_state["location_id"]:
            return (False, "Please select a location before continuing.")
        if not page_state["arrived"]:
            return (False, "Please provide the date/time before continuing.")
        if not page_state["confirm_update"]:
            return (False, "Please confirm that you want to update the shipment location.")
        try:
            update_transit_location(record)
            save_workflow_progress(record["pid"], record)
        except Exception as exc:
            logger.exception("Failed to update transit location for %s", record.get("pid"))
            return (False, f"Location update failed: {type(exc).__name__}: {exc}")
        return (True, "")
    return (False, "Unsupported scene.")




def _handle_receiving_submit(record: dict, scene: int) -> tuple[bool, str]:
    ws = record.setdefault("workflow_state", {})
    if scene == 1:
        page_state = {"confirm_list": bool(request.form.get("confirm_list"))}
        _save_page_state(record, "Receiving1", page_state)
        return (page_state["confirm_list"], "" if page_state["confirm_list"] else "Please confirm the component list before continuing.")

    if scene == 2:
        page_state = {
            "country_code": _normalize_text("country_code"),
            "location_id": _normalize_text("location_id"),
            "arrived": _normalize_datetime_local("arrived"),
            "comments": _normalize_text("comments"),
            "confirm_update": bool(request.form.get("confirm_update")),
        }
        for opt in get_institution_options():
            if str(opt.get("id")) == str(page_state["location_id"]):
                page_state["location_name"] = opt.get("name") or ""
                page_state["location_display"] = opt.get("label") or ""
                page_state["country_code"] = opt.get("country_code") or page_state["country_code"]
                break
        _save_page_state(record, "Receiving2", page_state)
        if not page_state["location_id"]:
            return (False, "Please select a location before continuing.")
        if not page_state["arrived"]:
            return (False, "Please provide the date/time before continuing.")
        if not page_state["confirm_update"]:
            return (False, "Please confirm that you want to update the shipment location.")
        try:
            update_receiving_location(record)
            save_workflow_progress(record["pid"], record)
        except Exception as exc:
            logger.exception("Failed to update receiving location for %s", record.get("pid"))
            return (False, f"Receiving update failed: {type(exc).__name__}: {exc}")
        return (True, "")

    if scene == 3:
        page_state = {"confirm_email_contents": bool(request.form.get("confirm_email_contents"))}
        _save_page_state(record, "Receiving3", {**ws.get("Receiving3", {}), **page_state})
        return (page_state["confirm_email_contents"], "" if page_state["confirm_email_contents"] else "Please confirm that you have sent the email before continuing.")

    return (False, "Unsupported scene.")


def _render_scene(pid: str, workflow: str, scene: int, record: dict, error: str = "") -> str:
    if workflow == "preshipping":
        if scene == 1:
            return render_preshipping1(pid, record, scene)
        if scene == 2:
            return render_preshipping2(pid, record, scene, error=error)
        if scene == 3:
            return render_preshipping3(pid, record, scene, error=error)
        if scene == 4:
            return render_preshipping4a(pid, record, scene, error=error)
        if scene == 5:
            return render_preshipping4b(pid, record, scene, error=error)
        if scene == 6:
            return render_preshipping5(pid, record, scene)
        if scene == 7:
            return render_preshipping6(pid, record, scene, error=error)
        if scene == 8:
            return render_preshipping7(pid, record, scene, error=error)
        return render_complete(pid, workflow, record)
    if workflow == "shipping":
        if scene == 1:
            return render_shipping1(pid, record, scene)
        if scene == 2:
            return render_shipping2(pid, record, scene, error=error)
        if scene == 3:
            return render_shipping3(pid, record, scene)
        if scene == 4:
            return render_shipping4(pid, record, scene, error=error)
        if scene == 5:
            return render_shipping5(pid, record, scene, error=error)
        if scene == 6:
            return render_shipping6(pid, record, scene)
        return render_complete(pid, workflow, record)
    if workflow == "transit":
        if scene == 1:
            return render_transit1(pid, record, scene, error=error)
        return render_complete(pid, workflow, record)
    if workflow == "receiving":
        if scene == 1:
            return render_receiving1(pid, record, scene)
        if scene == 2:
            return render_receiving2(pid, record, scene, error=error)
        if scene == 3:
            return render_receiving3(pid, record, scene, error=error)
        return render_complete(pid, workflow, record)
    return render_placeholder(pid, workflow)



def register_shipping_workflow_routes(app, lan_mode: bool = False) -> None:
    server = app.server

    @server.get('/shipping-workflow')
    def shipping_workflow_page():
        pid = (request.args.get('pid') or '').strip()
        if not pid:
            return Response("<h2>Missing PID</h2><p>Please launch this page from Shipment Tracker after selecting a shipping box.</p>", mimetype='text/html', status=400)
        try:
            record = _load_or_init_record(pid)

            # Refresh current part/sub-component/location info from the HWDB
            # so the launcher reflects changes made by workflows such as
            # Receiving, which may remove sub-component links.
            try:
                fresh_state = download_part_info(pid, refresh=True)
                if isinstance(fresh_state, dict):
                    if fresh_state.get("part_info") is not None:
                        record["part_info"] = fresh_state.get("part_info") or {}
                        record.setdefault("workflow_state", {})
                        record["workflow_state"]["part_info"] = fresh_state.get("part_info") or {}
                    save_workflow_progress(pid, record)
            except Exception:
                logger.exception("Failed to refresh launcher data from HWDB for %s", pid)

        except Exception as exc:
            logger.exception('Failed to initialize shipping workflow for %s', pid)
            return Response(("<h2>Unable to load shipping workflow</h2>" f"<p>PID: <code>{escape(pid)}</code></p>" f"<p>{escape(type(exc).__name__)}: {escape(str(exc))}</p>"), mimetype='text/html', status=500)
        return Response(render_launcher(pid, record, lan_mode), mimetype='text/html')

    @server.post('/shipping-workflow/start')
    def shipping_workflow_start():
        pid = (request.form.get('pid') or '').strip()
        workflow = (request.form.get('workflow') or '').strip()
        key = (request.form.get('k') or '').strip() or None
        if not pid:
            return redirect('/shipping-workflow')
        record = _load_or_init_record(pid)
        _save_route_choice(record)
        record = _load_or_init_record(pid)
        record['workflow_type'] = workflow
        record['current_scene'] = 1 if workflow in {'preshipping', 'shipping', 'receiving'} else 0
        save_workflow_progress(pid, record)
        if workflow not in {'preshipping', 'shipping', 'receiving'}:
            return redirect('/shipping-workflow?' + base_query(pid, key=key))
        return redirect(_scene_url(pid, workflow, 1, key))

    @server.get('/shipping-workflow/scene')
    def shipping_workflow_scene():
        pid = (request.args.get('pid') or '').strip()
        workflow = (request.args.get('workflow') or '').strip()
        key = (request.args.get('k') or '').strip() or None
        try:
            scene = int(request.args.get('scene') or '1')
        except ValueError:
            scene = 1
        if not pid or not workflow:
            return redirect('/shipping-workflow')
        record = _load_or_init_record(pid)
        record['workflow_type'] = workflow
        record['current_scene'] = scene
        save_workflow_progress(pid, record)
        return Response(_render_scene(pid, workflow, scene, record), mimetype='text/html')

    @server.post('/shipping-workflow/scene')
    def shipping_workflow_scene_post():
        pid = (request.form.get('pid') or '').strip()
        workflow = (request.form.get('workflow') or '').strip()
        key = (request.form.get('k') or '').strip() or None
        try:
            scene = int(request.form.get('scene') or '1')
        except ValueError:
            scene = 1
        if not pid or not workflow:
            return redirect('/shipping-workflow')
        record = _load_or_init_record(pid)
        record['workflow_type'] = workflow
        if workflow == 'preshipping':
            ok, error = _handle_preshipping_submit(record, scene)
        elif workflow == 'shipping':
            ok, error = _handle_shipping_submit(record, scene)
        elif workflow == 'transit':
            ok, error = _handle_transit_submit(record, scene)
        elif workflow == 'receiving':
            ok, error = _handle_receiving_submit(record, scene)
        else:
            ok, error = (False, 'Unsupported workflow.')
        record = _load_or_init_record(pid)
        if not ok:
            record['current_scene'] = scene
            save_workflow_progress(pid, record)
            return Response(_render_scene(pid, workflow, scene, record, error=error), mimetype='text/html')
        next_scene = scene + 1
        record['current_scene'] = next_scene
        save_workflow_progress(pid, record)
        if next_scene > get_scene_count(workflow):
            return Response(render_complete(pid, workflow, record), mimetype='text/html')
        return redirect(_scene_url(pid, workflow, next_scene, key))
