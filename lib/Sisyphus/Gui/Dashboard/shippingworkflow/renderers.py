#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

from html import escape
from typing import Any

from flask import request

from .helpers import generate_preshipping_csv, generate_preshipping_email_html, generate_receiving_email_html, generate_shipping_sheet, generate_shipping_email_html, generate_shipping_csv, get_country_options, get_institution_options, get_location_history_rows, get_preshipping_gate_status, get_shipping_service_type_from_hwdb, is_surf_route, route_label
from .persistence import get_persistence_path
from .workflow_config import WORKFLOWS


def fmt(value: Any, default: str = "—") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


HTML_CSS = """
<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1'/>
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0f2235; --panel: #122940; --panel-2: #16314d; --text: #edf3fb;
      --muted: #b7c7da; --line: rgba(173, 197, 222, 0.35); --accent: #1b84ff;
      --disabled: #5d6d7e; --ok: #3fb950; --warn:#f2b84b;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family: Arial, Helvetica, sans-serif; background: linear-gradient(180deg,#0c1b2d 0%,var(--bg) 100%); color:var(--text); }}
    .page {{ max-width: 1180px; margin:0 auto; padding: 22px 20px 38px; }}
    .topbar {{ display:flex; justify-content:space-between; align-items:center; gap:14px; margin-bottom: 18px; }}
    .brand {{ font-size: 18px; font-weight: 700; }}
    .hero, .card {{ background: rgba(18, 41, 64, 0.94); border:1px solid var(--line); border-radius:18px; box-shadow: 0 10px 28px rgba(0,0,0,0.18); }}
    .hero {{ padding: 22px 24px; margin-bottom: 18px; }}
    .card {{ padding: 18px 18px; }}
    .eyebrow {{ color: var(--muted); font-size: 14px; margin-bottom: 6px; }}
    .pid {{ font-size: 32px; font-weight: 800; margin: 0 0 8px; word-break: break-word; }}
    .subtitle {{ color: var(--muted); font-size: 16px; }}
    .section-title {{ font-size: 18px; font-weight: 800; margin: 0 0 14px; }}
    .meta-grid {{ display:grid; grid-template-columns: 240px 1fr; row-gap: 8px; column-gap: 14px; margin-bottom: 12px; }}
    .meta-key {{ color: var(--muted); font-weight: 700; }}
    .table-wrap {{ border:1px solid var(--line); border-radius:12px; overflow:hidden; margin-top: 12px; }}
    table {{ width:100%; border-collapse: collapse; }}
    thead th {{ background: rgba(122, 153, 186, 0.35); color: #f4f8fd; font-size: 14px; text-align:left; padding: 11px 12px; }}
    tbody td {{ border-top:1px solid rgba(173, 197, 222, 0.18); padding: 10px 12px; font-size: 14px; vertical-align: top; }}
    .grid {{ display:grid; grid-template-columns: 1.2fr 0.8fr; gap: 18px; }}
    .workflow-list {{ display:flex; flex-direction:column; gap: 12px; margin-top: 10px; }}
    .workflow-option {{ display:flex; align-items:flex-start; gap:12px; padding:14px; border:1px solid var(--line); border-radius:14px; cursor:pointer; background: rgba(255,255,255,0.02); }}
    .workflow-option.active {{ border-color: rgba(27,132,255,0.8); background: rgba(27,132,255,0.08); }}
    .workflow-option input {{ position:absolute; opacity:0; pointer-events:none; }}
    .dot {{ width:18px; height:18px; border-radius:50%; border:2px solid #7fa0c4; margin-top:2px; flex:0 0 auto; }}
    .workflow-option.active .dot {{ border-color: var(--accent); box-shadow: inset 0 0 0 4px var(--accent); }}
    .workflow-label {{ font-size: 18px; font-weight: 700; display:block; }}
    .workflow-desc {{ color: var(--muted); font-size: 14px; line-height: 1.35; display:block; margin-top: 4px; }}
    .route-list {{ display:flex; flex-direction:column; gap: 10px; margin-top: 10px; }}
    .route-option {{ display:flex; align-items:flex-start; gap:12px; padding:14px; border:1px solid var(--line); border-radius:14px; cursor:pointer; background: rgba(255,255,255,0.02); }}
    .route-option.active {{ border-color: rgba(242,184,75,0.9); background: rgba(242,184,75,0.10); }}
    .route-label {{ font-size: 16px; font-weight:700; }}
    .route-desc {{ color: var(--muted); font-size: 14px; display:block; margin-top:4px; }}
    .muted {{ color: var(--muted); }}
    .note, .help {{ color: var(--muted); font-size: 14px; line-height: 1.45; }}
    .btnrow {{ display:flex; justify-content:space-between; align-items:center; gap: 10px; margin-top: 18px; }}
    .btn {{ display:inline-flex; align-items:center; justify-content:center; text-decoration:none; border:none; border-radius:10px; padding:11px 16px; font-size:16px; font-weight:600; cursor:pointer; }}
    .btn-back {{ background:#5c6f82; color:#fff; }}
    .btn-next {{ background: var(--accent); color:#fff; }}
    .btn-disabled {{ background: var(--disabled); color:#fff; cursor:not-allowed; opacity:0.75; }}
    .checklist {{ display:flex; flex-direction:column; gap: 16px; margin-top: 6px; }}
    .checkbox-row {{ display:flex; align-items:flex-start; gap: 10px; font-size: 17px; }}
    .checkbox-row input {{ width: 18px; height: 18px; margin-top: 4px; }}
    .field {{ margin-bottom: 20px; }}
    .field label {{ display:block; font-weight:700; margin-bottom: 8px; }}
    .field input, .field textarea, .field select {{ width:100%; border-radius:8px; border:1px solid #46617e; background:#10263b; color:#eef6ff; padding: 11px 12px; font-size:16px; }}
    .field textarea {{ min-height: 140px; resize: vertical; }}
    .fieldset {{ border:1px solid var(--line); border-radius:14px; padding:16px; margin-bottom:18px; }}
    .fieldset legend {{ color:#fff; padding:0 8px; font-weight:700; }}
    .radio-row {{ display:flex; gap:16px; flex-wrap:wrap; margin-top: 10px; }}
    .radio-pill {{ display:flex; align-items:center; gap:8px; padding:10px 12px; border:1px solid var(--line); border-radius:999px; background:rgba(255,255,255,0.02); }}
    .banner {{ margin-top: 14px; padding: 12px 14px; border-radius: 12px; background: rgba(63,185,80,0.10); border:1px solid rgba(63,185,80,0.30); color: #d8f5df; }}
    .warn {{ margin-top: 14px; padding: 12px 14px; border-radius: 12px; background: rgba(242,184,75,0.10); border:1px solid rgba(242,184,75,0.30); color: #ffe8b3; }}
    .error {{ margin-top: 12px; padding: 12px 14px; border-radius: 12px; background: rgba(185,63,80,0.10); border:1px solid rgba(185,63,80,0.30); color: #ffd6dc; }}
    .small {{ font-size: 13px; }}
    .progress {{ display:flex; gap:10px; margin-top:16px; flex-wrap:wrap; }}
    .step {{ border:1px solid var(--line); border-radius:999px; padding:8px 12px; font-size:13px; color:var(--muted); }}
    .step.active {{ color:#fff; border-color:rgba(27,132,255,0.8); background:rgba(27,132,255,0.15); }}
    .step.done {{ color:#d8f5df; border-color:rgba(63,185,80,0.5); background:rgba(63,185,80,0.10); }}
    .html-box {{ border:1px solid var(--line); border-radius:12px; background:#0c2135; padding:14px; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    @media (max-width: 860px) {{ .grid {{ grid-template-columns: 1fr; }} .meta-grid {{ grid-template-columns: 1fr; }} .pid {{ font-size: 28px; }} .topbar {{ flex-wrap: wrap; }} }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def html_page(title: str, body: str) -> str:
    return HTML_CSS.format(title=escape(title), body=body)


def base_query(pid: str, workflow: str | None = None, scene: int | None = None, key: str | None = None) -> str:
    from urllib.parse import urlencode
    q = {"pid": pid}
    if workflow:
        q["workflow"] = workflow
    if scene is not None:
        q["scene"] = str(scene)
    if key:
        q["k"] = key
    return urlencode(q)


def get_back_href(lan_mode: bool) -> str:
    back_href = '/'
    if lan_mode:
        key = (request.args.get('k') or '').strip()
        if key:
            back_href = f"/?k={escape(key)}"
    return back_href


def _part_fields(part_info: dict, pid: str) -> tuple[str, str, str, str]:
    return (
        escape(fmt(part_info.get('part_id'), pid)),
        escape(fmt(part_info.get('part_type_name'))),
        escape(fmt(part_info.get('system_name') or part_info.get('system'))),
        escape(fmt(part_info.get('subsystem_name') or part_info.get('subsystem'))),
    )


def subcomponent_rows(part_info: dict) -> str:
    subcomponents = (part_info or {}).get('subcomponents', {}) or {}
    rows = []
    for _pid, row in sorted(subcomponents.items()):
        rows.append(
            "<tr>"
            f"<td>{escape(fmt(row.get('Sub-component PID')))}</td>"
            f"<td>{escape(fmt(row.get('Component Type Name')))}</td>"
            f"<td>{escape(fmt(row.get('Functional Position Name')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan='3' class='muted'>No linked sub-components were found for this box.</td></tr>")
    return "\n".join(rows)


def workflow_cards(selected: str = "") -> str:
    options = [
        ("preshipping", "Pre-Shipping", "Run the pre-shipping checklist and approvals."),
        ("shipping", "Shipping", "Record the shipment handoff and attached documents."),
        ("receiving", "Receiving", "Confirm receipt and receiving-side checks."),
    ]
    blocks = []
    for value, label, desc in options:
        active = " active" if selected == value else ""
        checked = " checked" if selected == value else ""
        blocks.append(
            f"<label class='workflow-option{active}'>"
            f"<input type='radio' name='workflow' value='{escape(value)}'{checked}/>"
            "<span class='dot'></span>"
            f"<span><span class='workflow-label'>{escape(label)}</span><span class='workflow-desc'>{escape(desc)}</span></span>"
            "</label>"
        )
    return "\n".join(blocks)


def route_cards(select_state: dict) -> str:
    items = [
        ("confirm_surf", "Shipping to SURF", "Shipping directly to the SD warehouse / SURF."),
        ("confirm_non_surf", "Shipping to non-SURF", "Shipping to a place that is not warehouse / SURF."),
        ("confirm_transshipping", "Transshipping to SURF", "Ship first to an intermediate non-SURF location, then later to SURF without opening the box."),
    ]
    blocks = []
    for key, label, desc in items:
        active = " active" if select_state.get(key) else ""
        checked = " checked" if select_state.get(key) else ""
        blocks.append(
            f"<label class='route-option{active}'>"
            f"<input type='radio' name='route_choice' value='{escape(key)}'{checked}/>")
        blocks.append(
            f"<span><span class='route-label'>{escape(label)}</span><span class='route-desc'>{escape(desc)}</span></span></label>"
        )
    return "\n".join(blocks)


def workflow_progress(record: dict, workflow: str, current_scene: int) -> str:
    scenes = WORKFLOWS.get(workflow, {}).get('scenes', [])
    pills = []
    for scene in scenes:
        idx = int(scene.get('index') or 0)
        cls = 'step'
        if idx < current_scene:
            cls += ' done'
        elif idx == current_scene:
            cls += ' active'
        pills.append(f"<span class='{cls}'>{escape(scene.get('short_title') or scene.get('title') or str(idx))}</span>")
    return "<div class='progress'>" + "".join(pills) + "</div>"


def render_launcher(pid: str, record: dict, lan_mode: bool) -> str:
    part_info = record.get('part_info') or {}
    title_pid, type_name, system_name, subsystem_name = _part_fields(part_info, pid)
    back_href = get_back_href(lan_mode)
    selected = (record.get('workflow_type') or '').strip()
    current_scene = int(record.get('current_scene') or 0)
    k = (request.args.get('k') or '').strip() or None
    select_state = (record.get('workflow_state') or {}).get('SelectPID') or {}
    has_route = bool(select_state.get('confirm_surf') or select_state.get('confirm_non_surf') or select_state.get('confirm_transshipping'))
    transit_href = '/shipping-workflow/scene?' + base_query(pid, 'transit', 1, k)

    resume_html = ''
    if selected and current_scene >= 1:
        href = '/shipping-workflow/scene?' + base_query(pid, selected, current_scene, k)
        label = escape(WORKFLOWS.get(selected, {}).get('label', selected))
        resume_html = f"<div class='banner'>Saved progress found for <b>{label}</b>. You can resume from scene {current_scene}. <a style='color:#fff;text-decoration:underline;' href='{escape(href)}'>Resume now</a>.</div>"

    transit_active = " style='border-color: rgba(27,132,255,0.8); box-shadow: inset 0 0 0 1px rgba(27,132,255,0.35);'" if selected == 'transit' else ''

    location_history_rows = get_location_history_rows(pid)
    if location_history_rows:
        rows_html = []
        for row in location_history_rows:
            rows_html.append(
                "<tr>"
                f"<td>{escape(row.get('location', '—'))}</td>"
                f"<td>{escape(row.get('arrived', '—'))}</td>"
                f"<td>{escape(row.get('comments', ''))}</td>"
                "</tr>"
            )
        history_table_html = ''.join(rows_html)
    else:
        history_table_html = "<tr><td colspan='3' class='muted'>No location history was found.</td></tr>"

    body = f"""
  <div class='page'>
    <div class='topbar'>
      <div class='brand'>DUNE Shipping Workflow</div>
      <a class='btn btn-back' href='{escape(back_href)}'>← Back to Dashboard</a>
    </div>
    <section class='hero'>
      <div class='eyebrow'>Workflow launcher</div>
      <h1 class='pid'>{title_pid}</h1>
      <div class='subtitle'>Select the workflow and shipping route for the already selected shipment box.</div>
      {resume_html}
      <div class='banner small'>Progress is saved after every scene to <code>{escape(str(get_persistence_path()))}</code>.</div>
    </section>

    <section class='card' style='margin-bottom:18px;'{transit_active}>
      <h2 class='section-title'>Update location</h2>
      <p class='note'>If you need to update only the location of your shipment.</p>
      <div class='table-wrap' style='margin-top:14px; max-height: 260px; overflow-y: auto; overflow-x: auto;'>
        <table>
          <thead><tr><th>Location</th><th>Arrived</th><th>Comments</th></tr></thead>
          <tbody>{history_table_html}</tbody>
        </table>
      </div>
      <div class='btnrow'>
        <div></div>
        <a class='btn btn-next' href='{escape(transit_href)}'>Continue</a>
      </div>
    </section>

    <form method='post' action='/shipping-workflow/start'>
      <input type='hidden' name='pid' value='{escape(pid)}'/>
      <input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>

      <section class='card' style='margin-bottom:18px;'>
        <h2 class='section-title'>Linked Sub-components</h2>
        <div class='table-wrap'>
          <table>
            <thead><tr><th>Sub-component PID</th><th>Component Type Name</th><th>Functional Position Name</th></tr></thead>
            <tbody>{subcomponent_rows(part_info)}</tbody>
          </table>
        </div>
      </section>

      <section class='card'>
        <h2 class='section-title'>Select Workflow</h2>
        <div class='meta-grid'>
          <div class='meta-key'>PID</div><div>{title_pid}</div>
          <div class='meta-key'>Part Type Name</div><div>{type_name}</div>
          <div class='meta-key'>System</div><div>{system_name}</div>
          <div class='meta-key'>Subsystem</div><div>{subsystem_name}</div>
        </div>
        <div class='workflow-list'>{workflow_cards(selected)}</div>
        <h2 class='section-title' style='margin-top:18px;'>Select Shipping Route</h2>
        <div class='route-list'>{route_cards(select_state)}</div>
        <div class='btnrow'>
          <div></div>
          <button id='continue-btn' type='submit' class='btn {'btn-next' if selected and has_route else 'btn-disabled'}' {'disabled' if not (selected and has_route) else ''}>Continue</button>
        </div>
      </section>
    </form>
  </div>
  <script>
    const wfOptions = document.querySelectorAll('.workflow-option');
    const routeOptions = document.querySelectorAll('.route-option');
    const btn = document.getElementById('continue-btn');
    function refreshSelection() {{
      let hasWorkflow = false;
      let hasRoute = false;
      wfOptions.forEach(el => {{
        const input = el.querySelector('input[type="radio"]');
        const active = !!input.checked;
        el.classList.toggle('active', active);
        if (active) hasWorkflow = true;
      }});
      routeOptions.forEach(el => {{
        const input = el.querySelector('input[type="radio"]');
        const active = !!input.checked;
        el.classList.toggle('active', active);
        if (active) hasRoute = true;
      }});
      const ok = hasWorkflow && hasRoute;
      btn.disabled = !ok;
      btn.className = 'btn ' + (ok ? 'btn-next' : 'btn-disabled');
    }}
    [...wfOptions, ...routeOptions].forEach(el => el.addEventListener('click', refreshSelection));
    refreshSelection();
  </script>
"""
    return html_page('HWDB Shipping Workflow', body)


def render_placeholder(pid: str, workflow: str) -> str:
    label = WORKFLOWS.get(workflow, {}).get('label', workflow)
    back_href = '/shipping-workflow?' + base_query(pid, key=(request.args.get('k') or '').strip() or None)
    body = f"""
    <div class='page'>
      <div class='topbar'>
        <div class='brand'>DUNE Shipping Workflow</div>
        <a class='btn btn-back' href='{escape(back_href)}'>← Back</a>
      </div>
      <section class='hero'>
        <div class='eyebrow'>Placeholder</div>
        <h1 class='pid'>{escape(label)}</h1>
        <div class='subtitle'>This workflow has not been ported yet. Pre-Shipping is the most complete workflow so far.</div>
      </section>
    </div>
    """
    return html_page(f'{label} Placeholder', body)


def _scene_shell(title: str, pid: str, record: dict, scene_index: int, subtitle: str, inner_html: str, workflow: str = 'preshipping') -> str:
    return html_page(title, f"""
    <div class='page'>
      <div class='topbar'>
        <div class='brand'>DUNE Shipping Workflow</div>
        <div class='muted'>{escape(title)}</div>
      </div>
      <section class='hero'>
        <div class='eyebrow'>{escape(title)}</div>
        <h1 class='pid'>{escape(pid)}</h1>
        <div class='subtitle'>{escape(subtitle)}</div>
        {workflow_progress(record, workflow, scene_index)}
      </section>
      {inner_html}
    </div>
    """)


def render_preshipping1(pid: str, record: dict, scene_index: int) -> str:
    ws = record.get('workflow_state') or {}
    page = ws.get('PreShipping1') or {}
    part_info = record.get('part_info') or {}
    gate = get_preshipping_gate_status(record)
    title_pid, type_name, system_name, subsystem_name = _part_fields(part_info, pid)
    back_q = base_query(pid, key=(request.args.get('k') or '').strip() or None)

    checked_list = 'checked' if page.get('confirm_list') else ''
    checked_qaqc = 'checked' if gate.get('qaqc_ready') else ''
    checked_exec = 'checked' if gate.get('executive_summary_found') else ''
    status_name = escape(gate.get('status_name') or '—')
    status_id = gate.get('status_id')
    status_text = f"{status_name}" + (f" (ID={status_id})" if status_id is not None else "")
    certified_text = "✓" if gate.get('certified') else "✗"
    uploaded_text = "✓" if gate.get('uploaded') else "✗"
    exec_name = escape(gate.get('executive_summary_image_name') or 'Not found')
    exec_uploader = escape(gate.get('executive_summary_uploader_name') or '—')

    ok = bool(page.get('confirm_list') and gate.get('qaqc_ready') and gate.get('executive_summary_found'))
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
        <input type='hidden' name='pid' value='{escape(pid)}'/>
        <input type='hidden' name='workflow' value='preshipping'/>
        <input type='hidden' name='scene' value='{scene_index}'/>
        <input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
        <section class='card'>
          <div class='meta-grid'>
            <div class='meta-key'>PID</div><div>{title_pid}</div>
            <div class='meta-key'>Part Type Name</div><div>{type_name}</div>
            <div class='meta-key'>System</div><div>{system_name}</div>
            <div class='meta-key'>Subsystem</div><div>{subsystem_name}</div>
            <div class='meta-key'>Route</div><div>{escape(route_label(record))}</div>
          </div>
          <div class='table-wrap'><table><thead><tr><th>Sub-component PID</th><th>Component Type Name</th><th>Functional Position Name</th></tr></thead><tbody>{subcomponent_rows(part_info)}</tbody></table></div>
        </section>
        <section class='card' style='margin-top:18px;'>
          <h2 class='section-title'>Please affirm the following</h2>
          <div class='checklist'>
            <label class='checkbox-row'><input id='confirm_list' type='checkbox' name='confirm_list' value='1' {checked_list}/> <span>The list of components for this shipment is correct</span></label>
            <div class='checkbox-row'>
              <input type='checkbox' disabled {checked_qaqc}/>
              <span>
                All necessary QA/QC information for these components has been stored in the HWDB
                <div class='help'>Status: {status_text}<br/>Certified: {certified_text}<br/>Uploaded: {uploaded_text}</div>
              </span>
            </div>
            <div class='checkbox-row'>
              <input type='checkbox' disabled {checked_exec}/>
              <span>
                An Executive Summary for this shipment has been found
                <div class='help'>Latest file: {exec_name}<br/>Uploaded by: {exec_uploader}</div>
              </span>
            </div>
          </div>
          <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
        </section>
      </form>
      <script>
      const c1 = document.getElementById('confirm_list');
      const btn = document.getElementById('continue-btn');
      const qaqcReady = {str(bool(gate.get('qaqc_ready'))).lower()};
      const execReady = {str(bool(gate.get('executive_summary_found'))).lower()};
      function refresh() {{ const ok = c1.checked && qaqcReady && execReady; btn.disabled = !ok; btn.className = 'btn ' + (ok ? 'btn-next' : 'btn-disabled'); }}
      c1.addEventListener('change', refresh);
      refresh();
      </script>
    """
    return _scene_shell('Pre-Shipping Workflow (1)', pid, record, scene_index, 'Confirm the selected shipment contents before proceeding.', inner)


def render_preshipping2(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.get('workflow_state') or {}
    page = dict(ws.get('PreShipping2') or {})
    gate = get_preshipping_gate_status(record)
    uploader_name = (gate.get('executive_summary_uploader_name') or '').strip()
    if uploader_name:
        page['qa_rep_name'] = uploader_name
    back_q = base_query(pid, 'preshipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    ok = bool((page.get('qa_rep_name') or '').strip() and (page.get('qa_rep_email') or '').strip() and (page.get('test_info') or '').strip())
    err = f"<div class='error'>{escape(error)}</div>" if error else ''
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
      <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='preshipping'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
      <section class='card'>
        <p class='help'>Provide the name and email address of your Consortium QA Representative who approved this shipment.</p>
        <p class='help'>(For multiple email addresses, separate addresses by commas.)</p>
        <div class='field'><label for='qa_rep_name'>Name</label><input id='qa_rep_name' name='qa_rep_name' type='text' value='{escape(page.get('qa_rep_name',''))}'/></div>
        <div class='field'><label for='qa_rep_email'>Email</label><input id='qa_rep_email' name='qa_rep_email' type='text' value='{escape(page.get('qa_rep_email',''))}'/></div>
        <div class='field'><label for='test_info'>Where can the corresponding QA/QC results be found?</label><textarea id='test_info' name='test_info'>{escape(page.get('test_info',''))}</textarea></div>
        {err}
        <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
      </section></form>
      <script>
      const a=document.getElementById('qa_rep_name'),b=document.getElementById('qa_rep_email'),c=document.getElementById('test_info'),btn=document.getElementById('continue-btn');
      function refresh(){{const ok=a.value.trim()&&b.value.trim()&&c.value.trim();btn.disabled=!ok;btn.className='btn '+(ok?'btn-next':'btn-disabled');}}
      [a,b,c].forEach(el=>el.addEventListener('input',refresh)); refresh();
      </script>
    """
    return _scene_shell('Pre-Shipping Workflow (2)', pid, record, scene_index, 'Provide consortium QA representative contact information and QA/QC reference details.', inner)

def render_preshipping3(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.get('workflow_state') or {}
    page = ws.get('PreShipping3') or {}
    back_q = base_query(pid, 'preshipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    ok = bool((page.get('approver_name') or '').strip() and (page.get('approver_email') or '').strip())
    err = f"<div class='error'>{escape(error)}</div>" if error else ''
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
      <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='preshipping'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
      <section class='card'>
        <p class='help'>Provide the point-of-contact person for this shipment. This POC will also be contacted in case of shipment failure.</p>
        <div class='field'><label for='approver_name'>Name</label><input id='approver_name' name='approver_name' type='text' value='{escape(page.get('approver_name',''))}'/></div>
        <div class='field'><label for='approver_email'>Email</label><input id='approver_email' name='approver_email' type='text' value='{escape(page.get('approver_email',''))}'/></div>
        {err}
        <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
      </section></form>
      <script>
      const a=document.getElementById('approver_name'),b=document.getElementById('approver_email'),btn=document.getElementById('continue-btn');
      function refresh(){{const ok=a.value.trim()&&b.value.trim();btn.disabled=!ok;btn.className='btn '+(ok?'btn-next':'btn-disabled');}}
      [a,b].forEach(el=>el.addEventListener('input',refresh)); refresh();
      </script>
    """
    return _scene_shell('Pre-Shipping Workflow (3)', pid, record, scene_index, 'Provide the point-of-contact information for this shipment.', inner)


def render_preshipping4a(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.get('workflow_state') or {}
    page = ws.get('PreShipping4a') or {}
    back_q = base_query(pid, 'preshipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    surf = is_surf_route(record)
    ship_type = page.get('shipping_service_type', 'Domestic') or 'Domestic'
    ok = bool((page.get('shipment_origin') or '').strip() and (page.get('shipment_destination') or '').strip())
    if surf:
        ok = ok and bool((page.get('dimension') or '').strip() and (page.get('weight') or '').strip())
        if ship_type == 'International':
            ok = ok and bool((page.get('hts_code') or '').strip())
    err = f"<div class='error'>{escape(error)}</div>" if error else ''
    surf_extra = f"""
      <fieldset class='fieldset'><legend>Shipment type</legend><div class='radio-row'>
        <label class='radio-pill'><input type='radio' name='shipping_service_type' value='Domestic' {'checked' if ship_type == 'Domestic' else ''}/> Domestic</label>
        <label class='radio-pill'><input type='radio' name='shipping_service_type' value='International' {'checked' if ship_type == 'International' else ''}/> International</label>
      </div></fieldset>
      <div id='hts-field' class='field' style='{'display:none;' if ship_type != 'International' else ''}'><label for='hts_code'>HTS code</label><input id='hts_code' name='hts_code' type='text' value='{escape(page.get('hts_code',''))}'/></div>
      <div class='field'><label for='dimension'>Dimension</label><input id='dimension' name='dimension' type='text' value='{escape(page.get('dimension',''))}' placeholder='e.g. 30 x 20 x 15 in'/></div>
      <div class='field'><label for='weight'>Weight</label><input id='weight' name='weight' type='text' value='{escape(page.get('weight',''))}' placeholder='e.g. 45 lb'/></div>
    """ if surf else "<div class='warn'>For non-SURF and transshipping routes, only origin and destination are required on this page.</div>"
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
      <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='preshipping'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
      <section class='card'>
        <div class='field'><label for='shipment_origin'>Shipment origin</label><input id='shipment_origin' name='shipment_origin' type='text' value='{escape(page.get('shipment_origin',''))}'/></div>
        <div class='field'><label for='shipment_destination'>Shipment destination</label><input id='shipment_destination' name='shipment_destination' type='text' value='{escape(page.get('shipment_destination',''))}'/></div>
        {surf_extra}
        {err}
        <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
      </section></form>
      <script>
      const routeIsSurf = {str(surf).lower()};
      const typeEls = Array.from(document.querySelectorAll('input[name="shipping_service_type"]'));
      const htsWrap = document.getElementById('hts-field'); const htsEl = document.getElementById('hts_code');
      const originEl = document.getElementById('shipment_origin'); const destEl = document.getElementById('shipment_destination');
      const dimEl = document.getElementById('dimension'); const weightEl = document.getElementById('weight'); const btn = document.getElementById('continue-btn');
      function selectedType(){{const m=typeEls.find(el=>el.checked); return m?m.value:'Domestic';}}
      function refresh(){{let ok=originEl.value.trim().length>0 && destEl.value.trim().length>0; if(routeIsSurf){{ const t=selectedType(); if(htsWrap) htsWrap.style.display = t==='International' ? '' : 'none'; ok = ok && dimEl.value.trim().length>0 && weightEl.value.trim().length>0 && (t!=='International' || htsEl.value.trim().length>0); }} btn.disabled=!ok; btn.className='btn '+(ok?'btn-next':'btn-disabled');}}
      typeEls.forEach(el=>el.addEventListener('change',refresh)); [originEl,destEl,dimEl,weightEl,htsEl].filter(Boolean).forEach(el=>el.addEventListener('input',refresh)); refresh();
      </script>
    """
    return _scene_shell('Pre-Shipping Workflow (4a)', pid, record, scene_index, 'Provide shipment origin, destination, and package details.', inner)


def render_preshipping4b(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.get('workflow_state') or {}
    page = ws.get('PreShipping4b') or {}
    back_q = base_query(pid, 'preshipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    surf = is_surf_route(record)
    ok = True if not surf else bool((page.get('freight_forwarder') or '').strip() and (page.get('mode_of_transportation') or '').strip() and (page.get('expected_arrival_time') or '').strip())
    err = f"<div class='error'>{escape(error)}</div>" if error else ''
    inner_fields = f"""
      <div class='field'><label for='freight_forwarder'>Freight Forwarder name</label><input id='freight_forwarder' name='freight_forwarder' type='text' value='{escape(page.get('freight_forwarder',''))}'/></div>
      <div class='field'><label for='mode_of_transportation'>Mode of Transportation</label><input id='mode_of_transportation' name='mode_of_transportation' type='text' value='{escape(page.get('mode_of_transportation',''))}' placeholder='e.g. Air, Ground, Ocean'/></div>
      <div class='field'><label for='expected_arrival_time'>Expected Arrival Date (CT)</label><input id='expected_arrival_time' name='expected_arrival_time' type='datetime-local' value='{escape(page.get('expected_arrival_time',''))}'/><div class='help'>Choose the Central Time date and time for the expected arrival.</div></div>
    """ if surf else "<div class='warn'>This page is informationally skipped for non-SURF and transshipping routes. Continue to proceed.</div>"
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
      <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='preshipping'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
      <section class='card'>{inner_fields}{err}<div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div></section></form>
      <script>
      const surf = {str(surf).lower()}, a=document.getElementById('freight_forwarder'), b=document.getElementById('mode_of_transportation'), c=document.getElementById('expected_arrival_time'), btn=document.getElementById('continue-btn');
      function refresh(){{const ok=!surf || (a.value.trim()&&b.value.trim()&&c.value.trim()); btn.disabled=!ok; btn.className='btn '+(ok?'btn-next':'btn-disabled');}}
      [a,b,c].filter(Boolean).forEach(el=>el.addEventListener('input',refresh)); refresh();
      </script>
    """
    return _scene_shell('Pre-Shipping Workflow (4b)', pid, record, scene_index, 'Provide transportation and arrival details for this shipment.', inner)


def render_preshipping5(pid: str, record: dict, scene_index: int) -> str:
    ws = record.setdefault('workflow_state', {})
    back_q = base_query(pid, 'preshipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    surf = is_surf_route(record)
    page = ws.setdefault('PreShipping5', {})
    info = generate_preshipping_csv(record)
    page.update(info)
    page['email_contents'] = generate_preshipping_email_html(record)
    ok = bool(page.get('confirm_email_contents')) if surf else True
    confirm_checked = 'checked' if page.get('confirm_email_contents') else ''
    inner_html = f"""
      <form method='post' action='/shipping-workflow/scene'>
      <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='preshipping'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
      <section class='card'>
        <div class='banner'>CSV generated in the Dashboard working directory for this Component Type at <code>{escape(page['csv_full_filename'])}</code>.</div>
        {'<p class="help">Paste the following into an email, attach the CSV file, and send it to the FD Logistics team.</p><div class="html-box">'+ page['email_contents'] + '</div><div class="checklist" style="margin-top:16px;"><label class="checkbox-row"><input id="confirm_email_contents" type="checkbox" name="confirm_email_contents" value="1" '+confirm_checked+'/> <span>I have sent the email</span></label></div>' if surf else '<div class="warn">For non-SURF and transshipping routes, the logistics-request email step is skipped. The CSV is still generated for reference.</div>'}
        <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
      </section></form>
      <script>
      const surf={str(surf).lower()}, box=document.getElementById('confirm_email_contents'), btn=document.getElementById('continue-btn');
      function refresh(){{const ok=!surf || (box && box.checked); btn.disabled=!ok; btn.className='btn '+(ok?'btn-next':'btn-disabled');}} if(box) box.addEventListener('change',refresh); refresh();
      </script>
    """
    return _scene_shell('Pre-Shipping Workflow (5)', pid, record, scene_index, 'Generate the logistics CSV and confirm the email step.', inner_html)


def render_preshipping6(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.get('workflow_state') or {}
    page = ws.get('PreShipping6') or {}
    surf = is_surf_route(record)
    back_q = base_query(pid, 'preshipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    damage_status = page.get('damage_status') or 'no damage'
    ack_checked = 'checked' if page.get('received_acknowledgement') else ''
    ok = damage_status == 'no damage' or bool((page.get('damage_description') or '').strip())
    if surf:
        ok = ok and bool(page.get('received_acknowledgement')) and bool((page.get('acknowledged_by') or '').strip()) and bool((page.get('acknowledged_time') or '').strip())
    err = f"<div class='error'>{escape(error)}</div>" if error else ''
    ack_html = f"""
      <p class='help'>Do not continue until you have received an acknowledgement from the FD Logistics team.</p>
      <div class='checklist'><label class='checkbox-row'><input id='received_acknowledgement' type='checkbox' name='received_acknowledgement' value='1' {ack_checked}/> <span>Yes, I have received an acknowledgement</span></label></div>
      <div class='field'><label for='acknowledged_by'>Acknowledged by whom?</label><input id='acknowledged_by' name='acknowledged_by' type='text' value='{escape(page.get('acknowledged_by',''))}'/></div>
      <div class='field'><label for='acknowledged_time'>When acknowledged (date/time in Central Time)?</label><input id='acknowledged_time' name='acknowledged_time' type='datetime-local' value='{escape(page.get('acknowledged_time',''))}'/><div class='help'>Choose the Central Time date and time when the acknowledgement was received.</div></div>
    """ if surf else "<div class='warn'>FD Logistics acknowledgement is skipped for this route.</div>"
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
      <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='preshipping'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
      <section class='card'>
        {ack_html}
        <fieldset class='fieldset'><legend>Visual inspection</legend>
          <div class='radio-row'>
            <label class='radio-pill'><input type='radio' name='damage_status' value='no damage' {'checked' if damage_status == 'no damage' else ''}/> no damage</label>
            <label class='radio-pill'><input type='radio' name='damage_status' value='damage' {'checked' if damage_status == 'damage' else ''}/> damage</label>
          </div>
          <div id='damage-wrap' class='field' style='margin-top:14px;{'display:none;' if damage_status != 'damage' else ''}'><label for='damage_description'>If there is damage, describe the damage</label><textarea id='damage_description' name='damage_description'>{escape(page.get('damage_description',''))}</textarea></div>
        </fieldset>
        {err}
        <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
      </section></form>
      <script>
      const surf={str(surf).lower()}, ack=document.getElementById('received_acknowledgement'), by=document.getElementById('acknowledged_by'), tm=document.getElementById('acknowledged_time'), dd=document.getElementById('damage_description'), wrap=document.getElementById('damage-wrap'), btn=document.getElementById('continue-btn');
      const radios=Array.from(document.querySelectorAll('input[name="damage_status"]')); function damageVal(){{const m=radios.find(r=>r.checked); return m?m.value:'no damage';}}
      function refresh(){{const d=damageVal(); if(wrap) wrap.style.display = d==='damage' ? '' : 'none'; let ok=(d==='no damage') || (dd && dd.value.trim().length>0); if(surf) ok = ok && ack && ack.checked && by.value.trim().length>0 && tm.value.trim().length>0; btn.disabled=!ok; btn.className='btn '+(ok?'btn-next':'btn-disabled');}}
      [ack,by,tm,dd,...radios].filter(Boolean).forEach(el=>el.addEventListener(el.type==='radio'?'change':'input',refresh)); if(ack) ack.addEventListener('change',refresh); refresh();
      </script>
    """
    return _scene_shell('Pre-Shipping Workflow (6)', pid, record, scene_index, 'Record acknowledgement and perform a visual damage inspection.', inner)


def render_preshipping7(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.setdefault('workflow_state', {})
    back_q = base_query(pid, 'preshipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    info = generate_shipping_sheet(record)
    page = ws.setdefault('PreShipping7', {})
    page.update(info)
    page['confirm_patch_hwdb'] = bool(page.get('confirm_patch_hwdb'))
    err = f"<div class='error'>{escape(error)}</div>" if error else ''
    checked = 'checked' if page.get('confirm_patch_hwdb') else ''
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
      <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='preshipping'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
      <section class='card'>
        <div class='banner'>A shipping label PDF has been created in the Dashboard working directory at <code>{escape(page['pdf_full_filename'])}</code>.</div>
        <p class='help'>Continuing from this page will upload the PDF to the HWDB and patch the <code>Pre-Shipping Checklist</code> specifications for this shipment.</p>
        <div class='checklist'><label class='checkbox-row'><input id='confirm_patch_hwdb' type='checkbox' name='confirm_patch_hwdb' value='1' {checked}/> <span>I am ready to upload the shipping sheet PDF and patch the HWDB</span></label></div>
        {err}
        <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if page.get('confirm_patch_hwdb') else 'btn-disabled'}' {'disabled' if not page.get('confirm_patch_hwdb') else ''}>Continue</button></div>
      </section></form>
      <script>
      const box=document.getElementById('confirm_patch_hwdb'), btn=document.getElementById('continue-btn'); function refresh(){{const ok=box.checked; btn.disabled=!ok; btn.className='btn '+(ok?'btn-next':'btn-disabled');}} box.addEventListener('change',refresh); refresh();
      </script>
    """
    return _scene_shell('Pre-Shipping Workflow (7)', pid, record, scene_index, 'Generate the shipping sheet and prepare the final HWDB update.', inner)



def render_shipping1(pid: str, record: dict, scene_index: int) -> str:
    ws = record.get('workflow_state') or {}
    page = ws.get('Shipping1') or {}
    part_info = record.get('part_info') or {}
    title_pid, type_name, system_name, subsystem_name = _part_fields(part_info, pid)
    back_q = base_query(pid, key=(request.args.get('k') or '').strip() or None)
    checked_list = 'checked' if page.get('confirm_list') else ''
    ok = bool(page.get('confirm_list'))
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
        <input type='hidden' name='pid' value='{escape(pid)}'/>
        <input type='hidden' name='workflow' value='shipping'/>
        <input type='hidden' name='scene' value='{scene_index}'/>
        <input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
        <section class='card'>
          <div class='meta-grid'>
            <div class='meta-key'>PID</div><div>{title_pid}</div>
            <div class='meta-key'>Part Type Name</div><div>{type_name}</div>
            <div class='meta-key'>System</div><div>{system_name}</div>
            <div class='meta-key'>Subsystem</div><div>{subsystem_name}</div>
            <div class='meta-key'>Route</div><div>{escape(route_label(record))}</div>
          </div>
          <div class='table-wrap'><table><thead><tr><th>Sub-component PID</th><th>Component Type Name</th><th>Functional Position Name</th></tr></thead><tbody>{subcomponent_rows(part_info)}</tbody></table></div>
        </section>
        <section class='card' style='margin-top:18px;'>
          <h2 class='section-title'>Please affirm the following</h2>
          <div class='checklist'>
            <label class='checkbox-row'><input id='confirm_list' type='checkbox' name='confirm_list' value='1' {checked_list}/> <span>The list of components for this shipment is correct</span></label>
          </div>
          <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
        </section>
      </form>
      <script>
      const c1 = document.getElementById('confirm_list'); const btn = document.getElementById('continue-btn');
      function refresh() {{ const ok = c1.checked; btn.disabled = !ok; btn.className = 'btn ' + (ok ? 'btn-next' : 'btn-disabled'); }}
      c1.addEventListener('change', refresh); refresh();
      </script>
    """
    return _scene_shell('Shipping Workflow (1)', pid, record, scene_index, 'Confirm the selected shipment contents before proceeding.', inner, workflow='shipping')



def render_shipping2(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.get('workflow_state') or {}
    page = ws.get('Shipping2') or {}
    back_q = base_query(pid, 'shipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    surf = is_surf_route(record)
    ship_type = get_shipping_service_type_from_hwdb(record)
    bol_name = escape(page.get('bol_file', {}).get('filename', ''))
    proforma_name = escape(page.get('proforma_file', {}).get('filename', ''))
    has_bol = bool(page.get('bol_file', {}).get('full_filename'))
    has_proforma = bool(page.get('proforma_file', {}).get('full_filename'))
    proforma_required = surf and ship_type == 'International'
    ok = True if not surf else has_bol and (not proforma_required or has_proforma)
    err = f"<div class='error'>{escape(error)}</div>" if error else ''

    if surf:
        bol_html = (
            '<p class="help">If your shipping department interacts with the freight forwarder on your behalf, make sure they follow the procedure below.</p>'
            '<p class="help">For this Bill of Lading (BoL), request your carrier to employ a type such as "Through Seaway BoL" or "Through BoL with an express release". Request them to include the shipment PID and Component Type Name.</p>'
            '<div class="field"><label for="bol_file">Select Bill of Lading image/PDF file</label>'
            '<input id="bol_file" name="bol_file" type="file" accept=".pdf,.png,.jpg,.jpeg"/>'
            + (f'<div class="help">Currently selected: <code>{bol_name}</code></div>' if bol_name else '')
            + '</div>'
        )
        if proforma_required:
            proforma_html = (
                '<div class="field"><label for="proforma_file">Select Proforma Invoice image/PDF file</label>'
                '<input id="proforma_file" name="proforma_file" type="file" accept=".pdf,.png,.jpg,.jpeg"/>'
                + (f'<div class="help">Currently selected: <code>{proforma_name}</code></div>' if proforma_name else '')
                + '<div class="help">This shipment is <b>International</b> based on the HWDB Pre-Shipping checklist, so Proforma Invoice upload is required.</div></div>'
            )
        else:
            proforma_html = (
                '<div class="field"><label for="proforma_file">Select Proforma Invoice image/PDF file</label>'
                '<input id="proforma_file" name="proforma_file" type="file" accept=".pdf,.png,.jpg,.jpeg" disabled/>'
                + (f'<div class="help">Previously selected: <code>{proforma_name}</code></div>' if proforma_name else '')
                + '<div class="help">This shipment is <b>Domestic</b> based on the HWDB Pre-Shipping checklist (HTS code is empty), so Proforma Invoice upload is not required.</div></div>'
            )
        route_html = (
            f'<div class="banner">Shipping type resolved from the HWDB Pre-Shipping checklist: <b>{escape(ship_type)}</b>.</div>'
            + bol_html
            + proforma_html
            + '<p class="help">Click Continue to keep the selected document(s) locally for this workflow. They will be uploaded to the HWDB at the final Shipping approval step.</p>'
        )
    else:
        route_html = '<div class="warn">For non-SURF and transshipping routes, BoL / proforma upload is skipped.</div>'

    inner = f"""
      <form method='post' action='/shipping-workflow/scene' enctype='multipart/form-data'>
        <input type='hidden' name='pid' value='{escape(pid)}'/>
        <input type='hidden' name='workflow' value='shipping'/>
        <input type='hidden' name='scene' value='{scene_index}'/>
        <input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
        <section class='card'>
          {route_html}
          {err}
          <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
        </section>
      </form>
      <script>
        const surf = {str(surf).lower()};
        const proformaRequired = {str(proforma_required).lower()};
        const hasExistingBol = {str(has_bol).lower()};
        const hasExistingProforma = {str(has_proforma).lower()};
        const bolFile = document.getElementById('bol_file');
        const proformaFile = document.getElementById('proforma_file');
        const btn = document.getElementById('continue-btn');

        function refreshShipping2() {{
          let ok = true;
          if (surf) {{
            const bolReady = hasExistingBol || (bolFile && bolFile.files && bolFile.files.length > 0);
            const proformaReady = (!proformaRequired) || hasExistingProforma || (proformaFile && proformaFile.files && proformaFile.files.length > 0);
            ok = !!bolReady && !!proformaReady;
          }}
          btn.disabled = !ok;
          btn.className = 'btn ' + (ok ? 'btn-next' : 'btn-disabled');
        }}

        if (bolFile) bolFile.addEventListener('change', refreshShipping2);
        if (proformaFile) proformaFile.addEventListener('change', refreshShipping2);
        refreshShipping2();
      </script>
    """
    return _scene_shell('Shipping Workflow (2)', pid, record, scene_index, 'Select shipping documentation for this shipment.', inner, workflow='shipping')



def render_shipping3(pid: str, record: dict, scene_index: int) -> str:
    ws = record.setdefault('workflow_state', {})
    back_q = base_query(pid, 'shipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    surf = is_surf_route(record)
    page = ws.setdefault('Shipping3', {})
    page['email_contents'] = generate_shipping_email_html(record)
    ok = bool(page.get('confirm_email_contents')) if surf else True
    confirm_checked = 'checked' if page.get('confirm_email_contents') else ''
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
        <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='shipping'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
        <section class='card'>
          {'<p class="help">Paste the following into an email, attach the BoL and Proforma Invoice (if applicable), and send it to the FD Logistics team.</p><div class="html-box">'+ page['email_contents'] + '</div><div class="checklist" style="margin-top:16px;"><label class="checkbox-row"><input id="confirm_email_contents" type="checkbox" name="confirm_email_contents" value="1" '+confirm_checked+'/> <span>I have sent the email</span></label></div>' if surf else '<div class="warn">For non-SURF and transshipping routes, the final-approval email step is skipped.</div>'}
          <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
        </section>
      </form>
      <script>
      const surf={str(surf).lower()}, box=document.getElementById('confirm_email_contents'), btn=document.getElementById('continue-btn');
      function refresh(){{const ok=!surf || (box && box.checked); btn.disabled=!ok; btn.className='btn '+(ok?'btn-next':'btn-disabled');}} if(box) box.addEventListener('change',refresh); refresh();
      </script>
    """
    return _scene_shell('Shipping Workflow (3)', pid, record, scene_index, 'Prepare the final-approval email for FD Logistics.', inner, workflow='shipping')


def render_shipping4(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.get('workflow_state') or {}
    page = ws.get('Shipping4') or {}
    surf = is_surf_route(record)
    back_q = base_query(pid, 'shipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    approval_name = escape(page.get('approval_file', {}).get('filename', ''))
    ok = True if not surf else bool(page.get('received_approval')) and bool((page.get('approved_by') or '').strip()) and bool((page.get('approved_time') or '').strip()) and bool(page.get('approval_file', {}).get('full_filename')) and bool(page.get('confirm_attached_sheet')) and bool(page.get('confirm_insured'))
    err = f"<div class='error'>{escape(error)}</div>" if error else ''
    inner = f"""
      <form method='post' action='/shipping-workflow/scene' enctype='multipart/form-data'>
      <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='shipping'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
      <section class='card'>
        {'<p class="help">Do not continue until you have received an approval from the FD Logistics team.</p><div class="checklist"><label class="checkbox-row"><input id="received_approval" type="checkbox" name="received_approval" value="1" ' + ('checked' if page.get('received_approval') else '') + '/> <span>Yes, I have received an approval</span></label></div><div class="field"><label for="approved_by">Approved by whom?</label><input id="approved_by" name="approved_by" type="text" value="' + escape(page.get('approved_by','')) + '"/></div><div class="field"><label for="approved_time">When approved (date/time in Central Time)?</label><input id="approved_time" name="approved_time" type="datetime-local" value="' + escape(page.get('approved_time','')) + '"/></div><div class="field"><label for="approval_file">Upload photo or screenshot of the approved message</label><input id="approval_file" name="approval_file" type="file" accept=".pdf,.png,.jpg,.jpeg"/>' + (f'<div class="help">Currently selected: <code>{approval_name}</code></div>' if approval_name else '') + '</div><div class="checklist"><label class="checkbox-row"><input id="confirm_attached_sheet" type="checkbox" name="confirm_attached_sheet" value="1" ' + ('checked' if page.get('confirm_attached_sheet') else '') + '/> <span>The DUNE Shipping Sheet has been securely attached to the shipment</span></label><label class="checkbox-row"><input id="confirm_insured" type="checkbox" name="confirm_insured" value="1" ' + ('checked' if page.get('confirm_insured') else '') + '/> <span>The cargo has been adequately insured for transit</span></label></div><p class="help">Click Continue to keep the selected approval image locally for this workflow. It will be uploaded to the HWDB at the final Shipping approval step.</p>' if surf else '<div class="warn">For non-SURF and transshipping routes, FD Logistics approval/image upload is skipped.</div>'}
        {err}
        <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
      </section></form>
      <script>
      const surf={str(surf).lower()}, received=document.getElementById('received_approval'), by=document.getElementById('approved_by'), tm=document.getElementById('approved_time'), sheet=document.getElementById('confirm_attached_sheet'), ins=document.getElementById('confirm_insured'), file=document.getElementById('approval_file'), btn=document.getElementById('continue-btn');
      function refresh(){{let ok=!surf; if(surf){{const hasExisting={str(bool(page.get('approval_file', {}).get('full_filename'))).lower()}; const hasNew=file && file.files && file.files.length>0; ok=received&&received.checked&&by.value.trim().length>0&&tm.value.trim().length>0&&sheet.checked&&ins.checked&&(hasExisting||hasNew);}} btn.disabled=!ok; btn.className='btn '+(ok?'btn-next':'btn-disabled');}}
      [received,by,tm,sheet,ins,file].filter(Boolean).forEach(el=>el.addEventListener(el.type==='checkbox'?'change':'input',refresh)); if(file) file.addEventListener('change',refresh); refresh();
      </script>
    """
    return _scene_shell('Shipping Workflow (4)', pid, record, scene_index, 'Record final approval details and supporting evidence.', inner, workflow='shipping')


def render_shipping5(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.get('workflow_state') or {}
    page = ws.get('Shipping5') or {}
    back_q = base_query(pid, 'shipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    ok = bool((page.get('shipment_time') or '').strip() and page.get('affirm_shipment'))
    err = f"<div class='error'>{escape(error)}</div>" if error else ''
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
      <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='shipping'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
      <section class='card'>
        <p class='help'>The location will be posted as <b>In-Transit</b>.</p>
        <div class='field'><label>Location</label><input type='text' value='In-Transit' disabled/></div>
        <div class='field'><label for='shipment_time'>Date/Time (Central Time)</label><input id='shipment_time' name='shipment_time' type='datetime-local' value='{escape(page.get('shipment_time',''))}'/></div>
        <div class='field'><label for='comments'>Comments</label><input id='comments' name='comments' type='text' value='{escape(page.get('comments',''))}'/></div>
        <div class='checklist'><label class='checkbox-row'><input id='affirm_shipment' type='checkbox' name='affirm_shipment' value='1' {'checked' if page.get('affirm_shipment') else ''}/> <span>I have shipped the cargo</span></label></div>
        {err}
        <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
      </section></form>
      <script>
      const tm=document.getElementById('shipment_time'), box=document.getElementById('affirm_shipment'), btn=document.getElementById('continue-btn');
      function refresh(){{const ok=tm.value.trim().length>0 && box.checked; btn.disabled=!ok; btn.className='btn '+(ok?'btn-next':'btn-disabled');}}
      [tm,box].forEach(el=>el.addEventListener(el.type==='checkbox'?'change':'input',refresh)); refresh();
      </script>
    """
    return _scene_shell('Shipping Workflow (5)', pid, record, scene_index, 'Post the shipment as in-transit and confirm shipment handoff.', inner, workflow='shipping')


def render_shipping6(pid: str, record: dict, scene_index: int) -> str:
    ws = record.setdefault('workflow_state', {})
    back_q = base_query(pid, 'shipping', scene_index - 1, (request.args.get('k') or '').strip() or None)
    page = ws.setdefault('Shipping6', {})
    info = generate_shipping_csv(record)
    page.update(info)
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
      <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='shipping'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
      <section class='card'>
        <div class='banner'>A shipping CSV has been generated at <code>{escape(page['csv_full_filename'])}</code>.</div>
        <p class='help'>(Optional) You may wish to email it and other documents to your collaborators for reference.</p>
        <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn btn-next'>Continue</button></div>
      </section></form>
    """
    return _scene_shell('Shipping Workflow (6)', pid, record, scene_index, 'Generate the shipping CSV and wrap up the Shipping checklist.', inner, workflow='shipping')




def render_transit1(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.setdefault('workflow_state', {})
    page = ws.get('Transit1') or {}
    back_q = base_query(pid, key=(request.args.get('k') or '').strip() or None)

    institution_options = get_institution_options()
    country_options = get_country_options()
    history_rows = get_location_history_rows(pid)

    selected_country = str(page.get('country_code', '') or '')
    selected_location_id = str(page.get('location_id', '') or '')

    if not selected_country and selected_location_id:
        for opt in institution_options:
            if str(opt.get('id')) == selected_location_id:
                selected_country = str(opt.get('country_code') or '')
                break

    country_html = []
    for opt in country_options:
        code = str(opt.get('code') or '')
        selected = ' selected' if code == selected_country else ''
        country_html.append(f"<option value='{escape(code)}'{selected}>{escape(opt.get('label', code))}</option>")

    institution_by_country = {}
    for opt in institution_options:
        code = str(opt.get('country_code') or '')
        institution_by_country.setdefault(code, []).append({
            "id": str(opt.get("id") or ""),
            "label": str(opt.get("label") or ""),
        })

    institution_html = []
    for opt in institution_options:
        code = str(opt.get('country_code') or '')
        selected = ' selected' if str(opt.get('id')) == selected_location_id else ''
        institution_html.append(
            f"<option value='{escape(str(opt.get('id') or ''))}' data-country='{escape(code)}'{selected}>{escape(str(opt.get('label') or ''))}</option>"
        )

    history_table = "<tr><td colspan='3' class='muted'>No location history was found.</td></tr>"
    if history_rows:
        row_html = []
        for row in history_rows:
            row_html.append(
                "<tr>"
                f"<td>{escape(row.get('location', '—'))}</td>"
                f"<td>{escape(row.get('arrived', '—'))}</td>"
                f"<td>{escape(row.get('comments', ''))}</td>"
                "</tr>"
            )
        history_table = "".join(row_html)

    err = f"<div class='error'>{escape(error)}</div>" if error else ""
    ok = bool(selected_location_id and (page.get('arrived') or '').strip() and page.get('confirm_update'))

    current_loc = page.get('location_name') or page.get('location_display') or 'Not set in this workflow yet'
    posted_at = page.get('location_posted_at', '')

    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
        <input type='hidden' name='pid' value='{escape(pid)}'/>
        <input type='hidden' name='workflow' value='transit'/>
        <input type='hidden' name='scene' value='{scene_index}'/>
        <input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
        <section class='card'>
          <div class='meta-grid'>
            <div class='meta-key'>PID</div><div>{escape(pid)}</div>
            <div class='meta-key'>Current workflow label</div><div>Updating Location</div>
            <div class='meta-key'>Last selected location</div><div>{escape(current_loc)}</div>
            <div class='meta-key'>Last posted at</div><div>{escape(posted_at or '—')}</div>
          </div>

          <h2 class='section-title'>Location History</h2>
          <div class='table-wrap' style='max-height: 260px; overflow-y: auto; overflow-x: auto;'>
            <table>
              <thead><tr><th>Location</th><th>Arrived</th><th>Comments</th></tr></thead>
              <tbody>{history_table}</tbody>
            </table>
          </div>

          <p class='help' style='margin-top:18px;'>Please update the Location record for this shipment.</p>

          <div class='grid' style='grid-template-columns: 0.6fr 1.4fr; gap:16px;'>
            <div class='field'>
              <label for='country_code'>Select Country</label>
              <select id='country_code' name='country_code'>
                <option value=''>Select Country...</option>
                {''.join(country_html)}
              </select>
            </div>
            <div class='field'>
              <label for='location_id'>Select Institution</label>
              <select id='location_id' name='location_id'>
                <option value=''>Select Institution...</option>
                {''.join(institution_html)}
              </select>
            </div>
          </div>

          <div class='field'>
            <label for='arrived'>Date/Time (Central Time)</label>
            <input id='arrived' name='arrived' type='datetime-local' value='{escape(page.get('arrived',''))}'/>
          </div>
          <div class='field'>
            <label for='comments'>Comments</label>
            <input id='comments' name='comments' type='text' value='{escape(page.get('comments',''))}'/>
          </div>
          <div class='checklist'>
            <label class='checkbox-row'><input id='confirm_update' type='checkbox' name='confirm_update' value='1' {'checked' if page.get('confirm_update') else ''}/> <span>I want to update the shipment location</span></label>
          </div>
          {err}
          <div class='btnrow'>
            <a class='btn btn-back' href='/shipping-workflow?{escape(back_q)}'>Back</a>
            <button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button>
          </div>
        </section>
      </form>
      <script>
        const countryEl = document.getElementById('country_code');
        const locEl = document.getElementById('location_id');
        const timeEl = document.getElementById('arrived');
        const boxEl = document.getElementById('confirm_update');
        const btn = document.getElementById('continue-btn');

        function filterInstitutions() {{
          const selectedCountry = countryEl.value;
          let hasSelectedVisible = false;
          Array.from(locEl.options).forEach((opt, idx) => {{
            if (idx === 0) return;
            const country = opt.getAttribute('data-country') || '';
            const visible = !selectedCountry || country === selectedCountry;
            opt.hidden = !visible;
            if (!visible && opt.selected) {{
              opt.selected = false;
            }}
            if (visible && opt.selected) {{
              hasSelectedVisible = true;
            }}
          }});
          if (!hasSelectedVisible && locEl.selectedIndex > 0) {{
            locEl.value = '';
          }}
        }}

        function refreshTransit() {{
          const ok = locEl.value.trim().length > 0 && timeEl.value.trim().length > 0 && boxEl.checked;
          btn.disabled = !ok;
          btn.className = 'btn ' + (ok ? 'btn-next' : 'btn-disabled');
        }}

        countryEl.addEventListener('change', () => {{
          filterInstitutions();
          refreshTransit();
        }});
        locEl.addEventListener('change', refreshTransit);
        timeEl.addEventListener('input', refreshTransit);
        boxEl.addEventListener('change', refreshTransit);

        filterInstitutions();
        refreshTransit();
      </script>
    """
    return _scene_shell('Updating Location', pid, record, scene_index, 'Update only the location of your shipment.', inner, workflow='transit')





def render_receiving1(pid: str, record: dict, scene_index: int) -> str:
    ws = record.get('workflow_state') or {}
    page = ws.get('Receiving1') or {}
    part_info = record.get('part_info') or {}
    title_pid, type_name, system_name, subsystem_name = _part_fields(part_info, pid)
    back_q = base_query(pid, key=(request.args.get('k') or '').strip() or None)
    checked_list = 'checked' if page.get('confirm_list') else ''
    transshipping = bool((ws.get('SelectPID') or {}).get('confirm_transshipping'))
    n_children = len((part_info or {}).get('subcomponents', {}) or {})
    warn_html = ""
    if n_children and not transshipping:
        warn_html = f"<div class='error'>Warning: continuing through Receiving will remove all {n_children} sub-component links from this shipping box.</div>"
    ok = bool(page.get('confirm_list'))
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
        <input type='hidden' name='pid' value='{escape(pid)}'/>
        <input type='hidden' name='workflow' value='receiving'/>
        <input type='hidden' name='scene' value='{scene_index}'/>
        <input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
        <section class='card'>
          <div class='meta-grid'>
            <div class='meta-key'>PID</div><div>{title_pid}</div>
            <div class='meta-key'>Part Type Name</div><div>{type_name}</div>
            <div class='meta-key'>System</div><div>{system_name}</div>
            <div class='meta-key'>Subsystem</div><div>{subsystem_name}</div>
            <div class='meta-key'>Route</div><div>{escape(route_label(record))}</div>
          </div>
          <div class='table-wrap'><table><thead><tr><th>Sub-component PID</th><th>Component Type Name</th><th>Functional Position Name</th></tr></thead><tbody>{subcomponent_rows(part_info)}</tbody></table></div>
        </section>
        <section class='card' style='margin-top:18px;'>
          <h2 class='section-title'>Please affirm the following</h2>
          {warn_html}
          <div class='checklist'>
            <label class='checkbox-row'><input id='confirm_list' type='checkbox' name='confirm_list' value='1' {checked_list}/> <span>The list of components for this received shipment is correct</span></label>
          </div>
          <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
        </section>
      </form>
      <script>
      const c1 = document.getElementById('confirm_list'); const btn = document.getElementById('continue-btn');
      function refresh() {{ const ok = c1.checked; btn.disabled = !ok; btn.className = 'btn ' + (ok ? 'btn-next' : 'btn-disabled'); }}
      c1.addEventListener('change', refresh); refresh();
      </script>
    """
    return _scene_shell('Receiving Workflow (1)', pid, record, scene_index, 'Confirm the received shipment contents before proceeding.', inner, workflow='receiving')


def render_receiving2(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.setdefault('workflow_state', {})
    page = ws.get('Receiving2') or {}
    back_q = base_query(pid, 'receiving', scene_index - 1, (request.args.get('k') or '').strip() or None)

    institution_options = get_institution_options()
    country_options = get_country_options()
    history_rows = get_location_history_rows(pid)

    selected_country = str(page.get('country_code', '') or '')
    selected_location_id = str(page.get('location_id', '') or '')

    if not selected_country and selected_location_id:
        for opt in institution_options:
            if str(opt.get('id')) == selected_location_id:
                selected_country = str(opt.get('country_code') or '')
                break

    country_html = []
    for opt in country_options:
        code = str(opt.get('code') or '')
        selected = ' selected' if code == selected_country else ''
        country_html.append(f"<option value='{escape(code)}'{selected}>{escape(opt.get('label', code))}</option>")

    institution_html = []
    for opt in institution_options:
        code = str(opt.get('country_code') or '')
        selected = ' selected' if str(opt.get('id')) == selected_location_id else ''
        institution_html.append(
            f"<option value='{escape(str(opt.get('id') or ''))}' data-country='{escape(code)}'{selected}>{escape(str(opt.get('label') or ''))}</option>"
        )

    history_table = "<tr><td colspan='3' class='muted'>No location history was found.</td></tr>"
    if history_rows:
        row_html = []
        for row in history_rows:
            row_html.append(
                "<tr>"
                f"<td>{escape(row.get('location', '—'))}</td>"
                f"<td>{escape(row.get('arrived', '—'))}</td>"
                f"<td>{escape(row.get('comments', ''))}</td>"
                "</tr>"
            )
        history_table = "".join(row_html)

    transshipping = bool((ws.get('SelectPID') or {}).get('confirm_transshipping'))
    n_children = len((record.get('part_info') or {}).get('subcomponents', {}) or {})
    warning = ""
    if n_children and not transshipping:
        warning = f"<div class='error'>Warning: continuing from this page will remove all {n_children} sub-component links to the PID of your shipping box.</div>"
    elif transshipping:
        warning = "<div class='banner'>Transshipping route detected: only the box location will be updated. Sub-component links will be kept.</div>"

    err = f"<div class='error'>{escape(error)}</div>" if error else ""
    ok = bool(selected_location_id and (page.get('arrived') or '').strip() and page.get('confirm_update'))

    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
        <input type='hidden' name='pid' value='{escape(pid)}'/>
        <input type='hidden' name='workflow' value='receiving'/>
        <input type='hidden' name='scene' value='{scene_index}'/>
        <input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
        <section class='card'>
          <h2 class='section-title'>Location History</h2>
          <div class='table-wrap' style='max-height: 260px; overflow-y: auto; overflow-x: auto;'>
            <table>
              <thead><tr><th>Location</th><th>Arrived</th><th>Comments</th></tr></thead>
              <tbody>{history_table}</tbody>
            </table>
          </div>
          <p class='help' style='margin-top:18px;'>Please update the Location record for this shipment.</p>
          {warning}
          <div class='grid' style='grid-template-columns: 0.6fr 1.4fr; gap:16px;'>
            <div class='field'>
              <label for='country_code'>Select Country</label>
              <select id='country_code' name='country_code'>
                <option value=''>Select Country...</option>
                {''.join(country_html)}
              </select>
            </div>
            <div class='field'>
              <label for='location_id'>Select Institution</label>
              <select id='location_id' name='location_id'>
                <option value=''>Select Institution...</option>
                {''.join(institution_html)}
              </select>
            </div>
          </div>
          <div class='field'>
            <label for='arrived'>Date/Time (Central Time)</label>
            <input id='arrived' name='arrived' type='datetime-local' value='{escape(page.get('arrived',''))}'/>
          </div>
          <div class='field'>
            <label for='comments'>Comments</label>
            <input id='comments' name='comments' type='text' value='{escape(page.get('comments',''))}'/>
          </div>
          <div class='checklist'>
            <label class='checkbox-row'><input id='confirm_update' type='checkbox' name='confirm_update' value='1' {'checked' if page.get('confirm_update') else ''}/> <span>Yes, update the location now</span></label>
          </div>
          {err}
          <div class='btnrow'>
            <a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a>
            <button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button>
          </div>
        </section>
      </form>
      <script>
        const countryEl = document.getElementById('country_code');
        const locEl = document.getElementById('location_id');
        const timeEl = document.getElementById('arrived');
        const boxEl = document.getElementById('confirm_update');
        const btn = document.getElementById('continue-btn');

        function filterInstitutions() {{
          const selectedCountry = countryEl.value;
          let hasSelectedVisible = false;
          Array.from(locEl.options).forEach((opt, idx) => {{
            if (idx === 0) return;
            const country = opt.getAttribute('data-country') || '';
            const visible = !selectedCountry || country === selectedCountry;
            opt.hidden = !visible;
            if (!visible && opt.selected) opt.selected = false;
            if (visible && opt.selected) hasSelectedVisible = true;
          }});
          if (!hasSelectedVisible && locEl.selectedIndex > 0) locEl.value = '';
        }}

        function refreshReceiving() {{
          const ok = locEl.value.trim().length > 0 && timeEl.value.trim().length > 0 && boxEl.checked;
          btn.disabled = !ok;
          btn.className = 'btn ' + (ok ? 'btn-next' : 'btn-disabled');
        }}

        countryEl.addEventListener('change', () => {{ filterInstitutions(); refreshReceiving(); }});
        locEl.addEventListener('change', refreshReceiving);
        timeEl.addEventListener('input', refreshReceiving);
        boxEl.addEventListener('change', refreshReceiving);

        filterInstitutions();
        refreshReceiving();
      </script>
    """
    return _scene_shell('Receiving Workflow (2)', pid, record, scene_index, 'Update the location of the received shipment.', inner, workflow='receiving')


def render_receiving3(pid: str, record: dict, scene_index: int, error: str = '') -> str:
    ws = record.setdefault('workflow_state', {})
    page = ws.setdefault('Receiving3', {})
    back_q = base_query(pid, 'receiving', scene_index - 1, (request.args.get('k') or '').strip() or None)
    page['email_contents'] = generate_receiving_email_html(record)
    confirm_checked = 'checked' if page.get('confirm_email_contents') else ''
    ok = bool(page.get('confirm_email_contents'))
    result = ws.get('ReceivingResult') or {}
    unlink_failures = result.get('subcomponents_unlink_failures') or []
    warning = ""
    if unlink_failures:
        warning = "<div class='error'>Warning: one or more sub-component links may not have been removed automatically. Please verify in the HWDB.</div>"
    inner = f"""
      <form method='post' action='/shipping-workflow/scene'>
        <input type='hidden' name='pid' value='{escape(pid)}'/><input type='hidden' name='workflow' value='receiving'/><input type='hidden' name='scene' value='{scene_index}'/><input type='hidden' name='k' value='{escape((request.args.get('k') or '').strip())}'/>
        <section class='card'>
          <p class='help'>Paste the following into an email to notify the POC that the shipment has been received.</p>
          {warning}
          <div class='html-box'>{page['email_contents']}</div>
          <div class='checklist' style='margin-top:16px;'>
            <label class='checkbox-row'><input id='confirm_email_contents' type='checkbox' name='confirm_email_contents' value='1' {confirm_checked}/> <span>I have sent the email</span></label>
          </div>
          <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow/scene?{escape(back_q)}'>Back</a><button id='continue-btn' type='submit' class='btn {'btn-next' if ok else 'btn-disabled'}' {'disabled' if not ok else ''}>Continue</button></div>
        </section>
      </form>
      <script>
        const box = document.getElementById('confirm_email_contents'); const btn = document.getElementById('continue-btn');
        function refresh() {{ const ok = box.checked; btn.disabled = !ok; btn.className = 'btn ' + (ok ? 'btn-next' : 'btn-disabled'); }}
        box.addEventListener('change', refresh); refresh();
      </script>
    """
    return _scene_shell('Receiving Workflow (3)', pid, record, scene_index, 'Notify the POC that the shipment has been received.', inner, workflow='receiving')


def render_complete(pid: str, workflow: str, record: dict | None = None) -> str:
    label = WORKFLOWS.get(workflow, {}).get('label', workflow)
    launcher_q = base_query(pid, key=(request.args.get('k') or '').strip() or None)
    route = route_label(record or {}) if record else 'n/a'
    body = f"""
    <div class='page'>
      <div class='topbar'><div class='brand'>DUNE Shipping Workflow</div><div class='muted'>{escape(label)} complete</div></div>
      <section class='hero'>
        <div class='eyebrow'>Current phase complete</div>
        <h1 class='pid'>{escape(label)} complete</h1>
        <div class='subtitle'>The {escape(label)} workflow has been completed and persisted for route <b>{escape(route)}</b>.</div>
        <div class='banner'>Saved progress remains in <code>{escape(str(get_persistence_path()))}</code>.</div>
      </section>
      <div class='btnrow'><a class='btn btn-back' href='/shipping-workflow?{escape(launcher_q)}'>Back to launcher</a></div>
    </div>
    """
    return html_page(f'{label} Complete', body)
