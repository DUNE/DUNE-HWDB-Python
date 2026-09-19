from dash import Input, Output, State, html, dcc, ctx, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash import clientside_callback
from dash import ALL
import base64, json, time, threading
from datetime import datetime

from Sisyphus.Configuration import config
from Sisyphus.RestApiV1 import (
    get_hwitems, get_hwitem_test, get_hwitem, get_subcomponents,
    patch_hwitem, post_hwitem_image, get_hwitem_test, post_test, whoami,
    get_component_type_image_list, get_image,
    get_roles, post_component_type_image,
)
from Sisyphus.RestApiV1 import Utilities as ra_util

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import re

# for saving a PDF file
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Preformatted
from reportlab.platypus import Table, TableStyle
from xml.sax.saxutils import escape
from reportlab.lib import colors

# Add plots to the summary PDF
import io
import tempfile
import plotly.io as pio
from reportlab.platypus import Image as RLImage
from reportlab.lib.units import inch
import numpy as np

# Scanning
import socket
import requests
import urllib.parse
import ipaddress
#from Sisyphus.Gui.Dashboard.utils.scanner_certs import hostname_local, lan_ip_best_effort



logger = config.getLogger(__name__)

# Turn-on/off the scanner feature
import os
#ENABLE_SCANNER = os.getenv("HWDB_ENABLE_SCANNER", "0") == "1"
ENABLE_SCANNER = 1

if ENABLE_SCANNER:
    from Sisyphus.Gui.Dashboard.utils.scanner import new_scan_session
    from Sisyphus.Gui.Dashboard.utils import scanner_server as scanner_srv
    from flask import request as flask_request
    from Sisyphus.Gui.Dashboard.utils.netutil import lan_host_candidates
#---------------------------------------



# ----------------------------
# For the scanner
# ----------------------------
SCAN_BTN_BASE = {
    "height": "45px",
    "width": "46px",
    "borderRadius": "10px",
    "marginRight": "8px",
    "fontWeight": "900",
    "boxShadow": "0 2px 6px rgba(0,0,0,0.10)",
}
SCAN_BTN_LIGHT = {
    "backgroundColor": "#eef5ff",
    "border": "1px solid #b9d6ff",
    "color": "#0b3d91",
}

SCAN_BTN_ACTIVE = {
    "backgroundColor": "#cfe2ff",
    "border": "1px solid #7aa7ff",
    "color": "#0b3d91",
}
def _best_lan_ip() -> str:
    """
    Returns a LAN IP for the machine (best-effort).
    """
    try:
        # This doesn't actually connect; it's a common trick to pick an outbound interface.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


SCANNER_PORT = 8766  # must match __main__.py scanner server port

_SCANNER_HTTP = requests.Session()
_SCANNER_HTTP.trust_env = False  # Ignore HTTP(S)_PROXY for localhost calls!!

_QR_STYLE_HIDDEN = {"display": "none"}
_QR_STYLE_VISIBLE_BASE = {
    "width": "260px",
    "height": "260px",
    "margin": "0 auto",
    "borderRadius": "12px",
    "border": "1px solid #E0E6EF",
    "backgroundColor": "white",
}

def _scanner_local_base() -> str:
    # Prefer HTTPS, but allow HTTP if server is running without TLS for any reason.
    # (We still only ever call loopback here.)
    return f"https://127.0.0.1:{SCANNER_PORT}"

def _scanner_local_bases() -> list[str]:
    port = SCANNER_PORT
    bases = [
        f"https://127.0.0.1:{port}",
        f"http://127.0.0.1:{port}",
        f"https://localhost:{port}",
        f"http://localhost:{port}",
    ]

    # extra fallback: try WSL eth0 ip / best LAN ip
    #try:
    #    ip = _best_lan_ip()
    #    if ip and ip != "127.0.0.1":
    #        bases.insert(0, f"https://{ip}:{port}")
    #        bases.insert(1, f"http://{ip}:{port}")
    #except Exception:
    #    pass

    return bases

def _scanner_healthcheck(timeout=(2.5, 4.0)) -> tuple[bool, str, dict | None]:
    """
    Returns (ok, base_url_used, json_or_none).
    """
    last_https_err = None
    last_http_err = None
    for base in _scanner_local_bases():
        try:
            r = _SCANNER_HTTP.get(f"{base}/health", timeout=timeout, verify=False)
            if r.ok:
                j = r.json() if "application/json" in (r.headers.get("content-type") or "") else {}
                return True, base, j if isinstance(j, dict) else {}
        except Exception as e:
            #last_err = e
            if base.startswith("https://"):
                last_https_err = e
            else:
                last_http_err = e
            continue
    return False, "", {"https_error": str(last_https_err), "http_error": str(last_http_err)}
    #return False, "", {"error": str(last_err) if last_err else "unknown"}


def _scanner_best_effort_cancel(token: str | None):
    """
    Best-effort: clear active /phone job AND cancel token on the scanner server.
    Ignore errors.
    """
    token = (token or "").strip()

    for base in _scanner_local_bases():
        try:
            # Stop /phone from thinking a scan is pending
            _SCANNER_HTTP.post(f"{base}/api/active/clear", timeout=(1.5, 2.5), verify=False)
        except Exception:
            pass

        if token:
            try:
                _SCANNER_HTTP.post(f"{base}/api/scan/{urllib.parse.quote(token)}/cancel",
                                   timeout=(1.5, 2.5), verify=False)
            except Exception:
                pass

def _make_qr_data_uri(text: str, *, box_size: int = 10, border: int = 2) -> str | None:
    """
    Returns a data:image/png;base64,... URI for a QR code of `text`.
    If qrcode/PIL isn't installed, returns None.
    """
    try:
        import qrcode
        from PIL import Image  # noqa: F401 (qrcode uses PIL)
        import io, base64

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        bio = io.BytesIO()
        img.save(bio, format="PNG")
        b64 = base64.b64encode(bio.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.warning(f"[ExecSum] QR generation failed: {e}")
        return None

def _phone_url_for_scanner(*, host: str, port: int, token: str, scheme: str = "https") -> str:
    scheme = (scheme or "https").strip().lower()
    if scheme not in ("http", "https"):
        scheme = "https"
    return f"{scheme}://{host}:{port}/scan/{urllib.parse.quote(token)}?mode=component_type"



def _phone_home_url(*, host: str, port: int, scheme: str = "https") -> str:
    scheme = (scheme or "https").strip().lower()
    if scheme not in ("http", "https"):
        scheme = "https"
    return f"{scheme}://{host}:{port}/phone"

def _render_wsl2_portproxy_card(hj: dict, *, port: int) -> tuple[bool, list, list[str]]:
    """
    Returns:
      (is_wsl_ok, card_children, phone_urls)
    where card_children can be placed directly into a Dash container.
    """
    try:
        #pp = (hj or {}).get("wsl2_portproxy") or {}
        pp = (hj or {}).get("wsl2_portproxy") or hj or {}
        if not isinstance(pp, dict) or not pp.get("ok"):
            return (False, [], [])

        cmds = pp.get("commands") or []
        if not isinstance(cmds, list):
            cmds = []
        cmds_text = "\n".join(str(x) for x in cmds if x is not None).strip()

        phone_urls = pp.get("phone_urls") or []
        if not isinstance(phone_urls, list):
            phone_urls = []

        # A compact “card” block
        card = [
            html.Div(
                [
                    html.Div(
                        "WSL2 detected — Windows portproxy may be required",
                        style={"fontWeight": "900", "fontSize": "16px", "marginBottom": "6px", "color": "#7a3e00"},
                    ),
                    html.Div(
                        "If your phone cannot open the scanner page, run the commands below in "
                        "Windows PowerShell *as Administrator* after each reboot / WSL restart.",
                        style={"color": "#555", "fontSize": "13px", "marginBottom": "8px"},
                    ),
                    html.Pre(
                        cmds_text or "(no commands available)",
                        style={
                            "whiteSpace": "pre-wrap",
                            "fontFamily": "Menlo, Monaco, Consolas, monospace",
                            "fontSize": "12px",
                            "padding": "10px 12px",
                            "borderRadius": "10px",
                            "border": "1px solid #f0c37a",
                            "backgroundColor": "#fff7e6",
                            "maxHeight": "260px",
                            "overflowY": "auto",
                        },
                    ),
                    html.Div(
                        [
                            html.Div("Try these URLs on your phone:", style={"fontWeight": "800", "marginTop": "8px"}),
                            html.Ul(
                                [
                                    html.Li(
                                        html.A(u, href=u, target="_blank", rel="noopener noreferrer")
                                    )
                                    for u in phone_urls[:8]
                                ],
                                style={"marginTop": "6px", "marginBottom": "0px"},
                            ),
                        ],
                        style={"marginTop": "4px"},
                    ),
                ],
                style={
                    "border": "2px solid #f0c37a",
                    "backgroundColor": "#fffdf7",
                    "borderRadius": "12px",
                    "padding": "10px 12px",
                    "marginTop": "10px",
                },
            )
        ]

        return (True, card, [str(u) for u in phone_urls if isinstance(u, str)])
    except Exception:
        return (False, [], [])


def _host_from_url(u: str) -> str:
    try:
        return urllib.parse.urlparse(u).hostname or ""
    except Exception:
        return ""

def _score_host_for_phone(host: str) -> int:
    """
    Lower is better.
    Prefer 192.168/16, then 10/8, then other private;
    push 172.16/12 to the end (WSL2/NAT/VPN often).
    """
    h = (host or "").strip()
    try:
        ip = ipaddress.ip_address(h)
        if ip.is_loopback:
            return 900
        if ip.is_link_local:
            return 800
        if ip in ipaddress.ip_network("192.168.0.0/16"):
            return 0
        if ip in ipaddress.ip_network("10.0.0.0/8"):
            return 1
        if ip in ipaddress.ip_network("172.16.0.0/12"):
            return 50
        if ip.is_private:
            return 10
        return 500
    except Exception:
        # Hostname: ok, but usually worse than literal LAN IP
        if h.endswith(".local"):
            return 200
        if h in ("localhost",):
            return 999
        return 100

def _pick_phone_primary(urls: list[str]) -> str:
    urls = [u for u in (urls or []) if isinstance(u, str) and u.strip()]
    if not urls:
        return ""
    # Sort by score using parsed hostname
    urls_sorted = sorted(urls, key=lambda u: _score_host_for_phone(_host_from_url(u)))
    return urls_sorted[0]
    
    
# ----------------------------
# Background job registries
# ----------------------------
_execsum_subcomp_jobs = {}  # job_id -> {"done":bool, "error":str|None, "rowData":[...]}
_execsum_details_jobs = {}  # job_id -> {"done":bool,"error":str|None,"payload":tuple|None}
_execsum_sig_jobs = {}  # job_id -> {"done":bool, "error":str|None, "new_es":list|None, "msg":str|None, "new_table":list|None}
_execsum_pdf_jobs = {}  # job_id -> {"done":bool,"error":str|None,"msg":str|None}

# ----------------------------
# Role cache (id -> name)
# ----------------------------
_roles_cache = {
    "fetched_at": 0.0,
    "map": {},   # {role_id:int -> role_name:str}
}

def _whoami_role_ids() -> set[int]:
    """
    Return a set of role IDs from whoami().
    """
    try:
        resp = whoami()
        d = resp.get("data") if isinstance(resp, dict) else None
        roles = (d or {}).get("roles") if isinstance(d, dict) else None
        if not isinstance(roles, list):
            return set()
        out = set()
        for r in roles:
            if isinstance(r, dict) and r.get("id") is not None:
                try:
                    out.add(int(r["id"]))
                except Exception:
                    pass
        return out
    except Exception:
        return set()

def _get_role_name_map(max_age_sec: int = 600) -> dict[int, str]:
    """
    Returns {role_id: role_name}, cached for max_age_sec seconds.
    """
    now = time.time()
    if _roles_cache["map"] and (now - float(_roles_cache["fetched_at"])) < max_age_sec:
        return _roles_cache["map"]

    mp: dict[int, str] = {}
    try:
        resp = get_roles()
        data = resp.get("data") if isinstance(resp, dict) else None
        if isinstance(data, list):
            for r in data:
                if not isinstance(r, dict):
                    continue
                rid = r.get("id")
                nm = (r.get("name") or "").strip()
                if rid is None or not nm:
                    continue
                try:
                    mp[int(rid)] = nm
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"[ExecSum] get_roles() failed: {e}")

    _roles_cache["map"] = mp
    _roles_cache["fetched_at"] = now
    return mp

def _reset_required_role_ids_from_cfg(cfg: dict) -> list[int]:
    """
    RESET role restriction:
      - Find the smallest NON-NEGATIVE rank among cfg["signees"].
      - Use that signee's roles as required roles.
      - If there are NO non-negative ranks (i.e., everybody is negative), return [] (no restriction).
    """
    signees = (cfg or {}).get("signees") or []
    best = None
    best_rank = None

    for s in signees:
        if not isinstance(s, dict):
            continue
        try:
            rk = int(s.get("rank", -1))
        except Exception:
            rk = -1

        if rk < 0:
            continue  # only consider non-negative for RESET restriction

        if best_rank is None or rk < best_rank:
            best_rank = rk
            best = s

    if not best:
        return []  # everybody negative => no restriction

    rr = best.get("roles") or []
    out = []
    if isinstance(rr, list):
        for x in rr:
            try:
                out.append(int(x))
            except Exception:
                pass
    return out


# ----------------------------
# Component Status
# ----------------------------
STATUS_OPTIONS = [
    {"value": 0, "label": "Unknown"},
    {"value": 1, "label": "(obsolete) Available"},
    {"value": 2, "label": "(obsolete) Temporarily Unavailable"},
    {"value": 3, "label": "(obsolete) Permanently Unavailable"},
    {"value": 100, "label": "In Fabrication"},
    {"value": 110, "label": "Waiting on QA/QC Tests"},
    {"value": 120, "label": "QA/QC Tests - Passed All"},
    {"value": 130, "label": "QA/QC Tests - Non-conforming"},
    {"value": 140, "label": "QA/QC Tests - Use As Is"},
    {"value": 150, "label": "In Rework"},
    {"value": 160, "label": "In Repair"},
    {"value": 170, "label": "Permanently Unavailable"},
    {"value": 180, "label": "Broken or Needs Repair"},
]
STATUS_ID_BY_LABEL = {o["label"]: o["value"] for o in STATUS_OPTIONS}
STATUS_LABEL_BY_ID = {o["value"]: o["label"] for o in STATUS_OPTIONS}

DETAILS_STYLE_HIDDEN = {
    #"display": "flex",                 # IMPORTANT: not "none"
    #"gap": "20px",
    #"justifyContent": "space-between",
    #"opacity": 0.0,                    # invisible
    #"height": "0px",                   # collapsed
    #"overflow": "hidden",
    #"pointerEvents": "none",           # optional: prevents clicking invisible stuff
    "display": "none",   # Now thsi would fully removed from layout... hopefully...
}

DETAILS_STYLE_VISIBLE = {
    "display": "flex",
    "gap": "20px",
    "justifyContent": "space-between",
    #"opacity": 1.0,
    #"height": "auto",
    #"overflow": "visible",
    #"pointerEvents": "auto",
}

PDF_BTN_ENABLED_STYLE = {
    "width":"100%",
    "fontSize":"18px",
    "padding":"12px",
    "borderRadius":"10px",
}

PDF_BTN_DISABLED_STYLE = dict(PDF_BTN_ENABLED_STYLE, **{
    "opacity": 0.45,
    "cursor": "not-allowed",
})

MODE_BTN_BASE = {
    "height": "45px",
    "borderRadius": "10px",
    "marginRight": "8px",
    "fontWeight": "900",
}
MODE_BTN_DETAIL = dict(MODE_BTN_BASE, **{
    "backgroundColor": "#fff7e6",
    "border": "1px solid #f0b35a",
    "color": "#7a3e00",
})
MODE_BTN_DEFAULT = dict(MODE_BTN_BASE, **{
    "backgroundColor": "#eef5ff",
    "border": "1px solid #b9d6ff",
    "color": "#0b3d91",
})
MODE_BTN_DISABLED = dict(MODE_BTN_BASE, **{
    "opacity": 0.6,
    "cursor": "not-allowed",
})

# ----------------------------
# Signature upload jobs
# ----------------------------
SIG_BTN_STYLE_NORMAL = {
    "backgroundColor": "#0d6efd",   # bootstrap primary
    "border": "none",
    "borderRadius": "8px",
    "padding": "10px 18px",
    "fontWeight": "700",
    "transition": "all 0.15s ease-in-out",
}

SIG_BTN_STYLE_BUSY = dict(SIG_BTN_STYLE_NORMAL, **{
    # "lighter" look (like your screenshot) while the job runs
    "backgroundColor": "#6ea8fe",
    "opacity": 0.75,
    "cursor": "not-allowed",
})

# ----------------------------
# Fetch the Type Name
# ----------------------------
def _fetch_type_name(typeid: str) -> str:
    try:
        resp = get_hwitems(typeid, size=1)  # tiny request; we only need component_type!!
        ct = resp.get("component_type") if isinstance(resp, dict) else None
        if isinstance(ct, dict):
            nm = (ct.get("name") or "").strip()
            if nm:
                return nm
    except Exception as e:
        logger.warning(f"[ExecSum] _fetch_type_name failed typeid={typeid}: {e}")
    return ""

# ----------------------------
# Fetch the config file from the HWDB (Type/Image)
# ----------------------------
def _find_es_config_image_id(resp: dict, typeid: str) -> tuple[str | None, str | None]:
    """
    From get_component_type_image_list(typeid) response, find the ES config json image.
    Rule: image_name starts with f"ES_{typeid}_" and endswith ".json".
    Returns (image_id, image_name) or (None, None)
    If multiple match, pick the newest by 'created' timestamp.
    """
    if not isinstance(resp, dict):
        return (None, None)

    data = resp.get("data") or []
    if not isinstance(data, list) or not data:
        return (None, None)

    prefix = f"ES_{typeid}_"
    matches = []
    for rec in data:
        if not isinstance(rec, dict):
            continue
        nm = (rec.get("image_name") or "").strip()
        if nm.startswith(prefix) and nm.lower().endswith(".json"):
            matches.append(rec)

    if not matches:
        return (None, None)

    # pick newest by created string (ISO-ish); fallback: keep first
    # but now let's parse datetime, if possible. Then go to fall back. Put a tie-breaker as well (do we ever need this!!??)
    def _created_key(r):
        #return (r.get("created") or "")
        c = (r.get("created") or "").strip()

        # Try ISO-8601 parse (handles "...Z")
        dt = None
        if c:
            try:
                # normalize trailing Z
                cc = c.replace("Z", "+00:00")
                dt = datetime.fromisoformat(cc)
            except Exception:
                dt = None

        # tie-breaker (stable)
        tie = str(r.get("image_id") or r.get("id") or "")

        # sort descending, so return a tuple where "bigger" means newer
        # dt is preferred; otherwise raw string
        return (dt or datetime.min, c, tie)

    
    matches.sort(key=_created_key, reverse=True)

    best = matches[0]
    return (best.get("image_id"), best.get("image_name"))


def _download_es_config_json_to_temp(image_id: str, image_name: str) -> dict:
    """
    Downloads config json from HWDB to a temporary file, parses JSON, deletes temp file.
    Returns parsed dict.
    """
    import tempfile
    from pathlib import Path

    # keep suffix mainly for debugging / correct editor hints
    suffix = ".json"
    if isinstance(image_name, str) and image_name.lower().endswith(".json"):
        suffix = ".json"

    tmp_path = None
    try:
        fd, tmp_name = tempfile.mkstemp(suffix=suffix, prefix="execsum_cfg_")
        tmp_path = Path(tmp_name)

        # close the fd; get_image will write to the filename
        try:
            import os
            os.close(fd)
        except Exception:
            pass

        get_image(image_id, write_to_file=str(tmp_path))

        # parse
        return json.loads(tmp_path.read_text(encoding="utf-8"))

    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


def _load_execsum_cfg_from_hwdb_type(typeid: str) -> tuple[dict | None, str]:
    """
    Full flow:
      1) get_component_type_image_list(typeid)
      2) find ES_<typeid>_*.json
      3) download via get_image()
      4) parse JSON and normalize
    Returns (cfg_or_None, status_message)
    """
    try:
        resp = get_component_type_image_list(typeid)
    except Exception as e:
        return (None, f"Config lookup failed for {typeid}: {e}")

    img_id, img_name = _find_es_config_image_id(resp, typeid)
    if not img_id:
        return (None, f"No ES config found for {typeid} (expected image_name ES_{typeid}_*.json)")

    try:
        cfg = _download_es_config_json_to_temp(img_id, img_name or "")
        cfg = _normalize_execsum_cfg(cfg)
        return (cfg, f"Loaded config from HWDB: {img_name}")
    except Exception as e:
        return (None, f"Config download/parse failed for {typeid} (image_id={img_id}, name={img_name}): {e}")

# ----------------------------
# Fetch the latest ES
# ----------------------------
def fetch_latest_es_list(pid: str) -> list[dict]:
    """
    Returns the ES list from the LATEST ES test for this PID.
    If none exists, returns [].
    """
    try:
        resp = get_hwitem_test(pid, "ES", history=False)

        # Shape A: wrapper {"data":[...]}
        if isinstance(resp, dict) and isinstance(resp.get("data"), list) and resp["data"]:
            rec0 = resp["data"][0]
            if isinstance(rec0, dict):
                td = rec0.get("test_data") or {}
                if isinstance(td, dict):
                    es = td.get("ES") or []
                    return es if isinstance(es, list) else []
            return []

        # Shape B: direct test record dict (less common, but you already handle it elsewhere)
        if isinstance(resp, dict) and "test_data" in resp:
            td = resp.get("test_data") or {}
            if isinstance(td, dict):
                es = td.get("ES") or []
                return es if isinstance(es, list) else []
            return []

        return []
    except Exception as e:
        logger.error(f"[ExecSum] fetch_latest_es_list failed pid={pid}: {e}")
        return []
def fetch_latest_es_and_todos(pid: str) -> tuple[list[dict], dict | None]:
    """
    Returns (es_list, todos_payload) from the latest ES test.
    todos_payload is whatever we stored in test_data["todos"].
    """
    try:
        resp = get_hwitem_test(pid, "ES", history=False)

        # wrapper {"data":[{...}]}
        rec0 = None
        if isinstance(resp, dict) and isinstance(resp.get("data"), list) and resp["data"]:
            rec0 = resp["data"][0]
        elif isinstance(resp, dict) and "test_data" in resp:
            rec0 = resp

        if not isinstance(rec0, dict):
            return ([], None)

        td = rec0.get("test_data") or {}
        if not isinstance(td, dict):
            return ([], None)

        es = td.get("ES") or []
        if not isinstance(es, list):
            es = []

        todos = td.get("todos")
        if not isinstance(todos, dict):
            todos = None

        return (es, todos)

    except Exception as e:
        logger.error(f"[ExecSum] fetch_latest_es_and_todos failed pid={pid}: {e}")
        return ([], None)
# ----------------------------
# Merge entry into ES list
# ----------------------------
def merge_es_entry(es_list, *, name: str, signature: str, rank: int, timestamp: str, comments: str | None = None):
#def merge_es_entry(es_list: list[dict], *, name: str, signature: str, rank: int) -> list[dict]:
    """
    Merge/update one signee into existing ES list.
    - If 'name' exists, overwrite signature/rank (keeps one entry per name).
    - Else append.
    """
    out = []
    replaced = False

    for ent in (es_list or []):
        if not isinstance(ent, dict):
            continue
        if ent.get("name") == name:
            out.append({
                "name": name,
                "signature": signature,
                "rank": int(rank),
                "timestamp": timestamp,
                "comments": (comments or "").strip(),
            })
            replaced = True
        else:
            out.append(ent)

    if not replaced:
        out.append({
            "name": name,
            "signature": signature,
            "rank": int(rank),
            "timestamp": timestamp,
            "comments": (comments or "").strip(),
        })

    return out
# ----------------------------
# Post consolidated ES
# ----------------------------
def post_es_test(pid: str, es_list: list[dict], comments: str = "", todos_payload: dict | None = None) -> dict:
    data = {
        "comments": comments or "Executive Summary signatures",
        "test_type": "ES",
        "test_data": {
            "ES": es_list,
        }
    }
    if isinstance(todos_payload, dict):
        data["test_data"]["todos"] = todos_payload
    return post_test(pid, data)
# ----------------------------
# Map existing ES enrties by name
# ----------------------------
def _es_map_by_name(es_list: list[dict]) -> dict[str, dict]:
    """
    { "HWDB Liaison": {"signature": "...", "rank": 2, ...}, ... }
    """
    out = {}
    for ent in (es_list or []):
        if not isinstance(ent, dict):
            continue
        nm = (ent.get("name") or "").strip()
        sig = ent.get("signature")
        if nm:
            out[nm] = ent
    return out



# ----------------------------
# Helpers to deal with sub-components
# ----------------------------
def _bool_mark(x: bool) -> str:
    return "✅" if bool(x) else "❌"

def _add_group_levels(rows: list[dict], *, max_levels: int = 12) -> list[dict]:
    """
    Group by the FULL internal path including self, so each group node
    has a corresponding leaf row inside it.

    Keep internal keys (pid__N / pid__ROOT) for uniqueness.
    Use valueFormatter in the grid to display "pretty" labels.
    """
    out = []
    for r in (rows or []):
        p = r.get("path") or []
        if not isinstance(p, list):
            p = []

        # ✅ include self so leaf row exists inside its group
        levels = p

        rr = dict(r)
        for i in range(max_levels):
            rr[f"level{i}"] = levels[i] if i < len(levels) else None
        out.append(rr)
    return out


def _fetch_hwitem_status_flags(pid: str, cache_key: str | None = None) -> tuple[str, bool, bool]:
    """
    Returns (status_text, certified_qaqc, qaqc_uploaded) for a PID.
    Tries cache first, then falls back to get_hwitem().
    """
    # 1) try cache (no network)
    try:
        if cache_key and cache_key in _execsum_cache:
            it = (_execsum_cache[cache_key].get("by_pid", {}).get(pid, {}) or {}).get("item")
            if isinstance(it, dict):
                status_text = str(_safe(it.get("status", ""))).strip() or "Unknown"
                return (status_text, bool(it.get("certified_qaqc")), bool(it.get("qaqc_uploaded")))
    except Exception:
        pass

    # 2) fallback: network
    try:
        resp = get_hwitem(pid)
        d = resp.get("data") if isinstance(resp, dict) else {}
        if not isinstance(d, dict):
            return ("Unknown", False, False)

        status_text = str(_safe(d.get("status", ""))).strip() or "Unknown"
        return (status_text, bool(d.get("certified_qaqc")), bool(d.get("qaqc_uploaded")))
    except Exception as e:
        logger.error(f"[ExecSum] _fetch_hwitem_status_flags failed pid={pid}: {e}")
        return ("Unknown", False, False)


def _fetch_children(parent_pid: str) -> list[dict]:
    """
    Returns list of subcomponent entries from /subcomponents?history=False
    without passing 'history' into requests kwargs.
    """
    try:
        #resp = get_subcomponents(parent_pid)
        resp = get_subcomponents(parent_pid, params=[("history", "false")])
        
        data = resp.get("data", []) if isinstance(resp, dict) else []
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"[ExecSum] _fetch_children failed parent={parent_pid}: {e}")
        return []
    
def _build_subcomponent_rows_recursive(root_pid: str, cache_key: str | None = None) -> list[dict]:
    """
    BFS down the subcomponent tree, producing AG Grid treeData rows.

    Guarantees:
      - row["path"] is NON-EMPTY list[str]
      - row["id"] is UNIQUE across ALL rows
      - duplicates under same parent get internal suffix: pid__2, pid__3, ...
    """
    executor = ra_util._executor
    rows: list[dict] = []
    row_by_self_key: dict[str, dict] = {}

    # memo per cache_key
    subtree_cache = None
    if cache_key and cache_key in _execsum_cache:
        subtree_cache = _execsum_cache[cache_key].setdefault("subtree_cache", {})

    visited_edges: set[tuple[tuple[str, ...], str]] = set()

    # queue holds tuples: (real_parent_pid, INTERNAL path list for that parent)
    root_key = f"{root_pid}__ROOT"
    queue: list[tuple[str, list[str], str]] = [(root_pid, [root_key], root_key)]

    # -----------------------------
    # EMIT A REAL ROOT ROW here!!!
    # -----------------------------
    # fetch flags once here.
    try:
        #cert, upl = _fetch_hwitem_flags(root_pid)
        #cert, upl = _fetch_hwitem_flags(root_pid, cache_key=cache_key)
        status_text, cert, upl = _fetch_hwitem_status_flags(root_pid, cache_key=cache_key)
    except Exception:
        cert, upl = (False, False)

    root_row = {
        "id": root_key,          # unique
        "pid": root_pid,         # real pid
        "parent_pid": "",        # none for root
        "path": [root_key],      # leaf lives inside the __ROOT group
        "n_children": 0,        # this could be filled later
        "type_name": "",
        "position_name": "",
        "status": status_text,
        "certified": _bool_mark(cert),
        "uploaded": _bool_mark(upl),
        "self_key": root_key,    # for leafForGroup(node.key)
        "parent_key": None,
        "is_leaf_for_group": False,
    }
    rows.append(root_row)
    row_by_self_key[root_key] = root_row
    

    # Persist across the whole traversal!
    sibling_counts: dict[tuple[tuple[str, ...], str], int] = {}
    
    while queue:
        parents = queue
        queue = []

        # ---- DEBUG: detect same parent occurrence twice in this batch ----
        seen_parent_occ = set()
        for (ppid, ppath, pself_key) in parents:
            k = (str(ppid), tuple(ppath or []))
            if k in seen_parent_occ:
                logger.error(
                    f"[ExecSum] SAME PARENT OCCURRENCE TWICE in parents batch: pid={ppid} path={ppath}"
                )
            seen_parent_occ.add(k)

        
        # ---------------------------------------------------------
        # 1) Fetch children for each parent (concurrently)
        # ---------------------------------------------------------
        sub_futs: dict[str, any] = {}
        for (ppid, _ppath, _pself_key) in parents:
            if subtree_cache is not None and ppid in subtree_cache and "children" in subtree_cache[ppid]:
                sub_futs[ppid] = None
            else:
                sub_futs[ppid] = executor.submit(_fetch_children, ppid)

        parent_children_map: dict[str, list[dict]] = {}
        for (ppid, _ppath, pself_key) in parents:
            if subtree_cache is not None and ppid in subtree_cache and "children" in subtree_cache[ppid]:
                children = subtree_cache[ppid]["children"]
            else:
                fut = sub_futs.get(ppid)
                try:
                    children = fut.result() if fut is not None else []
                except Exception as e:
                    logger.error(f"[ExecSum] get_subcomponents failed parent={ppid}: {e}")
                    children = []
                if subtree_cache is not None:
                    subtree_cache.setdefault(ppid, {})["children"] = children

            # set THIS parent node’s n_children (always)
            n_children = len(children or [])
            if pself_key in row_by_self_key:
                row_by_self_key[pself_key]["n_children"] = n_children

            parent_children_map[ppid] = children if isinstance(children, list) else []

        
            
        # ---------------------------------------------------------
        # 2) Build child_meta (internal_path created HERE exactly once)
        # ---------------------------------------------------------
        # tuple:
        #  (child_pid, parent_pid, internal_path, type_name, position_name, n_children_of_parent)
        #child_meta: list[tuple[str, str, list[str], str, str, int]] = []
        child_meta = []

        for (parent_pid, parent_internal_path, _pself_key) in parents:
            children = parent_children_map.get(parent_pid, [])
            n_children = len(children or [])

            sibling_key_seen: dict[tuple[str, ...], set[str]] = {} # for debugging

            
            for ch in (children or []):
                child_pid = str(ch.get("part_id") or "").strip()
                if not child_pid:
                    continue

                type_name = str(_safe(ch.get("type_name") or "")).strip()
                position_name = str(_safe(ch.get("functional_position") or "")).strip()

                # parent occurrence key (NOT just parent_pid)
                pkey = tuple(parent_internal_path)

                
                
                # stable per-parent-occurrence counter for this child PID
                skey = (pkey, child_pid)
                n = sibling_counts.get(skey, 0) + 1
                sibling_counts[skey] = n

                child_key = f"{child_pid}__{n}"
                internal_path = list(parent_internal_path) + [child_key]

                #--------------
                # debugging
                sibling_key_seen.setdefault(pkey, set())
                if child_key in sibling_key_seen[pkey]:
                    logger.error(f"[ExecSum] DUP SIBLING KEY under parent_path={list(pkey)}: child_key={child_key}")
                sibling_key_seen[pkey].add(child_key)
                #--------------
                
                child_meta.append(
                    (child_pid, str(parent_pid), internal_path, type_name, position_name, n_children)
                )

        # ---------------------------------------------------------
        # 3) Fetch the 3 flags for unique child PIDs (concurrently)
        # ---------------------------------------------------------
        hw_futs = {}
        for (child_pid, *_rest) in child_meta:
            # reuse subtree_cache when possible
            if subtree_cache is not None and child_pid in subtree_cache and "status_flags" in subtree_cache[child_pid]:
                continue
            if child_pid not in hw_futs:
                hw_futs[child_pid] = executor.submit(_fetch_hwitem_status_flags, child_pid, cache_key)

        status_flags_map: dict[str, tuple[str, bool, bool]] = {}
        for (child_pid, *_rest) in child_meta:
            if subtree_cache is not None and child_pid in subtree_cache and "status_flags" in subtree_cache[child_pid]:
                status_flags_map[child_pid] = subtree_cache[child_pid]["status_flags"]
                continue

            fut = hw_futs.get(child_pid)
            try:
                status_flags = fut.result() if fut is not None else ("Unknown", False, False)
            except Exception:
                status_flags = ("Unknown", False, False)

            status_flags_map[child_pid] = status_flags
            if subtree_cache is not None:
                subtree_cache.setdefault(child_pid, {})["status_flags"] = status_flags

        # ---------------------------------------------------------
        # 4) Emit rows + enqueue next parents
        # ---------------------------------------------------------
        for (child_pid, parent_pid, internal_path, type_name, position_name, n_children_of_parent) in child_meta:
            #cert, upl = flags_map.get(child_pid, (False, False))
            status_text, cert, upl = status_flags_map.get(child_pid, ("Unknown", False, False))

            node_path = internal_path

            rid = "|".join(node_path)

            self_key = node_path[-1]
            parent_key = node_path[-2] if len(node_path) >= 2 else None

            
            row = {
                "id": rid,
                "pid": child_pid,
                "parent_pid": parent_pid,
                "path": node_path,
                "n_children": 0,
                "type_name": type_name,
                "position_name": position_name,
                "status": status_text,
                "certified": _bool_mark(cert),
                "uploaded": _bool_mark(upl),
                "self_key": self_key,
                "parent_key": parent_key,
                "is_leaf_for_group": False,
            }
            rows.append(row)
            row_by_self_key[self_key] = row

            # Traverse using the NODE path (not the row path)
            parent_path_key = tuple(node_path[:-1])
            edge_key = (parent_path_key, child_pid)

            if edge_key not in visited_edges:
                visited_edges.add(edge_key)
                queue.append((child_pid, node_path, self_key))

    # debugging...
    from collections import Counter

    paths = [tuple(r.get("path") or []) for r in rows if isinstance(r, dict)]
    dup_paths = [p for p, c in Counter(paths).items() if c > 1]

    if dup_paths:
        logger.error(f"[ExecSum] DUP FULL PATHS in builder: {len(dup_paths)}")
        for p in dup_paths[:10]:
            logger.error(f"  dup path = {list(p)}")




        
    # debugging...
    from collections import Counter
    paths = [tuple(r.get("path") or []) for r in rows]
    dups = [p for p, c in Counter(paths).items() if c > 1]
    if dups:
        logger.error(f"[ExecSum] STILL duplicate paths after disambiguate: {len(dups)}")
        for p in dups[:10]:
            logger.error(f"  dup path = {list(p)}")
            
    return rows


# ----------------------------
# Get the list of the all sub-components
# ----------------------------

def _patch_one_hwitem_flags(
    *,
    part_id: str,
    status_id: int,
    certified_qaqc: bool,
    qaqc_uploaded: bool,
    comment: str = "",
) -> tuple[str, bool, str]:
    """
    Returns (pid, ok, err_msg)
    """
    try:
        data = {
            "part_id": part_id,
            "status": {"id": int(status_id)},
            "certified_qaqc": bool(certified_qaqc),
            "qaqc_uploaded": bool(qaqc_uploaded),
        }
        if comment:
            data["comments"] = comment

        patch_hwitem(part_id, data=data)
        return (part_id, True, "")
    except Exception as e:
        return (part_id, False, str(e))

# ----------------------------
# Get Component Status ID
# ----------------------------
def _status_id_from_anywhere(*, status_id, pid: str, cache_key: str | None) -> int:
    """
    Prefer: dropdown value (status_id arg) if valid.
    Else: derive from _execsum_cache[cache_key]["by_pid"][pid]["item"]["status"].
    Else: 0
    """
    # 1) dropdown value
    try:
        if status_id is not None:
            sid = int(status_id)
            if sid in STATUS_LABEL_BY_ID:
                return sid
    except Exception:
        pass

    # 2) cache fallback (root PID only; we apply same sid to all)
    try:
        if cache_key and cache_key in _execsum_cache:
            it = (_execsum_cache[cache_key].get("by_pid", {}).get(pid, {}) or {}).get("item") or {}
            status_text = str(_safe(it.get("status", ""))).strip()
            if status_text in STATUS_ID_BY_LABEL:
                return int(STATUS_ID_BY_LABEL[status_text])
            # sometimes a dict could carry an id
            if isinstance(it.get("status"), dict) and "id" in it["status"]:
                sid = int(it["status"]["id"])
                if sid in STATUS_LABEL_BY_ID:
                    return sid
            # or numeric string
            sid = int(status_text)
            if sid in STATUS_LABEL_BY_ID:
                return sid
    except Exception:
        pass

    return 0

    
# ----------------------------
# Server-side cache to be used when a PID row is selected (so it doesn’t hit HWDB again).
# ----------------------------
# Server-side cache: cache_key -> {"typeid":..., "test_types":[...], "by_pid":{pid: {"item":..., "tests":{tt: test_data}}}}
_execsum_cache = {}

# ----------------------------
# Background job registry
# ----------------------------
_execsum_jobs = {}  # jobid -> {"processed","total","done","error","rows","stage"}

# ----------------------------
# Get the full name
# ----------------------------
def _get_fullname_safe():
    try:
        resp = whoami()
        # common shapes: {"data": {...}} or direct dict
        d = resp.get("data") if isinstance(resp, dict) else None
        if isinstance(d, dict):
            return d.get("full_name")
        if isinstance(resp, dict):
            return resp.get("full_name")
        return "—"
    except Exception:
        return "—"

# ----------------------------
# Helpers for the worker
# ----------------------------

# now only grab a list of PIDs (and the config file)
def _execsum_sync_worker(job_id: str):
    job = _execsum_jobs[job_id]
    typeid = job["typeid"]

    try:
        # -------------------------
        # Stage 0: fetch config FIRST
        # -------------------------
        job["stage"] = "fetching_config"

        cfg, cfg_msg = _load_execsum_cfg_from_hwdb_type(typeid)
        if not cfg:
            job["cfg"] = None
            #job["mode"] = "default"
            job["has_config"] = False
        else:
            job["cfg"] = cfg
            #job["mode"] = "detail"
            job["has_config"] = True

        job["cfg_msg"] = cfg_msg
        job["type_name"] = _fetch_type_name(typeid)

        # -------------------------
        # Stage 1: fetch PID list
        # -------------------------
        job["stage"] = "fetching_pids"

        resp = get_hwitems(typeid, size=99999)
        items = resp.get("data", []) or []

        def _pid_key(it):
            pid = str(it.get("part_id") or it.get("pid") or "").strip()
            if "-" in pid:
                a, b = pid.split("-", 1)
                try:
                    return (a, int(b))
                except Exception:
                    return (a, b)
            return (pid, 0)

        items.sort(key=_pid_key, reverse=True)

        job["total"] = len(items)

        rows = []
        by_pid = {}
        for it in items:
            pid = _safe(it.get("part_id") or it.get("pid") or "")
            by_pid[pid] = {"item": it, "tests": {}}

            #rows.append({
            #    "selected": "☐",
            #    "pid": pid,
            #    "serial": _safe(it.get("serial_number", "")),
            #    "status": _safe(it.get("status", "")),
            #    "certified": "✅" if bool(it.get("certified_qaqc")) else "❌",
            #    "uploaded":  "✅" if bool(it.get("qaqc_uploaded")) else "❌",
            #})

            rows.append({
                "id": pid,          # Dash DataTable row_id; not shown unless included in columns
                "selected": "☐",
                "pid": pid,
                "serial": _safe(it.get("serial_number", "")),
                "status": _safe(it.get("status", "")),
                "certified": "✅" if bool(it.get("certified_qaqc")) else "❌",
                "uploaded":  "✅" if bool(it.get("qaqc_uploaded")) else "❌",
            })

        job["rows"] = rows

        cache_key = f"{typeid}:{int(time.time()*1000)}"
        _execsum_cache[cache_key] = {
            "typeid": typeid,
            "by_pid": by_pid,
            "tests_cache": {},
            "subtree_cache": {},
            "pidlist_cache": {},
            "images_cache": {},
        }

        job["cache_key"] = cache_key
        job["done"] = True
        job["stage"] = "done"

    except Exception as e:
        job["error"] = str(e)
        job["done"] = True
        job["stage"] = "error"
        logger.error(f"[ExecSum Worker] {e}")




# ----------------------------
# worker
# ----------------------------
def _safe(v):
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, dict):
        if "name" in v:
            return v.get("name", "")
        if "id" in v:
            return str(v.get("id", ""))
        return json.dumps(v)
    if isinstance(v, (list, tuple)):
        try:
            if all(isinstance(x, (str, int, float, bool)) or x is None for x in v):
                return ", ".join("" if x is None else str(x) for x in v)
        except Exception:
            pass
        return json.dumps(v)
    try:
        return v.item()
    except Exception:
        return str(v)



# ----------------------------
# Helpers: parse uploaded JSON
# ----------------------------
def _parse_upload(contents: str):
    # contents = "data:application/json;base64,...."
    header, b64 = contents.split(",", 1)
    raw = base64.b64decode(b64).decode("utf-8")
    return json.loads(raw)
def _normalize_execsum_cfg(cfg: dict) -> dict:
    if not isinstance(cfg, dict):
        return {}

    consortium = (cfg.get("consortium name") or cfg.get("consortium_name") or "").strip()
    cfg["consortium_name"] = consortium

    # normalize signees list (NOW includes roles)
    signees = cfg.get("signees") or []
    if not isinstance(signees, list):
        signees = []

    norm = []
    for s in signees:
        if not isinstance(s, dict):
            continue

        name = (s.get("name") or "").strip()
        try:
            rank = int(s.get("rank", -1))
        except Exception:
            rank = -1

        # roles: list[int]
        roles_raw = s.get("roles", [])
        roles_list: list[int] = []
        if isinstance(roles_raw, list):
            for x in roles_raw:
                try:
                    roles_list.append(int(x))
                except Exception:
                    pass

        if name:
            norm.append({"name": name, "rank": rank, "roles": roles_list})

    cfg["signees"] = norm

    # plots normalization
    plots = cfg.get("plots") or []
    if not isinstance(plots, list):
        plots = []
    for p in plots:
        if isinstance(p, dict):
            p["sum"] = bool(p.get("sum", False))
            p["part_id"] = (p.get("part_id") or "").strip()
            p["component_type_id"] = (p.get("component_type_id") or "").strip()

            # keep image_path as dict if present
            ip = p.get("image_path")
            if not isinstance(ip, dict):
                p["image_path"] = None
            else:
                p["image_path"] = {
                    "image_name": (ip.get("image_name") or "").strip(),
                    "history_order": int(ip.get("history_order") or 0),
                }
    cfg["plots"] = [p for p in plots if isinstance(p, dict)]

    return cfg


# ----------------------------
# Helpers: path extraction
# Supports "A.B[0].C" style
# ----------------------------
def _get_by_path(obj, path: str):
    """
    Supports:
      - "MRB Resistance" (single key)
      - "DATA[0].SiPM[3].V"
    Returns: value or None
    """
    if obj is None or not isinstance(path, str) or not path.strip():
        return None

    # If it's a plain key and exists, just return it (nice for "MRB Resistance")
    if path in obj:
        return obj.get(path)

    cur = obj
    token = ""
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if token:
                if isinstance(cur, dict) and token in cur:
                    cur = cur[token]
                else:
                    return None
                token = ""
            i += 1
            continue

        if ch == "[":
            # first apply pending token as dict key
            if token:
                if isinstance(cur, dict) and token in cur:
                    cur = cur[token]
                else:
                    return None
                token = ""

            # parse index
            j = path.find("]", i)
            if j < 0:
                return None
            idx_str = path[i+1:j].strip()
            try:
                idx = int(idx_str)
            except:
                return None
            if isinstance(cur, list) and 0 <= idx < len(cur):
                cur = cur[idx]
            else:
                return None
            i = j + 1
            continue

        token += ch
        i += 1

    # final pending token
    if token:
        if isinstance(cur, dict) and token in cur:
            cur = cur[token]
        else:
            return None

    return cur

def _as_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]

# ----------------------------
# just get the 1st 12 characters!!
# ----------------------------
def _typeid12_from_pid(pid: str) -> str:
    """
    'Type ID' = first 12 chars of the PID prefix.
    """
    pid = (pid or "").strip()
    if not pid:
        return ""
    prefix = pid.split("-", 1)[0].strip()
    return prefix[:12]

# ----------------------------
# Fetch test blob
# ----------------------------
def fetch_test_blob(pid: str, test_type_name: str):
    """
    Returns the test_data dict (the payload you want to plot) or None.
    """
    try:
        resp = get_hwitem_test(pid, test_type_name)
        #data = resp.get("data") or []
        #if not data:
        #    return None
        #rec0 = resp["data"][0]
        #if isinstance(rec0, dict):
        #    td = rec0.get("test_data")
        #    return td if isinstance(td, dict) else None
        
        # Case A: single test record dict
        if isinstance(resp, dict) and "test_data" in resp:
            td = resp.get("test_data")
            return td if isinstance(td, dict) else None

        # Case B: wrapper {"data":[...]}
        if isinstance(resp, dict) and isinstance(resp.get("data"), list) and resp["data"]:
            rec0 = resp["data"][0]
            if isinstance(rec0, dict):
                td = rec0.get("test_data")
                return td if isinstance(td, dict) else None
        return None
        #return data[0] if isinstance(data[0], dict) else None
    except Exception as e:
        logger.error(f"[ExecSum] get_hwitem_test failed pid={pid} type={test_type_name}: {e}")
        return None

# ----------------------------
# Plot builders
# ----------------------------

def make_scatter(xs, ys, title="Scatter"):
    X, Y = [], []
    xs = _as_list(xs)
    ys = _as_list(ys)

    # If both are lists of equal length of numbers, use them directly
    if len(xs) == len(ys) and all(isinstance(a, (int,float)) for a in xs) and all(isinstance(b, (int,float)) for b in ys):
        X, Y = xs, ys
    else:
        # Try flatten if nested
        def flatten_num(z):
            out=[]
            for t in _as_list(z):
                if isinstance(t, (int,float)):
                    out.append(t)
                elif isinstance(t, list):
                    out += [u for u in t if isinstance(u, (int,float))]
            return out
        X = flatten_num(xs)
        Y = flatten_num(ys)
        n = min(len(X), len(Y))
        X, Y = X[:n], Y[:n]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=X, y=Y, mode="markers"))
    fig.update_layout(title=title, margin=dict(l=20, r=20, t=40, b=20), height=360)
    return fig


# ----------------------------
# Export Plotly figures to PNG with Kaleido
# ----------------------------
def _fig_to_png_bytes(fig, width=1100, height=650, scale=2) -> bytes:
    """
    Notice that this requires kaleido installed.
    Returns PNG bytes.
    """
    # This uses Kaleido under the hood:
    return pio.to_image(fig, format="png", width=width, height=height, scale=scale)

def _bytes_to_rl_image(img_bytes: bytes):
    """
    Convert image bytes into a ReportLab Image flowable (RLImage).
    Returns RLImage or raises.
    """
    import io
    from reportlab.platypus import Image as RLImage
    bio = io.BytesIO(img_bytes)
    return RLImage(bio)

def _pdf_bytes_to_png_bytes(pdf_bytes: bytes, *, page: int = 0, dpi: int = 200) -> bytes:
    """
    Convert a PDF (bytes) to a PNG (bytes) for embedding into ReportLab.
    Default: first page.
    Tries PyMuPDF first, then pdf2image.
    """
    if not pdf_bytes:
        raise ValueError("Empty PDF bytes.")

    # ---- Option A: PyMuPDF (fitz) ----
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count == 0:
            raise ValueError("PDF has no pages.")
        page = max(0, min(int(page), doc.page_count - 1))
        p = doc.load_page(page)

        # dpi -> zoom factor (72 dpi is default)
        zoom = float(dpi) / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = p.get_pixmap(matrix=mat, alpha=False)  # alpha=False keeps it simple
        return pix.tobytes("png")
    except Exception:
        pass

    # ---- Option B: pdf2image (needs Poppler installed) ----
    try:
        from pdf2image import convert_from_bytes
        imgs = convert_from_bytes(pdf_bytes, dpi=dpi, first_page=page + 1, last_page=page + 1)
        if not imgs:
            raise ValueError("pdf2image returned no pages.")
        import io
        bio = io.BytesIO()
        imgs[0].save(bio, format="PNG")
        return bio.getvalue()
    except Exception as e:
        raise RuntimeError(
            "Cannot convert PDF to image. Install PyMuPDF (fitz) or pdf2image+Poppler."
        ) from e

# ----------------------------
# Path for a PDF file to be saved in
# ----------------------------
def _get_working_dir() -> Path:
    pref_file = Path(config.active_profile.profile_dir) / "dash_user_preferences.txt"
    wd = Path(pref_file.read_text().strip()) if pref_file.exists() else Path.cwd()
    if not wd.is_dir():
        wd = Path.cwd()
    return wd

# ----------------------------
# Add a range to PDF file name, if mulitple PIDs are selected
# ----------------------------
def _minmax_item_range_from_pids(pids: list[str]) -> tuple[str | None, str | None]:
    """
    Returns (min_item_5, max_item_5) from a PID list.
    min_item_5/max_item_5 are "00001" strings, or (None, None) if unavailable.
    """
    nums = []
    for pid in (pids or []):
        n = _item_number_from_pid(pid)   # int (no leading zeros) or None
        if n is not None:
            nums.append(int(n))
    if not nums:
        return (None, None)
    return (f"{min(nums):05d}", f"{max(nums):05d}")

# ----------------------------
# Generate & Upload PDF
# ----------------------------
def _do_generate_and_upload_pdf_default(
    *,
    selected_pid: str,
    cache_key: str | None,
    typeid: str | None,
    selected_pids: list[str] | None,
    signinfo: dict | None,
) -> str:
    attach_pid = (selected_pid or "").strip()
    if not attach_pid:
        return "No PID selected."

    typeid = (typeid or "").strip()
    if not typeid:
        return "No Component Type ID."

    signinfo = signinfo if isinstance(signinfo, dict) else {}

    merged_pids = _selected_pids_union(attach_pid, selected_pids)
    has_multi, subtitle, items_line = _build_selected_pid_summary(attach_pid, selected_pids, typeid)

    wd = _get_working_dir()
    out_dir = wd / str(typeid)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if has_multi:
        lo5, hi5 = _minmax_item_range_from_pids(merged_pids)
        pdf_name = f"ExecutiveSummary_{typeid}-{lo5}-{hi5}_{ts}.pdf" if (lo5 and hi5) else f"ExecutiveSummary_{typeid}_MULTI_{ts}.pdf"
    else:
        pdf_name = f"ExecutiveSummary_{attach_pid}_{ts}.pdf"

    pdf_path = out_dir / pdf_name

    # subtree
    sub_rows = _build_subcomponent_rows_recursive(attach_pid, cache_key=cache_key) or []
    subtree_lines = _subtree_to_lines(sub_rows)

    # Build a minimal PDF (no cfg, no plots, no references, no checklist)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    story = []

    # Title
    if has_multi and subtitle:
        title = f"Executive Summary — {escape(subtitle)}"
    else:
        title = f"Executive Summary — {escape(attach_pid)}"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 8))

    # Selected items
    story.append(Paragraph("<b>Selected Item Numbers</b>", styles["Normal"]))
    story.append(Paragraph(escape(items_line or "—"), styles["Normal"]))
    story.append(Spacer(1, 12))

    # Status + flags
    status_label = (signinfo.get("status_label") or "Unknown").strip() or "Unknown"
    cert_ok = bool(signinfo.get("certified_flag"))
    upl_ok = bool(signinfo.get("uploaded_flag"))

    story.append(Paragraph("Component Status", styles["Heading2"]))
    story.append(Paragraph(escape(status_label), styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("QA/QC Flags", styles["Heading2"]))
    def _pf(flag: bool):
        return '<font color="#19b478"><b>PASS</b></font>' if flag else '<font color="#dc3c3c"><b>FAIL</b></font>'
    story.append(Paragraph(f"Consortium Certified QA/QC: {_pf(cert_ok)}", styles["Normal"]))
    story.append(Paragraph(f"All QA/QC Uploaded: {_pf(upl_ok)}", styles["Normal"]))
    story.append(Spacer(1, 10))

    # Sign-off (single row)
    story.append(Paragraph("Sign-off", styles["Heading2"]))
    sig = (signinfo.get("signature") or "—").strip() or "—"
    com = (signinfo.get("comments") or "—").strip() or "—"
    tss = (signinfo.get("timestamp") or "—").strip() or "—"
    tbl = Table(
        [
            ["Signature", "Comments", "Sign-off date/time"],
            [sig, com, tss],
        ],
        colWidths=[140, 280, 120],
    )
    tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(tbl)

    # Sub-components
    story.append(PageBreak())
    story.append(Paragraph("Sub-components", styles["Heading1"]))
    story.append(Spacer(1, 8))
    if subtree_lines:
        mono = styles["Code"] if "Code" in styles else styles["Normal"]
        story.append(Preformatted("\n".join(subtree_lines[:2000]), mono))
    else:
        story.append(Paragraph("—", styles["Normal"]))

    doc.build(story)

    # Upload (same routing as your current upload_pdf_to_hwdb)
    try:
        resp = upload_pdf_to_hwdb(
            pid=attach_pid,
            typeid=str(typeid),
            pdf_path=pdf_path,
            selected_pids=merged_pids,
        )
    except Exception as e:
        return f"Saved locally: {pdf_path} — upload failed: {e}"

    img_id = None
    try:
        if isinstance(resp, dict):
            d = resp.get("data")
            if isinstance(d, dict):
                img_id = d.get("image_id") or d.get("id")
            elif isinstance(d, list) and d and isinstance(d[0], dict):
                img_id = d[0].get("image_id") or d[0].get("id")
    except Exception:
        img_id = None

    if img_id:
        return f"Saved locally: {pdf_path} — uploaded to HWDB (image_id={img_id})"
    return f"Saved locally: {pdf_path} — uploaded to HWDB"
def _do_generate_and_upload_pdf(
    *,
    selected_pid: str,
    cache_key: str | None,
    typeid: str | None,
    cfg: dict | None,
    status_label: str | None,
    certified_flag: bool,
    uploaded_flag: bool,
    whoami_name: str | None,
    es_existing: list[dict] | None,
    selected_pids: list[str] | None,
    todos_state: dict | None,
) -> str:
    if not selected_pid:
        return "No PID selected."
    if not cfg:
        return "No config loaded."

    attach_pid = str(selected_pid).strip()
    if not attach_pid:
        return "No PID selected."

    typeid = (typeid or "").strip()
    if not typeid:
        return "No Component Type ID."

    merged_pids = _selected_pids_union(attach_pid, selected_pids)
    has_multi, subtitle, items_line = _build_selected_pid_summary(attach_pid, selected_pids, typeid)
    
    # Re-create desc_text
    desc_cfg = (cfg or {}).get("test_description") or {}
    if isinstance(desc_cfg, dict):
        desc_text = (desc_cfg.get("default_text") or desc_cfg.get("label") or "").strip()
    else:
        desc_text = str(desc_cfg).strip()
    if not desc_text:
        desc_text = "—"

    # Prepare save path
    wd = _get_working_dir()
    out_dir = wd / str(typeid)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    #pdf_path = out_dir / f"ExecutiveSummary_{attach_pid}_{ts}.pdf"
    
    # multi-PID filename: ExecutiveSummary_<TypeID>-<minItem>-<maxItem>_<ts>.pdf
    if has_multi:
        lo5, hi5 = _minmax_item_range_from_pids(merged_pids)
        if lo5 and hi5:
            pdf_name = f"ExecutiveSummary_{typeid}-{lo5}-{hi5}_{ts}.pdf"
        else:
            # fallback (should be rare): no parseable item numbers
            pdf_name = f"ExecutiveSummary_{typeid}_MULTI_{ts}.pdf"
    else:
        pdf_name = f"ExecutiveSummary_{attach_pid}_{ts}.pdf"

    pdf_path = out_dir / pdf_name

    # sub-components
    sub_rows = _build_subcomponent_rows_recursive(attach_pid, cache_key=cache_key) or []
    subtree_lines = _subtree_to_lines(sub_rows)

    # Build plot blocks
    plot_blocks = _build_plot_blocks_for_pdf(
        cfg=cfg,
        cache_key=cache_key,
        fallback_pid=attach_pid,
        pids_to_plot=[attach_pid],
        sub_rows=sub_rows,
    )

    # Use what the UI already knows! (avoids HWDB “not updated yet” race)
    es_list = es_existing or []

    type_name = _fetch_type_name(str(typeid))

    # Create PDF locally
    try:
        _make_execsum_pdf(
            pdf_path,
            pid=attach_pid,
            typeid=str(typeid),
            cfg=cfg,
            form={
                "description": desc_text,
                "status_label": (status_label or "Unknown"),
                "certified_flag": bool(certified_flag),
                "uploaded_flag": bool(uploaded_flag),
                "type_name": type_name,
                "es_list": es_list,
                "has_multi": has_multi,
                "subtitle": subtitle,
                "selected_items_line": items_line,
                "todos_state": todos_state,
            },
            plot_blocks=plot_blocks,
            subtree_lines=subtree_lines,
        )
    except Exception as e:
        logger.error(f"[ExecSum] PDF build failed: {e}")
        return f"PDF build failed: {e}"

    # Upload to HWDB
    try:
        #resp = upload_pdf_to_hwdb(attach_pid, pdf_path)
        resp = upload_pdf_to_hwdb(
            pid=attach_pid,
            typeid=str(typeid),
            pdf_path=pdf_path,
            selected_pids=merged_pids,
        )
    except NotImplementedError as e:
        return f"Saved locally: {pdf_path} — upload not wired yet ({e})"
    except Exception as e:
        logger.error(f"[ExecSum] Upload failed: {e}")
        return f"Saved locally: {pdf_path} — upload failed: {e}"

    # Extract image ID if present
    img_id = None
    try:
        if isinstance(resp, dict):
            d = resp.get("data")
            if isinstance(d, dict):
                img_id = d.get("image_id") or d.get("id")
            elif isinstance(d, list) and d and isinstance(d[0], dict):
                img_id = d[0].get("image_id") or d[0].get("id")
    except Exception:
        img_id = None

    if img_id:
        return f"Saved locally: {pdf_path} — uploaded to HWDB (image_id={img_id})"
    return f"Saved locally: {pdf_path} — uploaded to HWDB"

# ----------------------------
# Helper for "show_details()"
# ----------------------------
def _build_details_payload(
    *,
    pid: str,
    cache_key: str | None,
    cfg: dict | None,
    table_data: list,
    whoami_name: str | None,
    signoff_dt: str | None,
    selected_pids: list[str] | None,
    todos_state: dict | None,
    mode: str = "detail",
    has_config: bool = True,
):
    pid = (pid or "").strip()
    mode = (mode or "detail").strip().lower()

    # Force DEFAULT if config is missing
    if (not has_config) or (not cfg):
        mode = "default"

    if not pid or not table_data:
        return (DETAILS_STYLE_HIDDEN, [], [])

    # ---------- shared: title + selected items summary ----------
    typeid_here = ""
    try:
        if cache_key and cache_key in _execsum_cache:
            typeid_here = str(_execsum_cache[cache_key].get("typeid") or "").strip()
    except Exception:
        typeid_here = ""

    has_multi, subtitle, items_line = _build_selected_pid_summary(pid, selected_pids, typeid_here)

    if has_multi and subtitle:
        title_text = f"Executive Summary — {subtitle}"
    else:
        title_text = f"Executive Summary — {pid}"

    title_block = html.Div(
        title_text,
        style={
            "textAlign": "center",
            "fontWeight": "900",
            "fontSize": "34px",
            "marginBottom": "6px",
            "color": "#0b3d91",
        }
    )

    selected_items_block = html.Div(
        [
            html.Div(
                "Selected Item Numbers",
                style={"fontWeight": "900", "fontSize": "14px", "opacity": 0.85},
            ),
            html.Div(
                items_line or "—",
                style={
                    "marginTop": "4px",
                    "fontFamily": "Menlo, Monaco, Consolas, monospace",
                    "fontSize": "14px",
                    "padding": "8px 10px",
                    "borderRadius": "10px",
                    "border": "1px solid #d6e4ff",
                    "backgroundColor": "#f5f9ff",
                    "color": "#123",
                    "wordBreak": "break-word",
                    "whiteSpace": "normal",
                },
            ),
        ],
        style={"marginBottom": "10px"},
    )

    # ---------- shared: Status pane ----------
    current_status_text = "—"
    try:
        if cache_key and cache_key in _execsum_cache:
            it = (_execsum_cache[cache_key]["by_pid"].get(pid, {}) or {}).get("item", {}) or {}
            current_status_text = str(_safe(it.get("status", ""))).strip() or "—"
    except Exception:
        current_status_text = "—"

    status_pane = html.Div(
        [
            html.Div("Status", style={"fontWeight": "900", "fontSize": "22px", "marginBottom": "8px"}),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Current (HWDB)", style={"fontWeight": "800", "opacity": 0.85}),
                            html.Div(current_status_text, style={"fontSize": "20px", "fontWeight": "900", "marginTop": "4px"}),
                        ],
                        style={"flex": "1 1 45%"},
                    ),
                    html.Div(
                        [
                            html.Div("Set to", style={"fontWeight": "800", "opacity": 0.85}),
                            dcc.Dropdown(
                                id="execsum-status-dropdown",
                                options=STATUS_OPTIONS,
                                value=None,
                                clearable=False,
                                placeholder="Select status…",
                            ),
                        ],
                        style={"flex": "1 1 55%"},
                    ),
                ],
                style={"display": "flex", "gap": "14px", "alignItems": "center"},
            ),
        ],
        style={
            "backgroundColor": "#EEF5FF",
            "border": "2px solid #4A90E2",
            "borderRadius": "12px",
            "padding": "12px 14px",
            "marginTop": "6px",
            "marginBottom": "6px",
        }
    )

    flags_block = html.Div(
        style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "14px", "marginTop": "10px"},
        children=[
            html.Div(
                id="execsum-flag-certified-card",
                className="execsum-flag-card",
                children=[
                    html.Div("Consortium Certified QA/QC", className="execsum-flag-subtitle"),
                    dbc.Switch(
                        id="execsum-flag-certified",
                        label="PASS",
                        value=False,
                        className="execsum-flag-switch",
                    ),
                ],
            ),
            html.Div(
                id="execsum-flag-uploaded-card",
                className="execsum-flag-card",
                children=[
                    html.Div("All QA/QC Test and Documentation Uploaded", className="execsum-flag-subtitle"),
                    dbc.Switch(
                        id="execsum-flag-uploaded",
                        label="PASS",
                        value=False,
                        className="execsum-flag-switch",
                    ),
                ],
            ),
        ]
    )

    # =========================================================
    # DEFAULT MODE
    # =========================================================
    if mode == "default":
        who = (whoami_name or "—").strip() or "—"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        # dummy checklist so update_todos_state callback doesn't break
        dummy_checklist = dbc.Checklist(
            id="execsum-todos-checklist",
            options=[],
            value=[],
            style={"display": "none"},
        )

        default_sig_section = html.Div(
            [
                html.Div("Sign-off", style={"fontWeight": "800", "fontSize": "22px"}),
                html.Div(
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "220px 1fr 220px",
                        "columnGap": "10px",
                        "rowGap": "6px",
                        "alignItems": "center",
                        "marginTop": "10px",
                    },
                    children=[
                        html.Div("Signature", style={"fontWeight": "800"}),
                        dcc.Input(
                            id="execsum-default-signature",
                            value=who,
                            disabled=True,
                            style={
                                "width": "100%",
                                "height": "40px",
                                "borderRadius": "10px",
                                "border": "1px solid #CCC",
                                "padding": "8px 10px",
                            },
                        ),
                        dbc.Button(
                            "Sign & Update HWDB",
                            id="execsum-default-sign-btn",
                            n_clicks=0,
                            color="primary",
                            style={"fontWeight": "800"},
                        ),
                        html.Div("Comments", style={"fontWeight": "800"}),
                        dcc.Textarea(
                            id="execsum-default-comments",
                            value=f"signed by {who}".strip(),
                            style={
                                "gridColumn": "2 / 4",
                                "width": "100%",
                                "height": "70px",
                                "borderRadius": "10px",
                                "border": "1px solid #CCC",
                                "padding": "10px",
                                "resize": "vertical",
                            },
                        ),
                        html.Div("Sign-off date/time", style={"fontWeight": "800"}),
                        html.Div(
                            now_str,
                            id="execsum-default-ts",
                            style={"fontWeight": "900"},
                        ),
                    ],
                ),
            ],
            style={
                "backgroundColor": "#FFF7E6",
                "border": "2px solid #F0B35A",
                "borderRadius": "12px",
                "padding": "12px 14px",
                "marginTop": "6px",
            },
        )

        form_children = html.Div(
            style={"display": "flex", "flexDirection": "column", "gap": "10px"},
            children=[
                dummy_checklist,
                status_pane,
                flags_block,
                default_sig_section,
            ],
        )

        return (DETAILS_STYLE_VISIBLE, [title_block, selected_items_block, form_children], [])

    # =========================================================
    # DETAIL MODE (your original behavior)
    # =========================================================

    # Safety for detail mode
    if not cfg:
        return (DETAILS_STYLE_HIDDEN, [], [])

    consortium_name = (cfg.get("consortium_name") or "").strip() or "—"

    desc_raw = cfg.get("test_description")
    if isinstance(desc_raw, dict):
        test_description = (desc_raw.get("default_text") or desc_raw.get("label") or "").strip()
    else:
        test_description = (desc_raw or "").strip()
    test_description = test_description or "—"

    # TODOS / QC checks
    todos_state = todos_state if isinstance(todos_state, dict) else {}
    if not todos_state.get("check_list"):
        todos_cfg = (cfg or {}).get("todos") or {}
        todos_state = {
            "title": str(todos_cfg.get("title") or "").strip(),
            "check_list": (todos_cfg.get("check_list") or []),
            "checked": [],
        }

    todos_title = str(todos_state.get("title") or "").strip()
    todos_list = todos_state.get("check_list") or []
    todos_checked = todos_state.get("checked") or []

    if not isinstance(todos_list, list):
        todos_list = []
    if not isinstance(todos_checked, list):
        todos_checked = []

    options = [{"label": str(txt), "value": i} for i, txt in enumerate(todos_list)]

    todos_section = html.Div(
        [
            html.Div(todos_title or "QC Checks", style={"fontWeight": "900", "fontSize": "22px", "marginBottom": "8px"}),
            dbc.Checklist(
                id="execsum-todos-checklist",
                options=options,
                value=[int(i) for i in todos_checked if str(i).isdigit() and 0 <= int(i) < len(todos_list)],
                inputStyle={"marginRight": "10px"},
                labelStyle={"display": "block", "fontWeight": "700", "marginBottom": "6px"},
                style={"paddingLeft": "4px"},
            ),
        ],
        style={
            "backgroundColor": "#F6FBF6",
            "border": "2px solid #9BD3AE",
            "borderRadius": "12px",
            "padding": "12px 14px",
            "marginTop": "6px",
            "marginBottom": "6px",
        }
    )

    header_rows = html.Div(
        [
            html.Div(
                [html.Span("Consortium: ", style={"fontWeight": "900"}), html.Span(consortium_name)],
                style={"fontSize": "22px", "fontWeight": "700", "color": "#0b3d91"},
            ),
            html.Div(
                [html.Span("Description: ", style={"fontWeight": "900"}), html.Span(test_description)],
                style={"fontSize": "20px", "fontWeight": "700", "color": "#111", "marginTop": "6px"},
            ),
        ],
        style={"marginBottom": "10px"},
    )

    
    # ---------- Signees ----------
    signees = (cfg.get("signees") or [])

    def _rk(s):
        try:
            return int(s.get("rank", -1))
        except Exception:
            return -1

    # Display in the order of signing:
    #   1) all negative ranks first (any order)
    #   2) then non-negative ranks in descending order (rank 0 last)
    def _sig_sort_key(s):
        rk = _rk(s)
        if rk < 0:
            return (0, 0, (s.get("name") or ""))   # negatives first; stable by name
        return (1, -rk, (s.get("name") or ""))     # then rank desc

    signees_sorted = sorted(
        [s for s in signees if isinstance(s, dict)],
        key=_sig_sort_key
    )

    # --- role gating helpers (render-time, no extra callbacks needed) ---
    user_role_ids = _whoami_role_ids()           # set[int]
    role_map = _get_role_name_map()              # {id:int -> name:str}

    def _required_role_ids_for_signee(sig_cfg: dict) -> list[int]:
        rr = sig_cfg.get("roles", [])
        out = []
        if isinstance(rr, list):
            for x in rr:
                try:
                    out.append(int(x))
                except Exception:
                    pass
        return out

    def _role_requirement_message(req_ids: list[int]) -> str:
        # message shown to user; empty means no restriction
        if not req_ids:
            return ""
        names = []
        for rid in req_ids:
            nm = role_map.get(int(rid))
            names.append(nm if nm else f"(id={rid})")
        return "This signee is required to have one the following User Role(s): " + ", ".join(names)

    def _role_ok(req_ids: list[int]) -> bool:
        if not req_ids:
            return True
        return bool(set(req_ids) & set(user_role_ids))

    
    signee_rows = []
    for s in signees_sorted:
        nm = (s.get("name") or "").strip()
        rk = _rk(s)

        # compute per-signee role restriction message NOW (visible before click)
        req_role_ids = _required_role_ids_for_signee(s)
        req_msg = _role_requirement_message(req_role_ids)
        ok_for_roles = _role_ok(req_role_ids)

        # If restricted and user lacks role, show message in red; if user is OK, show message in muted color (or hide)
        # always show requirement line when there are required roles
        show_req = bool(req_role_ids)

        req_style = {
            "gridColumn": "2 / 4",
            "gridRow": "5",
            "fontWeight": "800",
            "marginTop": "2px",
            "paddingTop": "2px",
            "display": "block" if show_req else "none",
            "color": "#a33" if (show_req and not ok_for_roles) else "#666",
        }

        # Optional little badge to make it obvious
        badge = None
        if show_req:
            badge = html.Span(
                "NOT AUTHORIZED" if not ok_for_roles else "ROLE REQUIREMENT",
                style={
                    "display": "inline-block",
                    "marginRight": "8px",
                    "padding": "2px 8px",
                    "borderRadius": "999px",
                    "fontSize": "12px",
                    "fontWeight": "900",
                    "backgroundColor": "#ffe3e3" if not ok_for_roles else "#eef5ff",
                    "color": "#a33" if not ok_for_roles else "#0b3d91",
                    "border": "1px solid #f0b0b0" if not ok_for_roles else "1px solid #b9d6ff",
                    "verticalAlign": "middle",
                },
            )

        signee_rows.append(
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "220px 1fr 220px",
                    "columnGap": "10px",
                    "rowGap": "6px",
                    "alignItems": "center",
                },
                children=[
                    html.Div(nm, style={"fontWeight": "800", "gridColumn": "1 / 2", "gridRow": "1"}),

                    dcc.Input(
                        id={"type": "execsum-signee-input", "name": nm},
                        type="text",
                        placeholder=f"Type signature for {nm}",
                        style={
                            "width": "100%",
                            "height": "40px",
                            "borderRadius": "10px",
                            "border": "1px solid #CCC",
                            "padding": "8px 10px",
                            "gridColumn": "2 / 3",
                            "gridRow": "1",
                        },
                    ),

                    dbc.Button(
                        "Upload this signature",
                        id={"type": "execsum-signee-upload", "name": nm},
                        n_clicks=0,
                        color="primary",
                        disabled=True,  # enabled by your status callback
                        style={"gridColumn": "3 / 4", "gridRow": "1"},
                    ),

                    html.Div(
                        "Comments",
                        style={
                            "gridColumn": "2 / 3",
                            "gridRow": "2",
                            "fontWeight": "700",
                            "opacity": 0.9,
                        },
                    ),
                    dcc.Textarea(
                        id={"type": "execsum-signee-comments", "name": nm},
                        placeholder=f"Optional comments for {nm}...",
                        value="",
                        style={
                            "gridColumn": "2 / 4",
                            "gridRow": "3",
                            "width": "100%",
                            "height": "70px",
                            "borderRadius": "10px",
                            "border": "1px solid #CCC",
                            "padding": "10px",
                            "resize": "vertical",
                        },
                    ),

                    html.Div(
                        "Sign-off date/time",
                        style={
                            "gridColumn": "2 / 3",
                            "gridRow": "4",
                            "fontWeight": "700",
                            "opacity": 0.9,
                            "paddingTop": "2px",
                        }
                    ),
                    html.Div(
                        id={"type": "execsum-signee-ts", "name": nm},
                        children="—",
                        style={
                            "gridColumn": "3 / 4",
                            "gridRow": "4",
                            "fontWeight": "800",
                            "color": "#333",
                            "textAlign": "left",
                            "paddingTop": "2px",
                        },
                    ),

                    # NEW: role requirement line (shows before click)
                    html.Div(
                        [badge, html.Span(req_msg)],
                        style=req_style,
                    ),

                    html.Div(str(rk), id={"type": "execsum-signee-rank", "name": nm}, style={"display": "none"}),
                    dcc.Store(id={"type": "execsum-signee-ts-store", "name": nm}, storage_type="memory"),
                ],
            )
        )

    signee_section = html.Div(
        [
            html.Div("Sign-off by", style={"fontWeight": "800", "fontSize": "22px"}),
            html.Div(
                signee_rows,
                style={"marginTop": "10px", "display": "flex", "flexDirection": "column", "gap": "10px"},
            ),
        ],
        style={
            "backgroundColor": "#FFF7E6",
            "border": "2px solid #F0B35A",
            "borderRadius": "12px",
            "padding": "12px 14px",
            "marginTop": "6px",
        }
    )

    header_rows = html.Div(
        [
            html.Div(
                [html.Span("Consortium: ", style={"fontWeight": "900"}), html.Span(consortium_name)],
                style={"fontSize": "22px", "fontWeight": "700", "color": "#0b3d91"},
            ),
            html.Div(
                [html.Span("Description: ", style={"fontWeight": "900"}), html.Span(test_description)],
                style={"fontSize": "20px", "fontWeight": "700", "color": "#111", "marginTop": "6px"},
            ),
        ],
        style={"marginBottom": "10px"},
    )

    current_status_text = "—"
    try:
        if cache_key and cache_key in _execsum_cache:
            it = (_execsum_cache[cache_key]["by_pid"].get(pid, {}) or {}).get("item", {}) or {}
            current_status_text = str(_safe(it.get("status", ""))).strip() or "—"
    except Exception:
        current_status_text = "—"

    status_pane = html.Div(
        [
            html.Div("Status", style={"fontWeight": "900", "fontSize": "22px", "marginBottom": "8px"}),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Current (HWDB)", style={"fontWeight": "800", "opacity": 0.85}),
                            html.Div(current_status_text, style={"fontSize": "20px", "fontWeight": "900", "marginTop": "4px"}),
                        ],
                        style={"flex": "1 1 45%"},
                    ),
                    html.Div(
                        [
                            html.Div("Set to", style={"fontWeight": "800", "opacity": 0.85}),
                            dcc.Dropdown(
                                id="execsum-status-dropdown",
                                options=STATUS_OPTIONS,
                                value=None,  # filled by your existing prefill callback
                                clearable=False,
                                placeholder="Select status…",
                            ),
                        ],
                        style={"flex": "1 1 55%"},
                    ),
                ],
                style={"display": "flex", "gap": "14px", "alignItems": "center"},
            ),
        ],
        style={
            "backgroundColor": "#EEF5FF",
            "border": "2px solid #4A90E2",
            "borderRadius": "12px",
            "padding": "12px 14px",
            "marginTop": "6px",
            "marginBottom": "6px",
        }
    )

    form_children = html.Div(
        style={"display": "flex", "flexDirection": "column", "gap": "10px"},
        children=[
            header_rows,
            todos_section,
            status_pane,
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "14px", "marginTop": "10px"},
                children=[
                    html.Div(
                        id="execsum-flag-certified-card",
                        className="execsum-flag-card",
                        children=[
                            html.Div("Consortium Certified QA/QC", className="execsum-flag-subtitle"),
                            dbc.Switch(
                                id="execsum-flag-certified",
                                label="PASS",
                                value=False,
                                className="execsum-flag-switch",
                            ),
                        ],
                    ),
                    html.Div(
                        id="execsum-flag-uploaded-card",
                        className="execsum-flag-card",
                        children=[
                            html.Div("All QA/QC Test and Documentation Uploaded", className="execsum-flag-subtitle"),
                            dbc.Switch(
                                id="execsum-flag-uploaded",
                                label="PASS",
                                value=False,
                                className="execsum-flag-switch",
                            ),
                        ],
                    ),
                ]
            ),
            build_reference_urls_section(cfg),
            signee_section,
        ]
    )

    # ---------- Plots ----------
    plots_cfg = cfg.get("plots") or []
    plot_divs = []

    # Build subtree rows once so plots can resolve sub_part_id
    sub_rows_for_plot = _build_subcomponent_rows_recursive(pid, cache_key=cache_key) or []

    for p in plots_cfg:
        if not isinstance(p, dict):
            continue

        test_type_name = (p.get("test_type_name") or "").strip()
        title = p.get("title", "Plot")

        # Resolve single_pid (your existing logic)
        single_pid = None
        spi = p.get("sub_part_id")
        if isinstance(spi, dict):
            resolved = _resolve_pid_from_sub_part_id(
                sub_rows_for_plot,
                layer=spi.get("layer"),
                pos_name=spi.get("pos_name"),
            )
            single_pid = resolved or pid
        else:
            single_pid = (p.get("part_id") or "").strip() or pid

        # -------------------------
        # image_path handling
        # -------------------------
        ip = p.get("image_path")
        if isinstance(ip, dict) and (ip.get("image_name") or "").strip():
            image_name = (ip.get("image_name") or "").strip()
            try:
                history_order = int(ip.get("history_order") or 0)
            except Exception:
                history_order = 0

            plot_divs += build_image_plot_div(
                title=title,
                test_type_name=test_type_name,
                pid=single_pid,
                cache_key=cache_key,
                image_name=image_name,
                history_order=history_order,
            )
            continue

        # -------------------------
        # Existing numeric plots
        # -------------------------
        paths = p.get("data_paths") or []
        bins = int(p.get("bins", 40))
        do_sum = bool(p.get("sum", False))

        label_hint = f"single PID {single_pid}"
        if isinstance(spi, dict):
            label_hint = f"single PID {single_pid} (from sub_part_id layer={spi.get('layer')}, pos='{spi.get('pos_name')}')"

        plot_divs += build_plot_divs(
            title=title,
            test_type_name=test_type_name,
            paths=paths,
            bins=bins,
            pids_for_plot=[single_pid],
            cache_key=cache_key,
            label=label_hint,
        )

        if do_sum:
            typeid_for_sum = _typeid12_from_pid(single_pid)
            sum_pids = _get_pids_for_typeid(cache_key, typeid_for_sum) or [single_pid]
            plot_divs += build_plot_divs(
                title=title,
                test_type_name=test_type_name,
                paths=paths,
                bins=bins,
                pids_for_plot=sum_pids,
                cache_key=cache_key,
                label=f"sum over TypeID {typeid_for_sum} (N={len(sum_pids)})",
            )

    
    # derive typeid for subtitle (prefer cache -> fallback cfg)
    typeid_here = ""
    try:
        if cache_key and cache_key in _execsum_cache:
            typeid_here = str(_execsum_cache[cache_key].get("typeid") or "").strip()
    except Exception:
        typeid_here = ""
    if not typeid_here:
        typeid_here = str((cfg or {}).get("component_type_id") or "").strip()

    has_multi, subtitle, items_line = _build_selected_pid_summary(pid, selected_pids, typeid_here)

    # Title format:
    #  - single: "Executive Summary — <root pid>"
    #  - multi:  "Executive Summary — <TypeID>-<min>-<max>"
    if has_multi and subtitle:
        title_text = f"Executive Summary — {subtitle}"
    else:
        title_text = f"Executive Summary — {pid}"

    title_block = html.Div(
        title_text,
        style={
            "textAlign": "center",
            "fontWeight": "900",
            "fontSize": "34px",
            "marginBottom": "6px",
            "color": "#0b3d91",
        }
    )

    # Add selected items line (between title and consortium)
    selected_items_block = html.Div(
        [
            html.Div(
                "Selected Item Numbers",
                style={"fontWeight": "900", "fontSize": "14px", "opacity": 0.85},
            ),
            html.Div(
                items_line,
                style={
                    "marginTop": "4px",
                    "fontFamily": "Menlo, Monaco, Consolas, monospace",
                    "fontSize": "14px",
                    "padding": "8px 10px",
                    "borderRadius": "10px",
                    "border": "1px solid #d6e4ff",
                    "backgroundColor": "#f5f9ff",
                    "color": "#123",
                    "wordBreak": "break-word",
                    "whiteSpace": "normal",
                },
            ),
        ],
        style={"marginBottom": "10px"},
    )
            


    #form_block_children = [title_block, form_children]
    form_block_children = [title_block, selected_items_block, form_children]

    return (DETAILS_STYLE_VISIBLE, form_block_children, plot_divs)

# ----------------------------
# Build Plots in PDF in the same way as in Dashboard
# ----------------------------
def _build_plot_blocks_for_pdf(*, cfg: dict, cache_key: str | None, fallback_pid: str,
                               pids_to_plot: list[str], sub_rows: list[dict] | None):
    """
    Build plot_blocks that mirror what the dashboard shows:
      - If plot has image_path -> embed that image (no Plotly)
      - else -> normal numeric plots (Plotly) + optional sum plots
    """
    plot_blocks = []

    for p in (cfg.get("plots") or []):
        if not isinstance(p, dict):
            continue

        test_type_name = (p.get("test_type_name") or "").strip()
        title = p.get("title", "Plot")
        paths = p.get("data_paths") or []
        bins = int(p.get("bins", 40))
        do_sum = bool(p.get("sum", False))

        # ---- Resolve single_pid (matches dashboard) ----
        single_pid = None
        spi = p.get("sub_part_id")
        if isinstance(spi, dict):
            resolved = _resolve_pid_from_sub_part_id(
                sub_rows or [],
                layer=spi.get("layer"),
                pos_name=spi.get("pos_name"),
            )
            single_pid = resolved or fallback_pid
        else:
            single_pid = (p.get("part_id") or "").strip() or fallback_pid

        # ------------------------------------------------
        # image_path plots (ignore data_paths)
        # ------------------------------------------------
        ip = p.get("image_path")
        if isinstance(ip, dict) and (ip.get("image_name") or "").strip():
            image_name = (ip.get("image_name") or "").strip()
            try:
                history_order = int(ip.get("history_order") or 0)
            except Exception:
                history_order = 0

            img_bytes, img_mime, err = _get_test_attached_image_bytes(
                cache_key=cache_key,
                pid=single_pid,
                test_type_name=test_type_name,
                image_name=image_name,
                history_order=history_order,
            )

            plot_blocks.append({
                "title": f"{title} (single PID {single_pid})",
                "test_type_name": test_type_name,
                "data_paths": [],  # ignored for images
                "note": err or f"Image: {image_name} (history_order={history_order})",
                "fig": None,
                "stats": {"text_lines": []},
                "image_name": image_name,
                "image_mime": img_mime,
                "image_bytes": img_bytes,   # <-- THE KEY THING
            })

            # IMPORTANT: images do not participate in "sum" plots
            continue

        # ------------------------------------------------
        # Existing numeric plots (unchanged behavior)
        # ------------------------------------------------
        plot_blocks.append(
            _one_plot_block_for_pdf(
                title=title,
                test_type_name=test_type_name,
                paths=paths,
                bins=bins,
                pids_for_plot=[single_pid],
                cache_key=cache_key,
                label=f"single PID {single_pid}",
            )
        )

        if do_sum:
            typeid_for_sum = _typeid12_from_pid(single_pid)
            if not typeid_for_sum:
                typeid_for_sum = _pid_type_prefix(single_pid)

            sum_pids = _get_pids_for_typeid(cache_key, typeid_for_sum) or [single_pid]

            plot_blocks.append(
                _one_plot_block_for_pdf(
                    title=title,
                    test_type_name=test_type_name,
                    paths=paths,
                    bins=bins,
                    pids_for_plot=sum_pids,
                    cache_key=cache_key,
                    label=f"sum over TypeID {typeid_for_sum} (N={len(sum_pids)})",
                )
            )

    return [b for b in plot_blocks if isinstance(b, dict)]


def _one_plot_block_for_pdf(*, title: str, test_type_name: str, paths: list[str], bins: int,
                            pids_for_plot: list[str], cache_key: str | None, label: str) -> dict:
    """
    Returns one plot_block dict:
      {"title","test_type_name","data_paths","note","fig","stats"}
    """
    fig = None
    note = None
    stats = {"text_lines": []}

    # prefetch to avoid repeated calls (optional but helps)
    if cache_key and test_type_name:
        _prefetch_tests(cache_key, pids_for_plot, test_type_name)

    if len(paths) == 1:
        df1 = _collect_1d_series_from_selected(cache_key, pids_for_plot, test_type_name, paths[0])

        if df1.empty:
            note = f"No data found across {len(pids_for_plot)} PID(s) for '{test_type_name}'."
        else:
            num = pd.to_numeric(df1["value"], errors="coerce")
            numeric_ratio = num.notna().sum() / max(len(df1), 1)

            if numeric_ratio > 0.8:
                df1["value_num"] = num
                fig = px.histogram(df1, x="value_num", nbins=bins or 40)
                fig.update_layout(title=f"{title} — {label}", height=320)
                stats = stats_hist(df1["value_num"].dropna().tolist())
            else:
                df1["value_cat"] = df1["value"].map(lambda x: "True" if x is True else ("False" if x is False else str(x)))
                fig = px.histogram(df1, x="value_cat")
                fig.update_layout(title=f"{title} — {label}", height=320)
                vc = df1["value_cat"].value_counts(dropna=True)
                stats = {"text_lines": [f"N = {len(df1)}", f"unique = {vc.size}"] + [f"{k}: {v}" for k, v in vc.head(8).items()]}
                fig.update_xaxes(tickangle=-25)

    elif len(paths) == 2:
        X_all, Y_all = [], []
        for pid in (pids_for_plot or []):
            tb = _get_test_cached(cache_key, pid, test_type_name) if cache_key else fetch_test_blob(pid, test_type_name)
            if not tb:
                continue
            x = _get_by_path(tb, paths[0])
            y = _get_by_path(tb, paths[1])
            X = _flatten_numeric(x)
            Y = _flatten_numeric(y)
            n = min(len(X), len(Y))
            if n > 0:
                X_all += X[:n]
                Y_all += Y[:n]

        if not X_all or not Y_all:
            note = f"No numeric (x,y) pairs found across {len(pids_for_plot)} PID(s) for '{test_type_name}'."
        else:
            fig = make_scatter(X_all, Y_all, title=f"{title} — {label}")
            stats = stats_scatter(X_all, Y_all)

    else:
        note = "Invalid config: data_paths must have length 1 (hist/categorical) or 2 (scatter)."

    return {
        "title": f"{title} ({label})",
        "test_type_name": test_type_name,
        "data_paths": paths,
        "note": note,
        "fig": fig,
        "stats": stats,
    }


# ----------------------------
# Add "stats" of plots
# ----------------------------
def _is_number(x) -> bool:
    # avoid True/False counting as 1/0
    return isinstance(x, (int, float, np.number)) and not isinstance(x, bool)

def _to_float(x):
    if _is_number(x):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except Exception:
            return None
    return None

def _flatten_numeric(value):
    """
    Flattens nested lists of numbers into a simple list[float].
    Accepts scalars, lists, list-of-lists. Ignores dicts by default.
    """
    out = []

    def rec(v):
        if v is None:
            return
        f = _to_float(v)
        if f is not None:
            out.append(f)
            return
        if isinstance(v, (list, tuple, np.ndarray)):
            for t in v:
                rec(t)

    rec(value)
    return out

def _fmt(x, nd=4):
    if x is None:
        return "—"
    try:
        # compact format: 4 sig-ish digits
        return f"{float(x):.{nd}g}"
    except Exception:
        return str(x)

def stats_hist(values):
    vals = _flatten_numeric(values)
    if len(vals) == 0:
        return {"text_lines": ["No data found."]}

    a = np.array(vals, dtype=float)
    lines = [
        f"N = {len(a)}",
        f"min = {_fmt(np.min(a))}",
        f"median = {_fmt(np.median(a))}",
        f"mean = {_fmt(np.mean(a))}",
        f"std = {_fmt(np.std(a, ddof=1)) if len(a) > 1 else '—'}",
        f"max = {_fmt(np.max(a))}",
    ]
    # optional percentiles (nice for skewed distributions)
    p10, p90 = np.percentile(a, [10, 90])
    lines.append(f"p10 / p90 = {_fmt(p10)} / {_fmt(p90)}")
    return {"text_lines": lines}

def stats_scatter(xs, ys):
    X = _flatten_numeric(xs)
    Y = _flatten_numeric(ys)
    n = min(len(X), len(Y))
    if n == 0:
        return {"text_lines": ["No (x,y) pairs found."]}

    X = np.array(X[:n], dtype=float)
    Y = np.array(Y[:n], dtype=float)

    lines = [
        f"N = {n}",
        f"x[min,max] = {_fmt(np.min(X))}, {_fmt(np.max(X))}",
        f"y[min,max] = {_fmt(np.min(Y))}, {_fmt(np.max(Y))}",
    ]

    if n >= 2:
        # Pearson correlation
        try:
            r = float(np.corrcoef(X, Y)[0, 1])
            lines.append(f"corr (Pearson r) = {_fmt(r)}")
        except Exception:
            lines.append("corr (Pearson r) = —")

        # simple linear fit (y = m x + b)
        try:
            m, b = np.polyfit(X, Y, 1)
            lines.append(f"fit: y = m x + b,  m={_fmt(m)}, b={_fmt(b)}")
        except Exception:
            lines.append("fit: —")

    return {"text_lines": lines}

# ----------------------------
# Render clickable links in PDF
# ----------------------------
def _pdf_reference_block(cfg: dict, styles, *, include_header: bool = True):
    """
    Returns a list of Platypus flowables that render clickable references.
    Format: cfg["references"] = [{"url":..., "comments":...}, ...]
    """
    flows = []

    refs = cfg.get("references", [])

    # Optional header (lets caller put a big Heading1 on the page)
    if include_header:
        flows.append(Paragraph("Reference URLs", styles["Heading2"]))
        flows.append(Spacer(1, 6))

    if isinstance(refs, list):
        any_added = False
        for r in refs:
            if not isinstance(r, dict):
                continue
            url = (r.get("url") or "").strip()
            comments = (r.get("comments") or "").strip()
            if not url:
                continue

            any_added = True
            url_esc = escape(url)

            flows.append(
                Paragraph(
                    f'&#8226; <a href="{url_esc}" color="blue">{url_esc}</a>',
                    styles["Normal"],
                )
            )

            if comments:
                flows.append(
                    Paragraph(
                        f'<font color="#555555">&nbsp;&nbsp;&nbsp;&nbsp;{escape(comments)}</font>',
                        styles["Normal"],
                    )
                )
            flows.append(Spacer(1, 6))

        if not any_added:
            flows.append(Paragraph("—", styles["Normal"]))
        return flows

    flows.append(Paragraph("—", styles["Normal"]))
    return flows
# ----------------------------
# Build the sign-off table
# ----------------------------
def _build_signoff_table(cfg: dict, es_list: list[dict], styles):
    """
    Build the Sign-off table in the SAME order as the dashboard:

      1) all negative ranks first (any order; stable by name)
      2) then non-negative ranks in descending order (rank 0 last)
    """
    signees = [s for s in (cfg.get("signees") or []) if isinstance(s, dict)]
    es_map = _es_map_by_name(es_list or [])

    def _rk(s):
        try:
            return int(s.get("rank", -1))
        except Exception:
            return -1

    def _sig_sort_key(s):
        rk = _rk(s)
        # negatives first
        if rk < 0:
            return (0, 0, (s.get("name") or ""))
        # then non-negatives: rank desc
        return (1, -rk, (s.get("name") or ""))

    ordered = sorted(signees, key=_sig_sort_key)

    # table header
    data = [[
        Paragraph("<b>Position</b>", styles["Normal"]),
        Paragraph("<b>Signature</b>", styles["Normal"]),
        Paragraph("<b>Comments</b>", styles["Normal"]),
        Paragraph("<b>Sign-off date/time</b>", styles["Normal"]),
    ]]

    any_row = False
    for s in ordered:
        name = (s.get("name") or "").strip()
        ent = es_map.get(name) or {}
        sig = (ent.get("signature") or "").strip()
        com = (ent.get("comments") or "").strip()
        ts  = (ent.get("timestamp") or "").strip()

        if name or sig or com or ts:
            any_row = True

        data.append([
            Paragraph(escape(name) if name else "—", styles["Normal"]),
            Paragraph(escape(sig) if sig else "—", styles["Normal"]),
            Paragraph(escape(com) if com else "—", styles["Normal"]),
            Paragraph(escape(ts) if ts else "—", styles["Normal"]),
        ])

    if not any_row:
        return [Paragraph("—", styles["Normal"])]

    tbl = Table(data, colWidths=[110, 140, 190, 110])
    tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    return [tbl]

# ----------------------------
# Generate a PDF and write it to the selected path
# ----------------------------
def _make_execsum_pdf(
    pdf_path: Path,
    *,
    pid: str,
    typeid: str,
    cfg: dict,
    form: dict,
    plot_blocks: list[dict],
    subtree_lines: list[str] | None = None,
):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)

    story = []

    # ----------------------------
    # PAGE 1: Summary
    # ----------------------------
    #story.append(Paragraph(f"Executive Summary — PID {pid}", styles["Title"]))
    has_multi = bool(form.get("has_multi"))
    subtitle = (form.get("subtitle") or "").strip()
    selected_items_line = (form.get("selected_items_line") or "").strip() or "—"

    # Match detail-pane title style:
    #  - single: "Executive Summary — <root pid>"
    #  - multi:  "Executive Summary — <subtitle>"  (e.g. TypeID-min-max)
    if has_multi and subtitle:
        title = f"Executive Summary — {escape(subtitle)}"
    else:
        title = f"Executive Summary — {escape(pid)}"

    story.append(Paragraph(title, styles["Title"]))

    # Selection summary line right below title (before consortium/test description)
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Selected Item Numbers</b>", styles["Normal"]))
    story.append(Paragraph(escape(selected_items_line), styles["Normal"]))
    story.append(Spacer(1, 10))

    type_name = (form.get("type_name") or "").strip()
    if type_name:
        story.append(Paragraph(f'<para align="center"><b>{escape(type_name)}</b></para>', styles["Heading2"]))
        story.append(Spacer(1, 6))

    # Centered "Generated" line (right below Type Name)
    gen = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(f'<para align="center">Generated: {gen}</para>', styles["Normal"]))
    story.append(Spacer(1, 14))

    # Test Description
    story.append(Paragraph("Test Description", styles["Heading2"]))
    story.append(Paragraph(form.get("description", "—"), styles["Normal"]))
    story.append(Spacer(1, 10))

    # TODOS / QC checks
    todos_state = form.get("todos_state") or {}
    ttitle = (todos_state.get("title") or "").strip() or "QC Checks"
    clist = todos_state.get("check_list") or []
    checked = set(todos_state.get("checked") or [])

    story.append(Paragraph(escape(ttitle), styles["Heading2"]))
    story.append(Spacer(1, 6))
    if isinstance(clist, list) and clist:
        for i, txt in enumerate(clist):
            mark = "[x]" if i in checked else "[ ]"
            story.append(Paragraph(f"{mark} {escape(str(txt))}", styles["Normal"]))
    else:
        story.append(Paragraph("—", styles["Normal"]))
    story.append(Spacer(1, 10))
    
    # Sign-off table
    story.append(Paragraph("Sign-off by", styles["Heading2"]))
    story.append(Spacer(1, 6))
    story.extend(_build_signoff_table(cfg, form.get("es_list") or [], styles))
    story.append(Spacer(1, 10))

    # Component Status
    story.append(Paragraph("Component Status", styles["Heading2"]))
    status_label = (form.get("status_label") or "Unknown").strip() or "Unknown"
    story.append(Paragraph(escape(status_label), styles["Normal"]))
    story.append(Spacer(1, 10))

    # QA/QC Flags
    story.append(Paragraph("QA/QC Flags", styles["Heading2"]))

    cert_ok = bool(form.get("certified_flag"))
    upl_ok  = bool(form.get("uploaded_flag"))

    def _pf(flag: bool):
        if flag:
            return '<font color="#19b478"><b>PASS</b></font>'
        return '<font color="#dc3c3c"><b>FAIL</b></font>'

    story.append(Paragraph(f"Consortium Certified QA/QC: {_pf(cert_ok)}", styles["Normal"]))
    story.append(Paragraph(f"All QA/QC Uploaded: {_pf(upl_ok)}", styles["Normal"]))
    story.append(Spacer(1, 10))

    # ----------------------------
    # PAGE 2: Reference URLs (NEW PAGE)
    # ----------------------------
    story.append(PageBreak())
    story.append(Paragraph("Reference URLs", styles["Heading1"]))
    story.append(Spacer(1, 10))
    # call block without its own header to avoid double-titles
    story.extend(_pdf_reference_block(cfg, styles, include_header=False))

    # ----------------------------
    # PLOTS: 1 plot per page
    # ----------------------------
    if plot_blocks:
        # first plot page gets a big "Plots" title
        story.append(PageBreak())
        story.append(Paragraph("Plots", styles["Heading1"]))
        story.append(Spacer(1, 10))

        max_w = doc.width
        # keep image height under control so title + metadata + stats fit
        max_h = doc.height * 0.60

        for i, pb in enumerate(plot_blocks):
            # each plot starts on its own page (except the first, which shares with the "Plots" title)
            if i > 0:
                story.append(PageBreak())

            title = pb.get("title", "Plot")
            test_type_name = pb.get("test_type_name", "")
            data_paths = pb.get("data_paths", [])
            note = pb.get("note")
            fig = pb.get("fig")

            story.append(Paragraph(f"{escape(str(title))}", styles["Heading2"]))
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"Test Type: {escape(str(test_type_name))}", styles["Normal"]))
            story.append(Paragraph(f"Paths: {escape(str(data_paths))}", styles["Normal"]))
            if note:
                story.append(Paragraph(escape(str(note)), styles["Normal"]))
            story.append(Spacer(1, 8))

            # --------------------------------------------
            # Render: either embedded image OR Plotly figure
            # --------------------------------------------
            img_bytes = pb.get("image_bytes")
            img_name = pb.get("image_name")
            img_mime = pb.get("image_mime")

            if img_bytes:
                try:
                    # If it's a PDF attachment, rasterize first page -> PNG
                    is_pdf = (str(img_mime or "").lower() == "application/pdf") or \
                             (str(img_name or "").lower().endswith(".pdf"))

                    render_bytes = img_bytes
                    render_name = img_name

                    if is_pdf:
                        render_bytes = _pdf_bytes_to_png_bytes(img_bytes, page=0, dpi=200)
                        render_name = f"{img_name or 'attachment'}.page0.png"

                    img = _bytes_to_rl_image(render_bytes)

                    iw, ih = img.imageWidth, img.imageHeight
                    if iw > 0 and ih > 0:
                        scale_w = float(max_w) / float(iw)
                        scale_h = float(max_h) / float(ih)
                        scale = min(scale_w, scale_h, 1.0)
                        img.drawWidth = iw * scale
                        img.drawHeight = ih * scale

                    # Optional: print the filename above the image
                    if render_name:
                        story.append(Paragraph(f"Image file: {escape(str(render_name))}", styles["Normal"]))
                        story.append(Spacer(1, 6))

                    story.append(img)
                    story.append(Spacer(1, 8))

                except Exception as e:
                    story.append(
                        Paragraph(
                            f"⚠ Image/PDF render failed ({escape(str(img_name or ''))}): {escape(str(e))}",
                            styles["Normal"]
                        )
                    )

            elif fig is not None:
                try:
                    png = _fig_to_png_bytes(fig)
                    img_stream = io.BytesIO(png)
                    img = RLImage(img_stream)

                    iw, ih = img.imageWidth, img.imageHeight
                    if iw > 0 and ih > 0:
                        scale_w = float(max_w) / float(iw)
                        scale_h = float(max_h) / float(ih)
                        scale = min(scale_w, scale_h, 1.0)
                        img.drawWidth = iw * scale
                        img.drawHeight = ih * scale

                    story.append(img)
                    story.append(Spacer(1, 8))

                    stats = pb.get("stats") or {}
                    lines = stats.get("text_lines") or []
                    if lines:
                        story.append(Paragraph("<b>Stats</b>", styles["Normal"]))
                        for ln in lines:
                            story.append(Paragraph(f"• {escape(str(ln))}", styles["Normal"]))

                except Exception as e:
                    story.append(Paragraph(f"⚠ Plot render failed: {escape(str(e))}", styles["Normal"]))

            else:
                story.append(Paragraph("⚠ No figure/image available for this plot.", styles["Normal"]))

    # ----------------------------
    # SUB-COMPONENTS (new page)
    # ----------------------------
    story.append(PageBreak())
    story.append(Paragraph("Sub-components", styles["Heading1"]))
    story.append(Spacer(1, 8))

    subtree_lines = subtree_lines or []
    if subtree_lines:
        mono = styles["Code"] if "Code" in styles else styles["Normal"]
        story.append(Preformatted("\n".join(subtree_lines[:2000]), mono))
    else:
        story.append(Paragraph("—", styles["Normal"]))

    doc.build(story)

# ----------------------------
# Generate Sub-tree lines:
# ----------------------------
def _subtree_to_lines(rows):
    """
    ASCII-safe tree lines for ReportLab default fonts.
    Includes Certified/Uploaded as Y/N.

    Tweaks:
      - reduced indentation step so deep trees fit better on the page
    """
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    if not rows:
        return []

    by_key = {}
    children = {}
    root_key = None

    for r in rows:
        sk = r.get("self_key")
        pk = r.get("parent_key")
        if sk:
            by_key[sk] = r
            children.setdefault(pk, []).append(sk)
        if pk is None:
            root_key = sk

    def _sort_key(sk):
        rr = by_key.get(sk, {})
        return (rr.get("pid") or "", rr.get("type_name") or "", rr.get("position_name") or "")

    for pk in list(children.keys()):
        children[pk] = sorted(children[pk], key=_sort_key)

    def _short(s, n=30):
        s = (s or "").strip()
        return (s[: n - 3] + "...") if len(s) > n else s

    def _yn(mark):
        return "Y" if str(mark).strip() == "✅" else "N"

    def _line(rr):
        pid = (rr.get("pid") or "").strip()
        t   = _short(rr.get("type_name"), 28)
        pos = _short(rr.get("position_name"), 28)
        cert = _yn(rr.get("certified"))
        upl  = _yn(rr.get("uploaded"))
        status = _short(str(rr.get("status") or "").strip() or "Unknown", 24)
        flags = f"S:{status}  C:{cert} U:{upl}"
        mid = "  ".join([flags, t, pos]).strip()
        return f"{pid}  {mid}".strip()

    out = []

    def walk(sk, prefix="", is_last=True):
        rr = by_key.get(sk, {})
        if prefix == "":
            out.append(_line(rr))
        else:
            out.append(prefix + "+- " + _line(rr))

        kids = children.get(sk, [])
        if not kids:
            return

        # reduced indentation step (2 chars instead of 3)
        new_prefix = prefix + ("  " if is_last else "| ")

        for i, ck in enumerate(kids):
            walk(ck, new_prefix, i == len(kids) - 1)

    if root_key:
        walk(root_key, "", True)
    else:
        for r in rows:
            out.append(_line(r))

    return out
    
# ----------------------------
# Upload a PDF to the HWDB
# ----------------------------
def upload_pdf_to_hwdb(*, pid: str, typeid: str, pdf_path: Path, selected_pids: list[str] | None) -> dict:
    """
    If multiple PIDs are selected: upload to Component Type images (post_component_type_image).
    Else: upload to the selected PID images (post_hwitem_image).
    """
    if not pdf_path.exists():
        raise FileNotFoundError(str(pdf_path))

    merged = _selected_pids_union(pid, selected_pids)
    multi = len(merged) > 1

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    if multi:
        data = {
            "comments": f"Executive Summary PDF uploaded by HWDB Dashboard ({ts}) — MULTI-PID selection"
        }
        resp = post_component_type_image(typeid, data, filename=str(pdf_path))
        return resp

    data = {
        "comments": f"Executive Summary PDF uploaded by HWDB Dashboard ({ts})"
    }
    resp = post_hwitem_image(pid, data=data, filename=str(pdf_path))
    return resp

# ----------------------------
# Also to show Stats on screen
# ----------------------------
def _stats_block(stats: dict):
    lines = (stats or {}).get("text_lines") or []
    if not lines:
        return html.Div("Stats: —", style={"color":"#777", "marginTop":"6px"})
    return html.Div(
        [
            html.Div("Stats", style={"fontWeight":"bold", "marginTop":"6px"}),
            html.Ul([html.Li(ln) for ln in lines], style={"marginTop":"4px", "marginBottom":"0px"})
        ],
        style={
            "fontSize":"14px",
            "color":"#444",
            "backgroundColor":"#F6F8FB",
            "border":"1px solid #E0E6EF",
            "borderRadius":"10px",
            "padding":"8px 10px",
            "marginTop":"8px",
        }
    )

# ----------------------------
# Create the Reference section
# ----------------------------
def build_reference_urls_section(cfg: dict):
    """
    Renders the clickable Reference URLs section based on cfg["references"].

    format: "references": [{"url": "...", "comments": "..."}, ...]
    """
    refs = cfg.get("references", None)

    items = []

    if isinstance(refs, list):
        for r in refs:
            if not isinstance(r, dict):
                continue
            url = (r.get("url") or "").strip()
            comments = (r.get("comments") or "").strip()

            if not url:
                continue

            refs_list = [r for r in refs if isinstance(r, dict) and (r.get("url") or "").strip()]

            items = []
            for i, r in enumerate(refs_list):
                url = (r.get("url") or "").strip()
                comments = (r.get("comments") or "").strip()

                bg = "#FFFFFF" if i % 2 == 0 else "#F6F8FB"
                
                items.append(
                    html.Div(
                        [
                            html.A(url, href=url, target="_blank", rel="noopener noreferrer",
                                       style={"fontSize":"18px", "fontWeight":"600"}),
                            html.Div(comments, style={"color":"#555", "marginTop":"4px"}) if comments else None,
                        ],
                        style={
                            "backgroundColor": bg,
                            "border": "1px solid #DCE6F5",
                            "borderRadius": "10px",
                            "padding": "10px 12px",
                            "marginBottom": "10px",
                        }
                            #html.Div(comments, style={"color":"#555", "marginTop":"2px"}) if comments else None,
                            ## divider (not after last)
                            #html.Hr(style={"opacity": 0.25, "marginTop": "10px", "marginBottom": "10px"})
                            #if i < len(refs_list) - 1 else None,
                        #]
                    )
                )

    if not items:
        items = [html.Div("—", style={"color":"#777"})]

    return html.Div(
        [
            html.Div("Reference URLs", style={"fontWeight":"800", "fontSize":"22px"}),
            html.Div(items, style={"marginTop":"8px"}),
        ],
        style={
            "backgroundColor":"#EEF5FF",
            "border":"2px solid #4A90E2",
            "borderRadius":"12px",
            "padding":"12px 14px",
            "marginTop":"6px",
        }
    )


# ----------------------------
# TypeID helpers + PID list cache (for sum plots)
# ----------------------------

def _pid_type_prefix(pid: str) -> str:
    """
    Rule: type id is the first chunk before '-'
    (or "first 12 digits" if that's exactly what PIDs do).
    """
    pid = (pid or "").strip()
    return pid.split("-", 1)[0] if "-" in pid else pid


def _get_pids_for_typeid(cache_key: str | None, typeid: str) -> list[str]:
    typeid = (typeid or "").strip()
    if not typeid:
        return []

    bucket = _execsum_cache.get(cache_key) if cache_key else None
    plc = bucket.setdefault("pidlist_cache", {}) if isinstance(bucket, dict) else None

    # Only return cached value if it’s a *non-empty* list
    if plc is not None and typeid in plc:
        cached = plc.get(typeid)
        if isinstance(cached, list) and len(cached) > 0:
            return list(cached)

    # Otherwise refetch from HWDB (and overwrite cache)
    try:
        resp = get_hwitems(typeid, size=99999)
        items = resp.get("data", []) or []
        pids = []
        for it in items:
            pid = _safe(it.get("part_id") or it.get("pid") or "")
            if pid:
                pids.append(pid)

        # sort largest first
        def _pid_key(pid: str):
            if "-" in pid:
                a, b = pid.split("-", 1)
                try:
                    return (a, int(b))
                except Exception:
                    return (a, b)
            return (pid, 0)
        pids.sort(key=_pid_key, reverse=True)

        if plc is not None:
            plc[typeid] = pids
        return pids

    except Exception as e:
        logger.error(f"[ExecSum] _get_pids_for_typeid failed typeid={typeid}: {e}")
        if plc is not None:
            plc[typeid] = []   # ok to cache empty, because we refetch next time anyway
        return []


# ----------------------------
# Test cache getters + prefetch
# ----------------------------

def _get_test_cached(cache_key: str | None, pid: str, test_type: str):
    """
    Returns cached test_data dict or fetches via get_hwitem_test.
    Works even if pid is not in the synced PID table.
    """
    if not cache_key or cache_key not in _execsum_cache:
        return None

    tc = _execsum_cache[cache_key].setdefault("tests_cache", {})
    key = (pid, test_type)
    if key in tc:
        return tc[key]

    td = fetch_test_blob(pid, test_type)
    tc[key] = td
    return td


def _prefetch_tests(cache_key: str | None, pids: list[str], test_type: str):
    """
    Fetch many tests concurrently into tests_cache for speed.
    """
    if not cache_key or cache_key not in _execsum_cache:
        return

    tc = _execsum_cache[cache_key].setdefault("tests_cache", {})
    executor = ra_util._executor

    futs = {}
    for pid in (pids or []):
        k = (pid, test_type)
        if k in tc:
            continue
        futs[k] = executor.submit(fetch_test_blob, pid, test_type)

    for k, fut in futs.items():
        try:
            tc[k] = fut.result()
        except Exception:
            tc[k] = None

# MIME
def _guess_mime_from_name(name: str) -> str:
    n = (name or "").lower()
    if n.endswith(".png"):
        return "image/png"
    if n.endswith(".jpg") or n.endswith(".jpeg"):
        return "image/jpeg"
    if n.endswith(".gif"):
        return "image/gif"
    if n.endswith(".webp"):
        return "image/webp"
    if n.endswith(".pdf"):
        return "application/pdf"
    return "application/octet-stream"

# Let's scan common key first and then does a search recursively
def _find_image_id_in_test_record(test_rec: dict, image_name: str) -> str | None:
    """
    Returns image_id for the image_name within ONE test record dict.
    Tries common list fields, then a recursive fallback.
    """
    want = (image_name or "").strip()
    if not want or not isinstance(test_rec, dict):
        return None

    # common fields where image entries live
    candidates = []
    for k in ("images", "test_images", "image_list", "images_list", "attachments"):
        v = test_rec.get(k)
        if isinstance(v, list):
            candidates.extend(v)

    def check_list(lst):
        for it in lst:
            if not isinstance(it, dict):
                continue
            nm = (it.get("image_name") or it.get("name") or it.get("filename") or "").strip()
            if nm == want:
                iid = it.get("image_id") or it.get("id")
                if iid:
                    return str(iid)
        return None

    iid = check_list(candidates)
    if iid:
        return iid

    # recursive fallback: find dicts that look like {"image_name":..., "image_id":...}
    def walk(obj):
        if isinstance(obj, dict):
            nm = (obj.get("image_name") or "").strip()
            if nm == want and (obj.get("image_id") or obj.get("id")):
                return str(obj.get("image_id") or obj.get("id"))
            for vv in obj.values():
                out = walk(vv)
                if out:
                    return out
        elif isinstance(obj, list):
            for vv in obj:
                out = walk(vv)
                if out:
                    return out
        return None

    return walk(test_rec)

# Fetch the correct test record by "history_order"
def _get_test_record_by_history_order(pid: str, test_type_name: str, history_order: int) -> tuple[dict | None, str | None]:
    """
    Returns (test_record_dict, error_msg).
    history_order=0 means latest.
    """
    pid = (pid or "").strip()
    tt = (test_type_name or "").strip()
    try:
        h = int(history_order)
    except Exception:
        h = 0
    if h < 0:
        h = 0

    try:
        # Prefer wrapper list (history)
        resp = get_hwitem_test(pid, tt, history=True)
    except TypeError:
        # If get_hwitem_test signature doesn't accept history=True,
        # try the default and hope it returns list anyway
        resp = get_hwitem_test(pid, tt)

    # If wrapper {"data":[...]}:
    if isinstance(resp, dict) and isinstance(resp.get("data"), list):
        data = resp.get("data") or []
        if not data:
            return (None, f"No test history found for {pid} / {tt}.")
        if h >= len(data):
            return (None, f"history_order={h} out of range (N={len(data)}).")
        rec = data[h]
        return (rec if isinstance(rec, dict) else None, None)

    # If direct dict:
    if isinstance(resp, dict):
        if h == 0:
            return (resp, None)
        return (None, "history_order>0 requested but API returned only a single record (no history list).")

    return (None, "Unexpected HWDB response shape when fetching test record.")

# Download bytes (cached)
def _get_test_attached_image_bytes(
    *,
    cache_key: str | None,
    pid: str,
    test_type_name: str,
    image_name: str,
    history_order: int = 0,
) -> tuple[bytes | None, str, str | None]:
    """
    Returns (bytes_or_None, mime_type, error_msg_or_None)
    Uses server-side cache to avoid repeated downloads (and avoid flashing).
    """
    pid = (pid or "").strip()
    tt = (test_type_name or "").strip()
    img_name = (image_name or "").strip()
    ho = int(history_order or 0)

    if not pid or not tt or not img_name:
        return (None, "application/octet-stream", "Missing pid/test_type_name/image_name.")

    # cache
    ck = (pid, tt, ho, img_name)
    bucket = _execsum_cache.get(cache_key) if cache_key else None
    icache = bucket.setdefault("images_cache", {}) if isinstance(bucket, dict) else None

    if icache is not None and ck in icache:
        cached = icache.get(ck) or {}
        return (cached.get("bytes"), cached.get("mime") or _guess_mime_from_name(img_name), cached.get("error"))

    # get test record at history_order
    rec, err = _get_test_record_by_history_order(pid, tt, ho)
    if err or not rec:
        if icache is not None:
            icache[ck] = {"bytes": None, "mime": _guess_mime_from_name(img_name), "error": err or "No record."}
        return (None, _guess_mime_from_name(img_name), err or "No record.")

    # find image_id
    image_id = _find_image_id_in_test_record(rec, img_name)
    if not image_id:
        msg = f"Could not find image_name='{img_name}' in test record (pid={pid}, test={tt}, history_order={ho})."
        if icache is not None:
            icache[ck] = {"bytes": None, "mime": _guess_mime_from_name(img_name), "error": msg}
        return (None, _guess_mime_from_name(img_name), msg)

    # download to temp file, then read bytes
    try:
        import tempfile
        from pathlib import Path

        suffix = "." + img_name.split(".")[-1] if "." in img_name else ""
        tmp = Path(tempfile.mkstemp(suffix=suffix)[1])
        try:
            get_image(image_id, write_to_file=str(tmp))
            b = tmp.read_bytes()
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

        mime = _guess_mime_from_name(img_name)
        if icache is not None:
            icache[ck] = {"bytes": b, "mime": mime, "error": None, "image_id": str(image_id)}
        return (b, mime, None)

    except Exception as e:
        msg = f"Failed to download image (image_id={image_id}): {e}"
        if icache is not None:
            icache[ck] = {"bytes": None, "mime": _guess_mime_from_name(img_name), "error": msg, "image_id": str(image_id)}
        return (None, _guess_mime_from_name(img_name), msg)

# Plot div builder for images
def build_image_plot_div(
    *,
    title: str,
    test_type_name: str,
    pid: str,
    cache_key: str | None,
    image_name: str,
    history_order: int,
):
    b, mime, err = _get_test_attached_image_bytes(
        cache_key=cache_key,
        pid=pid,
        test_type_name=test_type_name,
        image_name=image_name,
        history_order=history_order,
    )

    header = html.H5(f"{title}  —  {test_type_name}", style={"marginBottom": "6px"})

    if err or not b:
        return [
            html.Div(
                [
                    header,
                    html.Div(f"⚠ {err or 'No image bytes returned.'}", style={"color": "#a66"}),
                ],
                style={"marginBottom": "16px"},
            )
        ]

    b64 = base64.b64encode(b).decode("ascii")
    src = f"data:{mime};base64,{b64}"

    # For PDFs, show an embedded viewer instead of <img>
    if mime == "application/pdf" or (image_name or "").lower().endswith(".pdf"):
        return [
            html.Div(
                [
                    header,
                    html.Div(
                        f"PDF: {image_name} (history_order={history_order})",
                        style={"color": "#666", "fontSize": "13px", "marginBottom": "6px"},
                    ),
                    html.Iframe(
                        src=src,
                        style={
                            "width": "100%",
                            "height": "800px",
                            "borderRadius": "10px",
                            "border": "1px solid #E0E6EF",
                        },
                    ),
                ],
                style={"marginBottom": "16px"},
            )
        ]

    
    return [
        html.Div(
            [
                header,
                html.Div(
                    f"Image: {image_name} (history_order={history_order})",
                    style={"color": "#666", "fontSize": "13px", "marginBottom": "6px"},
                ),
                html.Img(
                    src=src,
                    style={
                        "maxWidth": "100%",
                        "height": "auto",
                        "borderRadius": "10px",
                        "border": "1px solid #E0E6EF",
                    },
                ),
            ],
            style={"marginBottom": "16px"},
        )
    ]
            
# ----------------------------
# Collect 1D series (uses _get_test_cached)
# ----------------------------

def _collect_1d_series_from_selected(cache_key, pids_to_plot, test_type_name, path0):
    rows = []

    for pid in (pids_to_plot or []):
        tb = _get_test_cached(cache_key, pid, test_type_name) if cache_key else fetch_test_blob(pid, test_type_name)
        if not tb:
            continue

        v = _get_by_path(tb, path0)
        if isinstance(v, list):
            for item in v:
                rows.append({"pid": pid, "value": item})
        else:
            rows.append({"pid": pid, "value": v})

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["pid", "value"])

    if df["value"].map(type).nunique() > 1:
        df["value"] = df["value"].astype(str)

    return df


# ----------------------------
# Build one plot block (hist or scatter) for an arbitrary pid population
# ----------------------------

def build_plot_divs(
    *,
    title: str,
    test_type_name: str,
    paths: list[str],
    bins: int,
    pids_for_plot: list[str],
    cache_key: str | None,
    label: str,   # e.g. "single PID Z...-00332" or "sum over TypeID Z001... (N=123)"
):
    """
    Returns a list[html.Div] (usually 1 div) for this plot population.
    """

    # Prefetch to speed up (optional but nice)
    if cache_key:
        _prefetch_tests(cache_key, pids_for_plot, test_type_name)

    # ----- Histogram / categorical -----
    if len(paths) == 1:
        df1 = _collect_1d_series_from_selected(cache_key, pids_for_plot, test_type_name, paths[0])

        if df1.empty or "value" not in df1.columns:
            return [
                html.Div(
                    [
                        html.H5(f"{title} — {label}", style={"marginBottom": "6px"}),
                        html.Div(
                            f"⚠ No data found for '{test_type_name}' across {len(pids_for_plot)} PID(s).",
                            style={"color": "#a66"},
                        ),
                        _stats_block({"text_lines": ["No data."]}),
                    ],
                    style={"marginBottom": "16px"},
                )
            ]

        num = pd.to_numeric(df1["value"], errors="coerce")
        numeric_ratio = num.notna().sum() / max(len(df1), 1)

        if numeric_ratio > 0.8:
            df1["value_num"] = num
            fig = px.histogram(df1, x="value_num", nbins=bins or 40)
            fig.update_layout(title=f"{title} — {label}", height=320)
            stats = stats_hist(df1["value_num"].dropna().tolist())
        else:
            df1["value_cat"] = df1["value"].map(lambda x: "True" if x is True else ("False" if x is False else str(x)))
            fig = px.histogram(df1, x="value_cat")
            fig.update_layout(title=f"{title} — {label}", height=320)
            vc = df1["value_cat"].value_counts(dropna=True)
            stats = {"text_lines": [f"N = {len(df1)}", f"unique = {vc.size}"] + [f"{k}: {v}" for k, v in vc.head(5).items()]}
            fig.update_xaxes(tickangle=-25)

        return [
            html.Div(
                [
                    html.H5(f"{title}  —  {test_type_name}", style={"marginBottom": "6px"}),
                    dcc.Graph(figure=fig, config={"displayModeBar": True}),
                    _stats_block(stats),
                ],
                style={"marginBottom": "16px"},
            )
        ]

    # ----- Scatter -----
    if len(paths) == 2:
        X_all, Y_all = [], []

        for each_pid in (pids_for_plot or []):
            tb = _get_test_cached(cache_key, each_pid, test_type_name) if cache_key else fetch_test_blob(each_pid, test_type_name)
            if not tb:
                continue

            x = _get_by_path(tb, paths[0])
            y = _get_by_path(tb, paths[1])

            X = _flatten_numeric(x)
            Y = _flatten_numeric(y)
            n = min(len(X), len(Y))
            if n > 0:
                X_all += X[:n]
                Y_all += Y[:n]

        if not X_all or not Y_all:
            return [
                html.Div(
                    [
                        html.H5(f"{title} — {label}", style={"marginBottom": "6px"}),
                        html.Div(
                            f"⚠ No numeric (x,y) data found for '{test_type_name}' across {len(pids_for_plot)} PID(s).",
                            style={"color": "#a66"},
                        ),
                        _stats_block({"text_lines": ["No data."]}),
                    ],
                    style={"marginBottom": "16px"},
                )
            ]

        fig = make_scatter(X_all, Y_all, title=f"{title} — {label}")
        stats = stats_scatter(X_all, Y_all)

        return [
            html.Div(
                [
                    html.H5(f"{title}  —  {test_type_name}", style={"marginBottom": "6px"}),
                    dcc.Graph(figure=fig, config={"displayModeBar": True}),
                    _stats_block(stats),
                ],
                style={"marginBottom": "16px"},
            )
        ]

    # ----- invalid config -----
    return [
        html.Div(
            [
                html.H5(title, style={"marginBottom": "6px"}),
                html.Div("⚠ data_paths must have length 1 (hist/categorical) or 2 (scatter).", style={"color": "#a66"}),
                _stats_block({"text_lines": ["Invalid data_paths length."]}),
            ],
            style={"marginBottom": "16px"},
        )
    ]

# ----------------------------
# To select a range of PIDs
# ----------------------------
def _item_number_from_pid(pid: str) -> int | None:
    """
    Extract the 'item number' (last 5 digits) from a PID like:
      Z00100300001-07039  -> 7039
    Returns int or None if parsing fails.
    """
    pid = (pid or "").strip()
    if not pid:
        return None
    if "-" not in pid:
        return None
    suffix = pid.split("-", 1)[1].strip()          # "07039"
    suffix5 = suffix[-5:] if len(suffix) >= 5 else suffix
    # allow users to type "7039" too
    suffix5 = re.sub(r"\D", "", suffix5)
    if not suffix5:
        return None
    try:
        return int(suffix5)
    except Exception:
        return None


def _parse_item_input(s: str | None) -> int | None:
    """
    Accepts "07039", "7039", " 07039 ", etc.
    Returns int or None.
    """
    if s is None:
        return None
    t = re.sub(r"\D", "", str(s).strip())
    if not t:
        return None
    try:
        return int(t)
    except Exception:
        return None


def _pids_in_item_range(table_data: list[dict], start_num: int, end_num: int) -> list[str]:
    """
    Returns PIDs whose item-number is within [start_num, end_num] inclusive.
    Uses the FULL table_data.
    """
    lo = min(start_num, end_num)
    hi = max(start_num, end_num)

    out = []
    for r in (table_data or []):
        if not isinstance(r, dict):
            continue
        pid = str(r.get("pid") or "").strip()
        n = _item_number_from_pid(pid)
        if n is None:
            continue
        if lo <= n <= hi:
            out.append(pid)
    return out

# ----------------------------
# For the case of selecting multiple PIDs
# ----------------------------
def _pid_item_suffix5(pid: str) -> str:
    """
    Returns last 5 digits (string) of PID item number, preserving leading zeros.
     e.g.,  Z00100300001-07039 -> "07039"
    """
    pid = (pid or "").strip()
    if "-" not in pid:
        return ""
    suf = pid.split("-", 1)[1].strip()
    # keep only digits, preserve last 5
    suf = re.sub(r"\D", "", suf)
    if not suf:
        return ""
    return suf[-5:].zfill(5)

def _compress_item_suffixes_to_ranges(items5: list[str]) -> str:
    """
    items5: list of "07039" strings
    Returns: "07001-07100, 07105, 07200-07210" etc.
    """
    nums = []
    for s in (items5 or []):
        t = re.sub(r"\D", "", str(s))
        if not t:
            continue
        try:
            nums.append(int(t))
        except Exception:
            pass

    if not nums:
        return "—"

    nums = sorted(set(nums))
    ranges = []
    start = prev = nums[0]

    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        # close range
        if start == prev:
            ranges.append(f"{start:05d}")
        else:
            ranges.append(f"{start:05d}-{prev:05d}")
        start = prev = n

    # final close
    if start == prev:
        ranges.append(f"{start:05d}")
    else:
        ranges.append(f"{start:05d}-{prev:05d}")

    return ", ".join(ranges)

def _selected_pids_union(root_pid: str, selected_pids: list[str] | None) -> list[str]:
    """
    Returns unique list preserving order:
      [root_pid] + selected_pids (minus duplicates)
    """
    root_pid = (root_pid or "").strip()
    raw = []
    if root_pid:
        raw.append(root_pid)
    for p in (selected_pids or []):
        pp = str(p or "").strip()
        if pp:
            raw.append(pp)

    out = []
    seen = set()
    for p in raw:
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out

def _build_selected_pid_summary(root_pid: str, selected_pids: list[str] | None, typeid: str | None) -> tuple[bool, str, str]:
    """
    Returns:
      (has_multiple, subtitle_text, items_line_text)

    subtitle_text:
      - single: ""
      - multi:  "<TypeID>-<minItem>-<maxItem>"  (e.g. "Z00100300023-07001-07100")
    """
    merged = _selected_pids_union(root_pid, selected_pids)
    has_multiple = len(merged) > 1

    # Item-number list line (compressed ranges)
    items5 = [_pid_item_suffix5(p) for p in merged if _pid_item_suffix5(p)]
    items_line = _compress_item_suffixes_to_ranges(items5) if items5 else "—"

    # Subtitle for the title (NO "and other PIDs")
    subtitle = ""
    if has_multiple:
        t = (typeid or "").strip()
        lo5, hi5 = _minmax_item_range_from_pids(merged)
        if t and lo5 and hi5:
            subtitle = f"{t}-{lo5}-{hi5}"
        elif t:
            subtitle = f"{t}-MULTI"
        else:
            subtitle = "MULTI"

    return has_multiple, subtitle, items_line

def _resolve_pid_from_sub_part_id(sub_rows: list[dict], *, layer: int, pos_name: str) -> str | None:
    """
    layer:
      0 => root row (len(path)-1 == 0)
      1 => first child
      2 => grandchild
      ...
    pos_name compares to row["position_name"] (exact string match after strip).
    Returns first match PID, or None if not found.
    """
    try:
        layer = int(layer)
    except Exception:
        return None

    want_pos = (pos_name or "").strip()
    if want_pos == "":
        return None

    matches = []
    for r in (sub_rows or []):
        if not isinstance(r, dict):
            continue
        p = r.get("path")
        if not isinstance(p, list) or not p:
            continue
        d = len(p) - 1  # root is 0
        if d != layer:
            continue
        rp = (r.get("position_name") or "").strip()
        if rp == want_pos:
            pid = str(r.get("pid") or "").strip()
            if pid:
                matches.append(pid)

    if not matches:
        return None

    # stable pick (lowest PID string) if multiple
    matches = sorted(set(matches))
    return matches[0]

def _dash_request_host() -> str:
    """
    Best effort: returns the hostname the *client browser* is using to access Dash.
    Example: '192.168.1.23' or 'localhost' or '127.0.0.1'
    """
    try:
        host = (flask_request.host or "").strip()   # may include :port
        if not host:
            return ""
        return host.split(":", 1)[0].strip()
    except Exception:
        return ""

def _dash_request_scheme() -> str:
    """
    Best effort: returns 'https' or 'http' for the current client request.
    """
    try:
        s = (flask_request.scheme or "").strip().lower()
        return s if s in ("http", "https") else "https"
    except Exception:
        return "https"

def _is_lan_mode_request() -> bool:
    """
    Heuristic LAN-mode detector:
      - If the client is accessing Dash via https, assume LAN mode.
    This matches the design: LAN mode uses app.run(..., ssl_context=...).
    """
    return (_dash_request_scheme() == "https")

# ============================================================
# Callbacks
# ============================================================
def register_executive_summary_callbacks(app):

    # ----------------------------
    # Populate Type Name from the store
    # ----------------------------
    @app.callback(
        Output("execsum-type-name-display", "children"),
        Input("execsum-type-name", "data"),
    )
    def show_type_name(type_name):
        t = (type_name or "").strip()
        return t if t else ""

    # ----------------------------
    # Prefill eachsignature input
    # ----------------------------
    @app.callback(
        Output({"type":"execsum-signee-input","name":ALL}, "value"),
        Input("execsum-es-existing", "data"),
        State({"type":"execsum-signee-input","name":ALL}, "id"),
        prevent_initial_call=False,
    )
    def prefill_signature_inputs(es_existing, input_ids):
        m = _es_map_by_name(es_existing or [])
        values = []
        for iid in (input_ids or []):
            nm = (iid or {}).get("name")
            ent = m.get(nm) or {}
            values.append(ent.get("signature", ""))  # show existing signature, else blank
        return values
    # ----------------------------
    # Make "already signed" fields look read-only!
    # ----------------------------
    @app.callback(
        Output({"type":"execsum-signee-input","name":ALL}, "disabled"),
        Input("execsum-es-status", "data"),
        State({"type":"execsum-signee-input","name":ALL}, "id"),
    )
    def disable_signed_inputs(status, input_ids):
        per = (status or {}).get("per") or {}
        disabled = []
        for iid in (input_ids or []):
            nm = (iid or {}).get("name")
            info = per.get(nm) or {}
            disabled.append(bool(info.get("already")))  # disable if already signed
        return disabled


    # ----------------------------
    # clicking RESET creates a “SIG job” that posts ES: []
    # ----------------------------
    @app.callback(
        Output("execsum-sig-job", "data", allow_duplicate=True),
        Output("execsum-sig-interval", "disabled", allow_duplicate=True),
        Output("execsum-sig-busy", "data", allow_duplicate=True),
        #Input("execsum-reset-es", "n_clicks"),
        Input("execsum-reset-confirm-yes", "n_clicks"), # start by clicking the Modal
        State("execsum-selected-pid", "data"),
        prevent_initial_call=True,
    )
    def start_reset_es_job(n_clicks, pid):
        if not n_clicks:
            raise PreventUpdate
        if not pid:
            raise PreventUpdate

        pid_ = str(pid).strip()
        if not pid_:
            raise PreventUpdate

        job_id = f"SIG-RESET-{int(time.time()*1000)}"
        _execsum_sig_jobs[job_id] = {"done": False, "error": None, "new_es": None, "msg": None, "new_table": None}

        def _worker():
            try:
                # Overwrite ES with empty list
                #post_es_test(pid_, [], comments="ES RESET requested (cleared signatures)")
                es_list, todos_payload = fetch_latest_es_and_todos(pid_)
                post_es_test(pid_, [], comments="ES RESET requested (cleared signatures)", todos_payload=todos_payload)

                _execsum_sig_jobs[job_id]["new_es"] = []
                _execsum_sig_jobs[job_id]["msg"] = "RESET done: cleared ES signatures (ES: [])."
                _execsum_sig_jobs[job_id]["done"] = True
            except Exception as e:
                _execsum_sig_jobs[job_id]["error"] = str(e)
                _execsum_sig_jobs[job_id]["done"] = True

        threading.Thread(target=_worker, daemon=True).start()

        # Use busy to “grey out” signee buttons while reset runs
        return job_id, False, {"name": "__RESET__"}

    
    # ----------------------------
    # Populate the sub-component table once an original PID is selected
    # ----------------------------
    @app.callback(
        Output("execsum-subcomp-wrapper", "style"),
        Output("execsum-subcomp-status", "children"),
        Output("execsum-subcomp-job", "data"),
        Output("execsum-subcomp-interval", "disabled"),
        Output("execsum-subcomp-grid", "rowData"),
        Input("execsum-selected-pid", "data"),
        State("execsum-cache-key", "data"),
        prevent_initial_call=True,
    )
    def start_subcomp_job(selected_pid, cache_key):
        if not selected_pid:
            return {"display":"none"}, "", None, True, []

        pid = str(selected_pid).strip()
        job_id = f"SUBCOMP-{int(time.time()*1000)}"
        _execsum_subcomp_jobs[job_id] = {"done": False, "error": None, "rowData": None}

        def _worker():
            try:
                rows = _build_subcomponent_rows_recursive(pid, cache_key=cache_key) or []
                rows = _add_group_levels(rows, max_levels=12)

                def _strip_suffix(s):
                    if s is None:
                        return None
                    return str(s).split("__", 1)[0]
            
                for r in rows:
                    if not isinstance(r, dict):
                        continue
                    for i in range(12):
                        li = r.get(f"level{i}")
                        r[f"g{i}"] = _strip_suffix(li) if li else None

                    # depth
                    d = -1
                    for i in range(12):
                        if r.get(f"g{i}") is not None:
                            d = i
                    r["depth"] = d

                cleaned = []
                seen_ids = set()
                for r in rows:
                    if not isinstance(r, dict):
                        continue
                    rid = r.get("id")
                    p = r.get("path")
                    if not isinstance(rid, str) or not rid.strip():
                        continue
                    if not isinstance(p, list) or not p:
                        continue
                    if rid in seen_ids:
                        continue
                    seen_ids.add(rid)
                    r["is_leaf_for_group"] = True
                    cleaned.append(r)

                _execsum_subcomp_jobs[job_id]["rowData"] = cleaned
                _execsum_subcomp_jobs[job_id]["done"] = True
            except Exception as e:
                _execsum_subcomp_jobs[job_id]["error"] = str(e)
                _execsum_subcomp_jobs[job_id]["done"] = True

        threading.Thread(target=_worker, daemon=True).start()

        # show wrapper + message immediately; keep old rowData to avoid flicker
        return {"display":"block"}, "Preparing the list of sub-components…", job_id, False, no_update

    @app.callback(
        Output("execsum-subcomp-grid", "rowData", allow_duplicate=True),
        Output("execsum-subcomp-status", "children", allow_duplicate=True),
        Output("execsum-subcomp-job", "data", allow_duplicate=True),
        Output("execsum-subcomp-interval", "disabled", allow_duplicate=True),
        Input("execsum-subcomp-interval", "n_intervals"),
        State("execsum-subcomp-job", "data"),
        prevent_initial_call=True,
    )
    def poll_subcomp_job(_n, job_id):
        if not job_id or job_id not in _execsum_subcomp_jobs:
            raise PreventUpdate

        job = _execsum_subcomp_jobs[job_id]

        if job.get("error"):
            _execsum_subcomp_jobs.pop(job_id, None)
            return [], f"Error preparing sub-components: {job['error']}", None, True

        if not job.get("done"):
            raise PreventUpdate

        rowData = job.get("rowData") or []
        _execsum_subcomp_jobs.pop(job_id, None)
        return rowData, "", None, True

    # ----------------------------
    # Start PDF job (fast)
    # ----------------------------
    @app.callback(
        Output("execsum-details-wait-area", "style"),
        Output("execsum-details-wait-text", "children"),
        Output("execsum-details-wait-text", "style"),
        Output("execsum-details-section", "style"),
        Output("execsum-details-job", "data"),
        Output("execsum-details-interval", "disabled"),

        # Trigger on BOTH, but especially todos_state
        Input("execsum-selected-pid", "data"),
        Input("execsum-todos-state", "data"),

        State("execsum-details-section", "style"),   # to detect already-visible...
        
        State("execsum-cache-key", "data"),
        State("execsum-config-store", "data"),
        State("execsum-pid-table", "data"),
        State("execsum-whoami-name", "data"),
        State("execsum-signoff-datetime-store", "data"),
        State("execsum-plot-selected-pids", "data"),

        State("execsum-mode", "data"),
        State("execsum-has-config", "data"),
        
        prevent_initial_call=True,
    )
    def start_details_job(selected_pid, todos_state, details_style_now,
                      cache_key, cfg, table_data, whoami_name, signoff_dt, selected_pids, mode, has_config):

        if not selected_pid:
            return {"display": "none"}, "", {"display": "none"}, DETAILS_STYLE_HIDDEN, None, True


        mode = (mode or "detail").strip().lower()
        if (not has_config) or (not cfg):
            mode = "default"

        # In DETAIL mode we need todos_state ready; in DEFAULT mode we do not.
        if mode == "detail" and not isinstance(todos_state, dict):
            raise PreventUpdate


        trig = ctx.triggered_id

        # If the trigger is just "todos changed" and details are already visible, do nothing
        already_visible = isinstance(details_style_now, dict) and details_style_now.get("display") == "flex"
        if trig == "execsum-todos-state" and already_visible:
            raise PreventUpdate

        pid = str(selected_pid).strip()
        job_id = f"DETAILS-{int(time.time() * 1000)}"
        _execsum_details_jobs[job_id] = {"done": False, "error": None, "payload": None}

        wait_style = {"minHeight": "55vh", "display": "block", "pointerEvents": "none"}
        text_style = {"marginTop": "10px", "color": "#666", "display": "block", "pointerEvents": "none"}

        cache_key_ = cache_key
        cfg_ = cfg
        table_data_ = table_data
        whoami_name_ = whoami_name
        signoff_dt_ = signoff_dt
        selected_pids_ = selected_pids
        todos_state_ = todos_state

        def _worker():
            try:
                payload = _build_details_payload(
                    pid=pid,
                    cache_key=cache_key_,
                    cfg=cfg_,
                    table_data=table_data_,
                    whoami_name=whoami_name_,
                    signoff_dt=signoff_dt_,
                    selected_pids=selected_pids_,
                    todos_state=todos_state_,
                    mode=mode,
                    has_config=has_config,
                )
                _execsum_details_jobs[job_id]["payload"] = payload
                _execsum_details_jobs[job_id]["done"] = True
            except Exception as e:
                _execsum_details_jobs[job_id]["error"] = str(e)
                _execsum_details_jobs[job_id]["done"] = True

        threading.Thread(target=_worker, daemon=True).start()

        return wait_style, "Preparing the sign-off and plot section…", text_style, DETAILS_STYLE_HIDDEN, job_id, False
    
    @app.callback(
        Output("execsum-details-section", "style", allow_duplicate=True),
        Output("execsum-form-block", "children", allow_duplicate=True),
        Output("execsum-plots-container", "children", allow_duplicate=True),
        Output("execsum-details-wait-area", "style", allow_duplicate=True),
        Output("execsum-details-wait-text", "children", allow_duplicate=True),
        Output("execsum-details-wait-text", "style", allow_duplicate=True),
        Output("execsum-details-job", "data", allow_duplicate=True),
        Output("execsum-details-interval", "disabled", allow_duplicate=True),
        Input("execsum-details-interval", "n_intervals"),
        State("execsum-details-job", "data"),
        prevent_initial_call=True,
    )
    def poll_details_job(_n, job_id):
        if not job_id or job_id not in _execsum_details_jobs:
            raise PreventUpdate

        job = _execsum_details_jobs[job_id]

        # still running
        if not job.get("done"):
            raise PreventUpdate

        # done -> publish
        err = job.get("error")
        if err:
            _execsum_details_jobs.pop(job_id, None)
            wait_style = {"minHeight": "55vh", "display": "block", "pointerEvents": "none"}
            text_style = {"marginTop": "10px", "color": "#a66", "display": "block", "pointerEvents": "none"}
            return (
                DETAILS_STYLE_HIDDEN,
                [],
                [],
                wait_style,
                f"Error preparing details: {err}",
                text_style,
                None,
                True,
            )

        payload = job.get("payload")
        _execsum_details_jobs.pop(job_id, None)

        # payload format from _build_details_payload
        details_style, form_children, plot_children = payload

        return (
            details_style,
            form_children,
            plot_children,
            {"display": "none"},
            "",
            {"display": "none"},
            None,
            True,
        )

    @app.callback(
        Output("execsum-generate-upload", "disabled", allow_duplicate=True),
        Output("execsum-generate-upload", "style", allow_duplicate=True),
        Output("execsum-pdf-status", "children", allow_duplicate=True),
        Output("execsum-pdf-job", "data"),
        Output("execsum-pdf-interval", "disabled"),
        Input("execsum-generate-upload", "n_clicks"),
        State("execsum-selected-pid", "data"),
        State("execsum-cache-key", "data"),
        State("execsum-typeid", "value"),
        State("execsum-config-store", "data"),
        State("execsum-status-dropdown", "value"),     
        State("execsum-flag-certified", "value"),
        State("execsum-flag-uploaded", "value"),
        State("execsum-whoami-name", "data"),
        State("execsum-es-existing", "data"),
        State("execsum-plot-selected-pids", "data"),
        State("execsum-todos-state", "data"),
        State("execsum-mode", "data"),
        State("execsum-default-signinfo", "data"),
        prevent_initial_call=True,
    )
    def start_pdf_job(n_clicks, selected_pid, cache_key, typeid, cfg, status_id, certified_flag, uploaded_flag,
                          whoami_name, es_existing, selected_pids, todos_state, mode, default_signinfo):
        if not n_clicks:
            raise PreventUpdate
        if not selected_pid:
            return no_update, no_update, "No PID selected.", None, True

        attach_pid = str(selected_pid).strip()
        if not attach_pid:
            return no_update, no_update, "No PID selected.", None, True

        job_id = f"PDF-{int(time.time() * 1000)}"
        _execsum_pdf_jobs[job_id] = {"done": False, "error": None, "msg": None}

        # snapshot inputs
        cache_key_ = cache_key
        typeid_ = typeid
        cfg_ = cfg
        status_id_ = status_id
        certified_flag_ = bool(certified_flag)
        uploaded_flag_ = bool(uploaded_flag)
        whoami_name_ = whoami_name
        es_existing_ = es_existing
        selected_pids_ = selected_pids
        todos_state_ = todos_state
        mode_ = mode
        default_signinfo_ = default_signinfo

        def _worker():
            try:
                mode_ = (mode or "detail").strip().lower()

                if mode_ == "default":
                    msg = _do_generate_and_upload_pdf_default(
                        selected_pid=attach_pid,
                        cache_key=cache_key_,
                        typeid=typeid_,
                        selected_pids=selected_pids_,
                        signinfo=default_signinfo_,
                    )
                else:
                    sid = _status_id_from_anywhere(status_id=status_id_, pid=attach_pid, cache_key=cache_key_)
                    status_label = STATUS_LABEL_BY_ID.get(sid, "Unknown")
                    msg = _do_generate_and_upload_pdf(
                        selected_pid=attach_pid,
                        cache_key=cache_key_,
                        typeid=typeid_,
                        cfg=cfg_,
                        status_label=status_label,
                        certified_flag=certified_flag_,
                        uploaded_flag=uploaded_flag_,
                        whoami_name=whoami_name_,
                        es_existing=es_existing_,
                        selected_pids=selected_pids_,
                        todos_state=todos_state_,
                    )
                    
                _execsum_pdf_jobs[job_id]["msg"] = msg
                _execsum_pdf_jobs[job_id]["done"] = True
            except Exception as e:
                _execsum_pdf_jobs[job_id]["error"] = str(e)
                _execsum_pdf_jobs[job_id]["done"] = True

        threading.Thread(target=_worker, daemon=True).start()

        return True, PDF_BTN_DISABLED_STYLE, "Uploading the PDF to the HWDB…", job_id, False

    @app.callback(
        Output("execsum-generate-upload", "disabled", allow_duplicate=True),
        Output("execsum-generate-upload", "style", allow_duplicate=True),
        Output("execsum-pdf-status", "children", allow_duplicate=True),
        Output("execsum-pdf-job", "data", allow_duplicate=True),
        Output("execsum-pdf-interval", "disabled", allow_duplicate=True),
        Input("execsum-pdf-interval", "n_intervals"),
        State("execsum-pdf-job", "data"),
        State("execsum-es-status", "data"),
        State("execsum-config-store", "data"),
        State("execsum-mode", "data"),
        State("execsum-default-signinfo", "data"),
        prevent_initial_call=True,
    )
    def poll_pdf_job(_n, job_id, es_status, cfg, mode, default_signed):
        if not job_id or job_id not in _execsum_pdf_jobs:
            raise PreventUpdate

        job = _execsum_pdf_jobs[job_id]

        if not job.get("done"):
            raise PreventUpdate

        # decide whether button should be enabled again (only when all_signed)
        mode = (mode or "detail").strip().lower()
        if mode == "default":
            can_enable = bool(default_signed)
        else:
            can_enable = bool(cfg) and bool((es_status or {}).get("all_signed"))

        
        btn_disabled = not can_enable
        btn_style = PDF_BTN_ENABLED_STYLE if can_enable else PDF_BTN_DISABLED_STYLE

        err = job.get("error")
        if err:
            _execsum_pdf_jobs.pop(job_id, None)
            return btn_disabled, btn_style, f"Upload failed: {err}", None, True

        msg = job.get("msg") or "Done."
        _execsum_pdf_jobs.pop(job_id, None)
        return btn_disabled, btn_style, msg, None, True

    
    # ----------------------------
    # Populate the user name
    # ----------------------------
    @app.callback(
        Output("execsum-whoami-name", "data"),
        Input("execsum-sync", "n_clicks"),   # or any input that happens early
        prevent_initial_call=False,
        )
    def load_whoami(_):
        return _get_fullname_safe()

    # ----------------------------
    # Signature button style driver
    # ----------------------------
    @app.callback(
        Output({"type": "execsum-signee-upload", "name": ALL}, "style"),
        Input("execsum-sig-busy", "data"),
        State({"type": "execsum-signee-upload", "name": ALL}, "id"),
    )
    def style_sig_buttons_while_busy(busy, ids):
        busy_name = (busy or {}).get("name")

        # If reset is running, grey out ALL signee buttons
        if busy_name == "__RESET__":
            return [SIG_BTN_STYLE_BUSY for _ in (ids or [])]

        out = []
        for _id in (ids or []):
            nm = (_id or {}).get("name")
            out.append(SIG_BTN_STYLE_BUSY if (busy_name and nm == busy_name) else SIG_BTN_STYLE_NORMAL)
        return out

    # ----------------------------
    # Disable RESET while a sig job or Modal is running (avoid double cllick/racing jobs...)
    # ----------------------------
    @app.callback(
        Output("execsum-reset-es", "disabled"),
        Output("execsum-reset-role-msg", "children"),
        Output("execsum-reset-role-msg", "style"),
        Input("execsum-sig-busy", "data"),
        Input("execsum-reset-confirm-modal", "is_open"),
        Input("execsum-config-store", "data"),
        Input("execsum-whoami-roles", "data"),
    )
    def disable_reset_while_busy_or_modal_and_roles(busy, is_open, cfg, whoami_roles):
        # base disable reasons
        base_disabled = bool(busy) or bool(is_open)

        cfg = cfg or {}
        user_role_ids = set()
        for x in (whoami_roles or []):
            try:
                user_role_ids.add(int(x))
            except Exception:
                pass

        required_role_ids = _reset_required_role_ids_from_cfg(cfg)

        # If no restriction (everybody negative OR smallest-rank signee has empty roles)
        if not required_role_ids:
            return (
                base_disabled,
                "",
                {"display": "none"},
            )

        # Resolve names for display
        role_map = _get_role_name_map()
        required_names = []
        for rid in required_role_ids:
            nm = role_map.get(int(rid))
            required_names.append(nm if nm else f"(id={rid})")

        has_role = bool(set(required_role_ids) & user_role_ids)

        msg = (
            "RESET requires one of the following User Role(s): "
            + ", ".join(required_names)
        )

        # If user lacks role -> disable RESET regardless of busy/modal
        disabled = base_disabled or (not has_role)

        style = {
            "marginTop": "6px",
            "marginBottom": "10px",
            "fontWeight": "800",
            "fontSize": "13px",
            "display": "block",
            "color": "#a33" if not has_role else "#666",
        }

        if not has_role:
            msg = "Not authorized. " + msg

        return disabled, msg, style

    # -----------------------------
    # Open/Close Modal + run reset only on “Yes”
    # -----------------------------
    @app.callback(
        Output("execsum-reset-confirm-modal", "is_open"),
        Input("execsum-reset-es", "n_clicks"),
        Input("execsum-reset-confirm-no", "n_clicks"),
        Input("execsum-reset-confirm-yes", "n_clicks"),
        State("execsum-reset-confirm-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_reset_confirm_modal(n_reset, n_no, n_yes, is_open):
        trig = ctx.triggered_id

        if trig == "execsum-reset-es":
            # open modal
            return True

        if trig in ("execsum-reset-confirm-no", "execsum-reset-confirm-yes"):
            # close modal on either choice
            return False

        return is_open

    
    # ----------------------------
    # Upload config JSON
    # ----------------------------
    # Preload typeid on startup (optional nice touch)
    @app.callback(
        Output("execsum-typeid", "value"),
        Input("execsum-typeid-memory", "data"),
        prevent_initial_call=False,
    )
    def preload_typeid(mem):
        if not mem:
            raise PreventUpdate
        return mem.get("last_typeid")

   

   
    
    # ----------------------------
    # Start job callback which should be triggered by clicking the button
    # ----------------------------
    @app.callback(
        Output("execsum-job-id", "data"),
        Output("execsum-interval", "disabled"),
        Output("execsum-sync", "children"),
        Output("execsum-sync", "style"),
        Output("execsum-sync", "disabled"),
        Output("execsum-pid-table", "data"),
        Output("execsum-cache-key", "data"),
        Output("execsum-config-store", "data"),
        Output("execsum-config-status", "children"),
        Output("execsum-typeid-memory", "data"),
        Output("execsum-type-name", "data"),

        Output("execsum-selected-pid", "data", allow_duplicate=True),
        Output("execsum-plot-selected-pids", "data", allow_duplicate=True),
        Output("execsum-pid-table", "selected_rows", allow_duplicate=True),
        Output("execsum-pid-table", "active_cell", allow_duplicate=True),
        Output("execsum-todos-existing", "data", allow_duplicate=True),
        Output("execsum-todos-state", "data", allow_duplicate=True),

        Output("execsum-mode", "data", allow_duplicate=True),
        Output("execsum-has-config", "data", allow_duplicate=True),
        Output("execsum-default-signed", "data", allow_duplicate=True),
        Output("execsum-default-signinfo", "data", allow_duplicate=True),

        Input("execsum-sync", "n_clicks"),
        State("execsum-typeid", "value"),

        State("execsum-mode", "data"),
        prevent_initial_call=True,
    )
    def start_execsum_sync(n_clicks, typeid, mode_now):
        if not n_clicks:
            raise PreventUpdate

        green = {
            "fontSize":"20px","padding":"14px 32px","backgroundColor":"#4CAF50",
            "color":"white","border":"none","borderRadius":"8px","cursor":"pointer",
            "transition":"all 0.2s ease-in-out","marginRight":"10px",
        }
        orange = dict(green, **{"backgroundColor":"#f39c12","cursor":"not-allowed"})
        red = dict(green, **{"backgroundColor":"#e74c3c"})

        typeid = (typeid or "").strip()
        if not typeid:
            return (None, True, "Enter TypeID", red, False, no_update, no_update,
                    no_update, "Enter Component Type ID first.", no_update, no_update,
                        no_update,no_update,no_update,no_update,no_update,no_update,
                        no_update, False, False, None)

        # Start background job immediately (config + pids happen in worker now)
        job_id = f"EXECSUM-{int(time.time()*1000)}"
        _execsum_jobs[job_id] = {
            "processed": 0,
            "total": 0,
            "done": False,
            "error": None,
            "rows": [],
            "cache_key": None,
            "stage": "starting",
            "typeid": typeid,
            "cfg": None,
            "cfg_msg": "",
            "type_name": "",
        }

        #mode_now = (mode_now or "detail").strip().lower()
        mode_now = (mode_now).strip().lower()
        
        threading.Thread(target=_execsum_sync_worker, args=(job_id,), daemon=True).start()

        # Return immediately so UI turns orange right away
        return (
            job_id,
            False,
            "Downloading config...",
            orange,
            True,
            [],          # clear pid table while syncing
            None,        # cache-key not ready yet
            None,        # config not ready yet
            "Downloading config from HWDB…",
            {"last_typeid": typeid},
            "",          # type_name not ready yet
            None,        # execsum-selected-pid
            [],          # execsum-plot-selected-pids  (THIS fixes the bug)
            [],          # selected_rows
            None,        # active_cell
            None,        # execsum-todos-existing
            None,        # execsum-todos-state
            mode_now,    # keep whatever the user set pre-sync...
            False,       # has_config unknown until worker returns
            False,       # reset default signed every sync
            None,        # reset default signinfo
        )


    # ----------------------------
    # Poll progress (this is triggered by interval)
    # ----------------------------
    @app.callback(
        Output("execsum-sync", "children", allow_duplicate=True),
        Output("execsum-sync", "style", allow_duplicate=True),
        Output("execsum-sync", "disabled", allow_duplicate=True),
        Output("execsum-interval", "disabled", allow_duplicate=True),
        Output("execsum-job-id", "data", allow_duplicate=True),
        Output("execsum-pid-table", "data", allow_duplicate=True),
        Output("execsum-cache-key", "data", allow_duplicate=True),

        # Publish config + status + type name as the worker obtains them
        Output("execsum-config-store", "data", allow_duplicate=True),
        Output("execsum-config-status", "children", allow_duplicate=True),
        Output("execsum-type-name", "data", allow_duplicate=True),

        Output("execsum-mode", "data", allow_duplicate=True),
        Output("execsum-has-config", "data", allow_duplicate=True),

        Input("execsum-interval", "n_intervals"),
        State("execsum-job-id", "data"),

        State("execsum-mode", "data"),
        prevent_initial_call=True,
    )
    def poll_execsum_sync(_, job_id, mode_now):
        if not job_id or job_id not in _execsum_jobs:
            raise PreventUpdate

        green = {
            "fontSize":"20px","padding":"14px 32px","backgroundColor":"#4CAF50",
            "color":"white","border":"none","borderRadius":"8px","cursor":"pointer",
            "transition":"all 0.2s ease-in-out","marginRight":"10px",
        }
        orange = dict(green, **{"backgroundColor":"#f39c12","cursor":"not-allowed"})
        red = dict(green, **{"backgroundColor":"#e74c3c"})

        job = _execsum_jobs[job_id]

        # If worker errored
        if job.get("error"):
            err = job["error"]
            _execsum_jobs.pop(job_id, None)
            return (
                f"Error: {err}", red, False, True, None,
                no_update, no_update,
                no_update, err, no_update,
                mode_now, False
            )

        done = bool(job.get("done", False))
        stage = job.get("stage", "")

        # publish these whenever available (safe to repeat)
        cfg = job.get("cfg")
        cfg_msg = job.get("cfg_msg") or ""
        type_name = job.get("type_name") or ""

        mode_now = (mode_now or "detail").strip().lower()
        has_config = bool(job.get("has_config"))
        stage = job.get("stage", "")

        # Auto-switch rule:
        # - If the user wants DETAIL, but config is missing (after config lookup), switch to DEFAULT.
        effective_mode = mode_now
        if stage in ("fetching_pids", "done") and (mode_now == "detail") and (not has_config):
            effective_mode = "default"

        if not done:
            if stage == "fetching_config":
                return (
                    "Downloading config...", orange, True, False, job_id,
                    no_update, no_update,
                    cfg, (cfg_msg or "Downloading config from HWDB…"), type_name, effective_mode, has_config
                )

            if stage == "fetching_pids":
                return (
                    "Fetching PID list...", orange, True, False, job_id,
                    no_update, no_update,
                    cfg, (cfg_msg or "Config loaded."), type_name, effective_mode, has_config
                )

            return (
                "Working...", orange, True, False, job_id,
                no_update, no_update,
                cfg, (cfg_msg or "Working…"), type_name, effective_mode, has_config
            )

        # DONE: publish rows/cache/config/type_name and reset button
        rows = job.get("rows") or []
        cache_key = job.get("cache_key")

        cfg = job.get("cfg")
        cfg_msg = job.get("cfg_msg") or ""
        type_name = job.get("type_name") or ""

        _execsum_jobs.pop(job_id, None)

        return (
            "Sync to the HWDB", green, False, True, None,
            rows, cache_key,
            cfg, cfg_msg, type_name, effective_mode, has_config
        )

   

    # ----------------------------
    # Keep execsum-todos-state updated when user clicks checkboxes
    # ----------------------------
    @app.callback(
        Output("execsum-todos-state", "data", allow_duplicate=True),
        Input("execsum-todos-checklist", "value"),
        State("execsum-todos-existing", "data"),
        State("execsum-todos-state", "data"),
        prevent_initial_call=True,
    )
    def update_todos_state(checked_values, existing, current):

        base = existing if isinstance(existing, dict) else (current if isinstance(current, dict) else {})
        cl = base.get("check_list") or []
        if not isinstance(cl, list):
            cl = []
        checked = checked_values or []
        checked = [int(i) for i in checked if str(i).isdigit() and 0 <= int(i) < len(cl)]
        return {"title": str(base.get("title") or "").strip(), "check_list": cl, "checked": checked}

    
    # ----------------------------
    # Selects row in the PID table
    # ----------------------------
    @app.callback(
        Output("execsum-pid-table", "selected_rows"),
        Output("execsum-selected-pid", "data"),
        Output("execsum-pid-table", "data", allow_duplicate=True),
        Output("execsum-plot-selected-pids", "data", allow_duplicate=True),
        Output("execsum-pid-table", "active_cell", allow_duplicate=True),
        Input("execsum-pid-table", "active_cell"),
        State("execsum-pid-table", "data"),
        State("execsum-plot-selected-pids", "data"),
        prevent_initial_call=True,
    )
    def select_row(active_cell, table_data, selected_pids):
        if not active_cell or not table_data:
            raise PreventUpdate

        #r = active_cell.get("row")
        #col = active_cell.get("column_id")
        #if r is None or r >= len(table_data):
        #    raise PreventUpdate
        #
        #pid = str((table_data[r] or {}).get("pid") or "").strip()
        #if not pid:
        #    raise PreventUpdate

        r = active_cell.get("row")
        col = active_cell.get("column_id")

        # Prefer Dash DataTable's stable row_id.
        # This avoids pagination bugs where active_cell["row"] is page-relative.
        pid = str(active_cell.get("row_id") or "").strip()

        # Fallback for older cached data that may not have row_id yet.
        if not pid:
            if r is None or r >= len(table_data):
                raise PreventUpdate
            pid = str((table_data[r] or {}).get("pid") or "").strip()

        if not pid:
            raise PreventUpdate
        

        selected_set = set(selected_pids or [])

        # A) Click on "Selected" column: toggle ONLY, then reset active_cell
        if col == "selected":
            if pid in selected_set:
                selected_set.remove(pid)
            else:
                selected_set.add(pid)

            new_table = []
            for row in (table_data or []):
                if not isinstance(row, dict):
                    continue
                rr = dict(row)
                rpid = str(rr.get("pid") or "").strip()
                rr["selected"] = "✅" if (rpid and rpid in selected_set) else "☐"
                new_table.append(rr)

            # Reset active_cell so the next click on the same cell re-fires!!
            return no_update, no_update, new_table, sorted(selected_set), None

        # B) Click on any other column: primary select + force checked
        selected_set.add(pid)

        new_table = []
        for row in (table_data or []):
            if not isinstance(row, dict):
                continue
            rr = dict(row)
            rpid = str(rr.get("pid") or "").strip()
            rr["selected"] = "✅" if (rpid and rpid in selected_set) else "☐"
            new_table.append(rr)

        # Keep active_cell as-is here
        return [r], pid, new_table, sorted(selected_set), active_cell
    

    # ----------------------------
    # For the "Clear/Select" and PID range as well
    # ----------------------------
    @app.callback(
        Output("execsum-pid-table", "data", allow_duplicate=True),
        Output("execsum-plot-selected-pids", "data", allow_duplicate=True),
        Output("execsum-range-start", "value"),
        Output("execsum-range-end", "value"),
        Input("execsum-clear-selected", "n_clicks"),
        Input("execsum-select-all", "n_clicks"),
        Input("execsum-select-range", "n_clicks"),
        Input("execsum-clear-range", "n_clicks"),
        State("execsum-pid-table", "data"),
        State("execsum-plot-selected-pids", "data"),
        State("execsum-range-start", "value"),
        State("execsum-range-end", "value"),
        prevent_initial_call=True,
    )
    def selection_and_range_controls(
        n_clear, n_all, n_sel_range, n_clr_range,
        table_data, selected_pids, start_val, end_val
    ):
        if not table_data:
            raise PreventUpdate

        trig = ctx.triggered_id
        selected_set = set(str(x).strip() for x in (selected_pids or []) if str(x).strip())

        # Defaults: don't touch inputs
        out_start = no_update
        out_end = no_update

        all_pids = [
            str(r.get("pid") or "").strip()
            for r in (table_data or [])
            if isinstance(r, dict) and str(r.get("pid") or "").strip()
        ]

        if trig == "execsum-clear-selected":
            selected_set = set()

        elif trig == "execsum-select-all":
            selected_set = set(all_pids)

        elif trig == "execsum-select-range":
            s0 = _parse_item_input(start_val)
            s1 = _parse_item_input(end_val)
            if s0 is None or s1 is None:
                # nothing to do if inputs aren't valid
                raise PreventUpdate
            in_range = _pids_in_item_range(table_data, s0, s1)
            # "add range" behavior
            selected_set |= set(in_range)
            #selected_set = set(in_range) # to replace the selection by the selected PID range

        elif trig == "execsum-clear-range":
            s0 = _parse_item_input(start_val)
            s1 = _parse_item_input(end_val)

            # If range is valid, remove that subset; else just clear the boxes.
            if s0 is not None and s1 is not None:
                in_range = _pids_in_item_range(table_data, s0, s1)
                selected_set -= set(in_range)

            out_start = ""
            out_end = ""

        else:
            raise PreventUpdate

        # Rebuild table marks
        new_table = []
        for row in (table_data or []):
            if not isinstance(row, dict):
                continue
            rr = dict(row)
            pid = str(rr.get("pid") or "").strip()
            rr["selected"] = "✅" if (pid and pid in selected_set) else "☐"
            new_table.append(rr)

        return new_table, sorted(selected_set), out_start, out_end
    
    # ----------------------------
    # Populate the datetime display
    # ----------------------------
    @app.callback(
        Output("execsum-signoff-datetime-store", "data"),
        Input("execsum-selected-pid", "data"),
        prevent_initial_call=True,
    )
    def set_signoff_datetime_store(pid):
        if not pid:
            raise PreventUpdate
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    # ----------------------------
    # Fill each row’s timestamp from HWDB when already signed, else show “now”
    # ----------------------------
    @app.callback(
        Output({"type":"execsum-signee-ts", "name": ALL}, "children"),
        Output({"type":"execsum-signee-ts-store", "name": ALL}, "data"),
        Input("execsum-es-existing", "data"),
        State({"type":"execsum-signee-ts", "name": ALL}, "id"),
        prevent_initial_call=False,
    )
    def fill_signee_timestamps(es_existing, ts_ids):
        m = _es_map_by_name(es_existing or [])
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        shown = []
        stored = []
        for iid in (ts_ids or []):
            nm = (iid or {}).get("name")
            ent = m.get(nm) or {}
            ts = (ent.get("timestamp") or "").strip()

            if ts:
                # already signed on HWDB
                shown.append(ts)
                stored.append(ts)   # store same
            else:
                # not signed yet: show “now” and store it for upload
                shown.append(now_str)
                stored.append(now_str)

        return shown, stored


    # ----------------------------
    # Disable per-signee comments when everything is already signed
    # ----------------------------
    @app.callback(
        Output({"type":"execsum-signee-comments", "name": ALL}, "disabled"),
        Input("execsum-es-status", "data"),
        State({"type":"execsum-signee-comments", "name": ALL}, "id"),
    )
    def lock_signee_comments_when_all_signed(status, ids):
        locked = bool((status or {}).get("all_signed"))
        return [locked for _ in (ids or [])]
    
    # ----------------------------
    # Prefill "per-signee" comments from the HWDB
    # ----------------------------
    @app.callback(
        Output({"type":"execsum-signee-comments", "name": ALL}, "value"),
        Input("execsum-es-existing", "data"),
        State({"type":"execsum-signee-comments", "name": ALL}, "id"),
        prevent_initial_call=False,
    )
    def prefill_signee_comments(es_existing, ids):
        m = _es_map_by_name(es_existing or [])
        out = []
        for iid in (ids or []):
            nm = (iid or {}).get("name")
            ent = m.get(nm) or {}
            out.append((ent.get("comments") or "").strip())
        return out

    # ----------------------------
    # Prefill the Component Status Dropdown menu
    # ----------------------------
    @app.callback(
        Output("execsum-status-dropdown", "value"),
        Input("execsum-selected-pid", "data"),
        State("execsum-cache-key", "data"),
        prevent_initial_call=True,
    )
    def prefill_status_dropdown(pid, cache_key):
        if not pid or not cache_key or cache_key not in _execsum_cache:
            raise PreventUpdate

        it = (_execsum_cache[cache_key]["by_pid"].get(pid, {}) or {}).get("item", {}) or {}
        status_text = str(_safe(it.get("status", ""))).strip()

        # status_text may already be the label; map to ID
        if status_text in STATUS_ID_BY_LABEL:
            return STATUS_ID_BY_LABEL[status_text]

        # if HWDB ever returns numeric id, handle that too
        try:
            sid = int(status_text)
            if sid in STATUS_LABEL_BY_ID:
                return sid
        except Exception:
            pass

        return 0  # Unknown fallback

    # ----------------------------
    # Capture any change user makes on the Status dropdown menu
    # ----------------------------
    @app.callback(
        Output("execsum-selected-status", "data"),
        Input("execsum-status-dropdown", "value"),
        State("execsum-selected-pid", "data"),
        prevent_initial_call=True,
    )
    def store_user_selected_status(status_id, pid):
        if not pid:
            raise PreventUpdate
        if status_id is None:
            raise PreventUpdate
        return {"pid": str(pid), "status_id": int(status_id)}
    
   
    # ----------------------------
    # Clear the signature status message whenever the context hanges
    # ----------------------------
    @app.callback(
        Output("execsum-generate-status", "children", allow_duplicate=True),
        Input("execsum-selected-pid", "data"),
        Input("execsum-es-existing", "data"),
        prevent_initial_call=True,
    )
    def clear_generate_status_on_context_change(_pid, _es):
        # Any time selecting a new PID or ES data refreshes, wipe stale messages!
        return ""
    
    # ----------------------------
    # Pre-fill the switches based on what the HWDB has
    # ----------------------------
    @app.callback(
        Output("execsum-flag-certified", "value"),
        Output("execsum-flag-uploaded", "value"),
        Input("execsum-selected-pid", "data"),
        #Input("execsum-form-container", "children"),   # Ensures switches exist
        Input("execsum-form-block", "children"),
        State("execsum-cache-key", "data"),
        prevent_initial_call=True,
    )
    def preload_flags(pid, _form_children, cache_key):
        if not pid or not cache_key or cache_key not in _execsum_cache:
            raise PreventUpdate
        item = (_execsum_cache[cache_key]["by_pid"].get(pid, {}) or {}).get("item", {}) or {}
        return bool(item.get("certified_qaqc")), bool(item.get("qaqc_uploaded"))
    
    # ----------------------------
    # Flip lable color (green/red)
    # ----------------------------
    @app.callback(
        Output("execsum-flag-certified-card", "className"),
        Output("execsum-flag-certified", "label"),
        Input("execsum-flag-certified", "value"),
    )
    def style_certified_switch(val):
        if val:
            return "execsum-flag-card execsum-pass", "PASS"
        return "execsum-flag-card execsum-fail", "FAIL"

    @app.callback(
        Output("execsum-flag-uploaded-card", "className"),
        Output("execsum-flag-uploaded", "label"),
        Input("execsum-flag-uploaded", "value"),
    )
    def style_uploaded_switch(val):
        if val:
            return "execsum-flag-card execsum-pass", "PASS"
        return "execsum-flag-card execsum-fail", "FAIL"
    
    # ----------------------------
    # Enable the PDF button only when all signed
    # ----------------------------
    @app.callback(
        Output("execsum-generate-upload", "disabled"),
        Input("execsum-es-status", "data"),
        Input("execsum-mode", "data"),
        Input("execsum-default-signed", "data"),
        State("execsum-config-store", "data"),
    )
    def enable_generate(status, mode, default_signed, cfg):
        mode = (mode or "detail").strip().lower()

        # DEFAULT: allow once default sign happened (config may be missing)
        if mode == "default":
            return not bool(default_signed)

        # DETAIL: the old rule!!
        if not cfg:
            return True
        if not status:
            return True
        return not bool(status.get("all_signed"))

    # ----------------------------
    # Hide RESET and Plots in the default mode
    # ----------------------------
    @app.callback(
        Output("execsum-reset-wrapper", "style"),
        Output("execsum-plots-panel", "style"),
        Output("execsum-form-panel", "style"),
        Input("execsum-mode", "data"),
        Input("execsum-has-config", "data"),
    )
    def hide_reset_and_plots_in_default(mode, has_config):
        mode = (mode or "detail").strip().lower()

        # Safety: if config doesn't exist, treat it as default UI
        effective_mode = "default" if (mode == "default" or not bool(has_config)) else "detail"

        if effective_mode == "default":
            # Hide RESET completely (no empty space)
            reset_style = {"display": "none"}

            # Hide Plots panel completely
            plots_style = {"display": "none"}

            # Let the left panel use full width
            form_style = {"flex": "1 1 100%", "minWidth": 0}

            return reset_style, plots_style, form_style

        # DETAIL mode: show everything normally
        reset_style = {"display": "block"}
        plots_style = {"flex": "1 1 55%", "minWidth": 0, "display": "block"}
        form_style  = {"flex": "1 1 45%", "minWidth": 0}

        return reset_style, plots_style, form_style
    
    # ----------------------------
    # Read existing ES from HWDB when PID is selected
    # ----------------------------
    @app.callback(
        Output("execsum-es-existing", "data"),
        Output("execsum-todos-existing", "data"),
        Output("execsum-todos-state", "data"),
        Input("execsum-selected-pid", "data"),
        State("execsum-config-store", "data"),
        prevent_initial_call=True,
    )
    def load_existing_es_and_todos(pid, cfg):
        if not pid:
            raise PreventUpdate

        es_list, todos_payload = fetch_latest_es_and_todos(str(pid))

        # Build a default todos payload from config if HWDB has none yet
        todos_cfg = (cfg or {}).get("todos") or {}
        title = (todos_cfg.get("title") or "").strip()
        check_list = todos_cfg.get("check_list") or []

        if not isinstance(check_list, list):
            check_list = []

        # normalize stored state: we’ll represent checked items as indices in "checked"
        if not isinstance(todos_payload, dict):
            todos_payload = {
                "title": title,
                "check_list": check_list,
                "checked": [],
            }

        # Ensure it matches current config list length/text
        # (If config changed,keep "checked" indices that are still valid)
        checked = todos_payload.get("checked") or []
        if not isinstance(checked, list):
            checked = []
        checked = [int(i) for i in checked if str(i).isdigit() and 0 <= int(i) < len(check_list)]

        todos_payload = {
            "title": title or (todos_payload.get("title") or ""),
            "check_list": check_list,
            "checked": checked,
        }

        # Set both existing + state to the same (UI starts from saved HWDB state)
        return es_list, todos_payload, todos_payload
    
    
    # ----------------------------
    # Compute “which buttons are enabled” + “is PDF allowed”
    # ----------------------------
    @app.callback(
        Output("execsum-es-status", "data"),
        Input("execsum-config-store", "data"),
        Input("execsum-es-existing", "data"),
        Input("execsum-whoami-roles", "data"), 
    )
    def compute_es_status(cfg, es_existing, whoami_roles):
        cfg = cfg or {}
        signees = cfg.get("signees") or []
        existing = es_existing or []

        # Who has signed (by name)
        signed_names = set()

        # Only track NON-NEGATIVE signed ranks for ordering logic
        signed_nonneg_ranks = set()

        # whoami
        user_role_ids = set(int(x) for x in (whoami_roles or []) if str(x).isdigit())
        role_map = _get_role_name_map()
        
        # Build a quick map name->rank from cfg (authoritative)
        cfg_rank_by_name = {}
        for s in signees:
            if not isinstance(s, dict):
                continue
            nm = (s.get("name") or "").strip()
            try:
                rk = int(s.get("rank", -1))
            except Exception:
                rk = -1
            if nm:
                cfg_rank_by_name[nm] = rk

        # Read ES: consider someone "signed" if name+signature present.
        for ent in existing:
            if not isinstance(ent, dict):
                continue
            nm = (ent.get("name") or "").strip()
            sig = (ent.get("signature") or "").strip()
            if not (nm and sig):
                continue

            signed_names.add(nm)

            # Rank for ordering should come from cfg (not from ES payload)
            rk = cfg_rank_by_name.get(nm, None)
            if rk is None:
                continue
            if rk >= 0:
                signed_nonneg_ranks.add(int(rk))

        # All non-negative ranks in config (ordered phase)
        nonneg = sorted(
            [int(s.get("rank")) for s in signees
            if isinstance(s, dict) and int(s.get("rank", -1)) >= 0],
            reverse=True
        )

        # Next required rank is the highest (descending) not yet signed
        next_required_rank = None
        for rk in nonneg:
            if rk not in signed_nonneg_ranks:
                next_required_rank = rk
                break

        per = {}
        for s in signees:
            if not isinstance(s, dict):
                continue
            nm = (s.get("name") or "").strip()
            if not nm:
                continue
            try:
                rk = int(s.get("rank", -1))
            except Exception:
                rk = -1

            already = (nm in signed_names)

            # RULES:
            # - rk < 0: can sign anytime (unless already signed)
            # - rk >= 0: must match next_required_rank (unless already signed)
            if rk < 0:
                allowed = not already
            else:
                #allowed = (not already) and (next_required_rank == rk) if nonneg else (not already)
                # All negatives must finish before any non-negative can sign!!!
                any_unsigned_negative = any(
                    (int(s.get("rank", -1)) < 0) and ((s.get("name") or "").strip() not in signed_names)
                    for s in signees if isinstance(s, dict) and (s.get("name") or "").strip()
                )
                allowed = (not already) and (not any_unsigned_negative) and (next_required_rank == rk) if nonneg else (not already)

            # roles required for this signee
            req_roles = s.get("roles") or []
            req_roles = [int(x) for x in req_roles if isinstance(x, (int, str)) and str(x).isdigit()]

            role_ok = True
            role_reason = ""
            if req_roles:
                role_ok = bool(set(req_roles) & user_role_ids)
                if not role_ok:
                    req_names = [role_map.get(int(r), f"(id={r})") for r in req_roles]
                    role_reason = "Requires role(s): " + ", ".join(req_names)

            allowed = allowed and role_ok
                
            #per[nm] = {"rank": rk, "already": already, "allowed": allowed}
            per[nm] = {"rank": rk, "already": already, "allowed": allowed, "role_ok": role_ok, "reason": role_reason}

        # "All signed" means all configured signees have signatures
        all_signed = all(
            ((s.get("name") or "").strip() in signed_names)
            for s in signees
            if isinstance(s, dict) and (s.get("name") or "").strip()
        )

        return {
            "per": per,
            "all_signed": all_signed,
            "next_required_rank": next_required_rank,
            "signed_names": sorted(signed_names),
            "signed_nonneg_ranks": sorted(signed_nonneg_ranks),
        }

    
    # ----------------------------
    # Enable/disable each “Upload this signature” button dynamically
    # ----------------------------
    @app.callback(
        Output({"type":"execsum-signee-upload","name":ALL}, "disabled"),
        Input("execsum-es-status", "data"),
        State({"type":"execsum-signee-upload","name":ALL}, "id"),
    )
    def enable_sig_buttons(status, ids):
        if not status or not ids:
            raise PreventUpdate
        per = status.get("per") or {}
        disabled = []
        for _id in ids:
            nm = _id.get("name")
            info = per.get(nm) or {}
            disabled.append(not bool(info.get("allowed")))
        return disabled
    # ----------------------------
    # whoami
    # ----------------------------
    @app.callback(
        Output("execsum-whoami-roles", "data"),
        Input("execsum-sync", "n_clicks"),
        prevent_initial_call=False,
    )
    def load_whoami_roles(_):
        return sorted(list(_whoami_role_ids()))

    # ----------------------------
    # Toggle button between detail and default
    # ----------------------------
    @app.callback(
        Output("execsum-mode", "data"),
        Input("execsum-mode-toggle", "n_clicks"),
        State("execsum-mode", "data"),
        #State("execsum-has-config", "data"), # comment this out, to allow to toggle always
        prevent_initial_call=True,
    )
    def toggle_execsum_mode(n, mode):
        # If no config exists on HWDB, force default mode
        #if not has_config:
        #    return "default"
        mode = (mode or "detail").strip().lower()
        return "default" if mode == "detail" else "detail"


    @app.callback(
        Output("execsum-mode-toggle", "children"),
        Output("execsum-mode-toggle", "style"),
        Output("execsum-mode-toggle", "disabled"),
        Input("execsum-mode", "data"),
        #Input("execsum-has-config", "data"),
    )
    def style_execsum_mode_button(mode):
        #if not has_config:
        #    return "DEFAULT", MODE_BTN_DISABLED, True

        mode = (mode or "detail").strip().lower()
        if mode == "default":
            return "DEFAULT", MODE_BTN_DEFAULT, False
        return "DETAIL", MODE_BTN_DETAIL, False

    # ----------------------------
    # Sign for the default version
    # ----------------------------
    @app.callback(
        Output("execsum-default-signed", "data"),
        Output("execsum-default-signinfo", "data"),
        Output("execsum-generate-status", "children", allow_duplicate=True),
        Output("execsum-pid-table", "data", allow_duplicate=True),
        
        Input("execsum-default-sign-btn", "n_clicks"),
        State("execsum-selected-pid", "data"),
        State("execsum-cache-key", "data"),
        State("execsum-status-dropdown", "value"),
        State("execsum-flag-certified", "value"),
        State("execsum-flag-uploaded", "value"),
        State("execsum-default-comments", "value"),
        State("execsum-whoami-name", "data"),
        State("execsum-plot-selected-pids", "data"),
        State("execsum-pid-table", "data"),
        prevent_initial_call=True,
    )
    def default_mode_sign_and_patch(n, pid, cache_key, status_id, certified_flag, uploaded_flag,
                                    comments_text, whoami_name, selected_pids, table_data):
        if not n:
            raise PreventUpdate
        pid = str(pid or "").strip()
        if not pid:
            raise PreventUpdate

        who = (whoami_name or "—").strip() or "—"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Decide status label/id
        sid = _status_id_from_anywhere(status_id=status_id, pid=pid, cache_key=cache_key)
        status_label = STATUS_LABEL_BY_ID.get(sid, "Unknown")

        cert_val = bool(certified_flag)
        upl_val = bool(uploaded_flag)

        # Patch ONLY checked; fallback to selected PID
        pids = [str(x).strip() for x in (selected_pids or []) if str(x).strip()]
        if not pids:
            pids = [pid]

        # unique preserve order
        seen = set()
        pids = [x for x in pids if x and not (x in seen or seen.add(x))]

        # comments -> HW item comments
        comment = (comments_text or "").strip()
        if not comment:
            comment = f"signed by {who}".strip()

        # run patches
        executor = ra_util._executor
        futs = [
            executor.submit(
                _patch_one_hwitem_flags,
                part_id=each_pid,
                status_id=sid,
                certified_qaqc=cert_val,
                qaqc_uploaded=upl_val,
                comment=comment,
            )
            for each_pid in pids
        ]

        ok = 0
        fails = []
        for fut in futs:
            _pid2, success, err = fut.result()
            if success:
                ok += 1
            else:
                fails.append((_pid2, err))

        if fails:
            head = "; ".join([f"{p}: {e}" for p, e in fails[:3]])
            more = "" if len(fails) <= 3 else f" (+{len(fails)-3} more)"
            msg = f"Default sign done, but patch failed for {len(fails)}/{len(pids)}: {head}{more}"
        else:
            msg = f"Default sign done. Patched HWDB flags/comments for {ok}/{len(pids)} item(s)."

        # update server-side cache snapshot (status/flags)
        try:
            if cache_key and cache_key in _execsum_cache:
                bucket = _execsum_cache[cache_key]
                by_pid = bucket.get("by_pid", {}) or {}
                subtree_cache = bucket.get("subtree_cache", {}) or {}
                for each_pid in pids:
                    ent = by_pid.get(each_pid)
                    if isinstance(ent, dict):
                        it = ent.get("item")
                        if isinstance(it, dict):
                            it["status"] = status_label
                            it["certified_qaqc"] = cert_val
                            it["qaqc_uploaded"] = upl_val
                            it["comments"] = comment
                    sc = subtree_cache.get(each_pid)
                    if isinstance(sc, dict) and "status_flags" in sc:
                        sc.pop("status_flags", None)
        except Exception as e:
            logger.warning(f"[ExecSum] default-mode cache sync failed: {e}")

        # update visible pid table
        patched_set = set(pids)
        new_table = []
        for row in (table_data or []):
            if not isinstance(row, dict):
                continue
            rpid = str(row.get("pid") or "").strip()
            if rpid and rpid in patched_set:
                rr = dict(row)
                rr["status"] = status_label
                rr["certified"] = "✅" if cert_val else "❌"
                rr["uploaded"]  = "✅" if upl_val else "❌"
                new_table.append(rr)
            else:
                new_table.append(row)

        signinfo = {
            "signature": who,
            "comments": comment,
            "timestamp": ts,
            "status_label": status_label,
            "certified_flag": cert_val,
            "uploaded_flag": upl_val,
        }

        return True, signinfo, msg, new_table


    
    # ----------------------------
    # Upload signature (merge into ES then POST TEST)
    # ----------------------------
    @app.callback(
        Output("execsum-sig-job", "data"),
        Output("execsum-sig-interval", "disabled"),
        Output("execsum-sig-busy", "data"),
        Output("execsum-generate-status", "children", allow_duplicate=True),
        Input({"type": "execsum-signee-upload", "name": ALL}, "n_clicks"),
        State({"type":"execsum-signee-upload","name":ALL}, "id"),
        State({"type":"execsum-signee-input","name":ALL}, "value"),
        State({"type":"execsum-signee-input","name":ALL}, "id"),
        State({"type":"execsum-signee-ts-store","name":ALL}, "data"),
        State({"type":"execsum-signee-ts-store","name":ALL}, "id"),
        State({"type":"execsum-signee-comments", "name": ALL}, "value"),
        State({"type":"execsum-signee-comments", "name": ALL}, "id"),
        State("execsum-status-dropdown", "value"),
        State("execsum-flag-certified", "value"),
        State("execsum-flag-uploaded", "value"),
        
        #State("execsum-subcomp-grid", "rowData"),
        State("execsum-plot-selected-pids", "data"),
        
        State("execsum-cache-key", "data"),
        State("execsum-pid-table", "data"),
        State("execsum-selected-pid", "data"),
        State("execsum-config-store", "data"),
        State("execsum-todos-state", "data"),
        prevent_initial_call=True,
    )
    def start_signature_job(n_clicks_list, upload_ids,
                            input_vals, input_ids,
                            ts_store_vals, ts_store_ids,
                            c_vals, c_ids,
                            status_id, certified_flag, uploaded_flag,
                            selected_pids, cache_key,
                            pid_table_data,
                            pid, cfg,
                            todos_state):
        if not pid:
            raise PreventUpdate

        trig = ctx.triggered_id
        if not isinstance(trig, dict) or trig.get("type") != "execsum-signee-upload":
            raise PreventUpdate

        name = (trig.get("name") or "").strip()
        if not name:
            raise PreventUpdate

        todos_state_ = todos_state or {}
        
        # require real click
        idx = None
        for i, uid in enumerate(upload_ids or []):
            if isinstance(uid, dict) and uid.get("type") == "execsum-signee-upload" and uid.get("name") == name:
                idx = i
                break
        if idx is None:
            raise PreventUpdate

        n = (n_clicks_list or [])[idx] if idx < len(n_clicks_list or []) else 0
        if not n or int(n) <= 0:
            raise PreventUpdate

        # pull signature text
        sig_text = ""
        for v, iid in zip(input_vals or [], input_ids or []):
            if isinstance(iid, dict) and iid.get("name") == name:
                sig_text = (v or "").strip()
                break
        if not sig_text:
            # don’t start job; keep UI normal
            return None, True, None, "Please type a signature first."

        # timestamp
        ts_value = ""
        for v, iid in zip(ts_store_vals or [], ts_store_ids or []):
            if isinstance(iid, dict) and iid.get("name") == name:
                ts_value = (v or "").strip()
                break
        if not ts_value:
            ts_value = datetime.now().strftime("%Y-%m-%d %H:%M")

        # comments
        comments_value = ""
        for v, iid in zip(c_vals or [], c_ids or []):
            if isinstance(iid, dict) and iid.get("name") == name:
                comments_value = (v or "").strip()
                break

        # rank from cfg
        rank = -1
        for s in (cfg or {}).get("signees") or []:
            if isinstance(s, dict) and (s.get("name") or "").strip() == name:
                try:
                    rank = int(s.get("rank", -1))
                except Exception:
                    rank = -1
                break



        # ---------------------------------------------------------
        # Role-gate this signee (whoami + get_roles for names)
        # ---------------------------------------------------------
        required_role_ids: list[int] = []
        for s in (cfg or {}).get("signees") or []:
            if isinstance(s, dict) and (s.get("name") or "").strip() == name:
                rr = s.get("roles", [])
                if isinstance(rr, list):
                    required_role_ids = []
                    for x in rr:
                        try:
                            required_role_ids.append(int(x))
                        except Exception:
                            pass
                break

        # If roles list is empty -> no restriction
        if required_role_ids:
            user_role_ids = _whoami_role_ids()

            # allow if user has ANY of the required roles
            if not (set(required_role_ids) & set(user_role_ids)):
                role_map = _get_role_name_map()
                required_names = []
                for rid in required_role_ids:
                    nm = role_map.get(int(rid))
                    required_names.append(nm if nm else f"(id={rid})")

                msg = (
                    f"Not authorized for '{name}'. "
                    f"This signee is required to have one of the following User Role(s): "
                    + ", ".join(required_names)
                )

                # Do NOT start the upload job
                return None, True, None, msg


            
        job_id = f"SIG-{int(time.time()*1000)}"
        _execsum_sig_jobs[job_id] = {"done": False, "error": None, "new_es": None, "msg": None, "new_table": None}


        
        # snapshot everything for worker
        pid_ = str(pid).strip()
        cfg_ = cfg or {}
        cache_key_ = cache_key
        pid_table_data_ = pid_table_data or []
        
        #subcomp_rowdata_ = subcomp_rowdata or []
        selected_pids_ = [str(x).strip() for x in (selected_pids or []) if str(x).strip()]
        
        status_id_ = status_id
        cert_val_ = bool(certified_flag)
        upl_val_  = bool(uploaded_flag)
    
        def _worker():
            try:
                existing_es = fetch_latest_es_list(pid_)
                new_es = merge_es_entry(
                    existing_es,
                    name=name,
                    signature=sig_text,
                    rank=rank,
                    timestamp=ts_value,
                    comments=comments_value,
                )

                # 1) POST ES test
                #post_es_test(pid_, new_es, comments=f"ES signature updated: {name}")
                post_es_test(
                    pid_,
                    new_es,
                    comments=f"ES signature updated: {name}",
                    todos_payload=todos_state_,
                )

                # 2) PATCH hwitem flags (ONLY checked PIDs; fallback to selected PID)
                sid = _status_id_from_anywhere(status_id=status_id_, pid=pid_, cache_key=cache_key_)
                status_label = STATUS_LABEL_BY_ID.get(sid, "Unknown")

                # Patch ONLY what user checked. If nothing checked, patch just the currently selected PID.
                pids = list(selected_pids_ or [])
                if not pids:
                    pids = [pid_]

                # unique, preserve order
                seen = set()
                pids = [x for x in pids if x and not (x in seen or seen.add(x))]

                comment = f"[ExecSum] signature '{name} uploaded, also Status, QAQC Certified, and Uploaded flags updated."

                executor = ra_util._executor
                futs = [
                    executor.submit(
                        _patch_one_hwitem_flags,
                        part_id=each_pid,
                        status_id=sid,
                        certified_qaqc=cert_val_,
                        qaqc_uploaded=upl_val_,
                        comment=comment,
                    )
                    for each_pid in pids
                ]

                ok = 0
                fails = []
                for fut in futs:
                    _pid2, success, err = fut.result()
                    if success:
                        ok += 1
                    else:
                        fails.append((_pid2, err))

                if not fails:
                    patch_msg = f"Patched HWDB flags for {ok}/{len(pids)} selected items."
                else:
                    head = "; ".join([f"{p}: {e}" for p, e in fails[:3]])
                    more = "" if len(fails) <= 3 else f" (+{len(fails)-3} more)"
                    patch_msg = f"Patched {ok}/{len(pids)} selected items; {len(fails)} failed: {head}{more}"


                # ---- Keep server-side cache consistent with what we just PATCHed ----
                try:
                    if cache_key_ and cache_key_ in _execsum_cache:
                        bucket = _execsum_cache[cache_key_]
                        by_pid = bucket.get("by_pid", {}) or {}
                        subtree_cache = bucket.get("subtree_cache", {}) or {}

                        for each_pid in pids:
                            # 1) Update by_pid item snapshot (used by status/flag reads)
                            ent = by_pid.get(each_pid)
                            if isinstance(ent, dict):
                                it = ent.get("item")
                                if isinstance(it, dict):
                                    it["status"] = status_label
                                    it["certified_qaqc"] = bool(cert_val_)
                                    it["qaqc_uploaded"] = bool(upl_val_)

                            # 2) Invalidate any cached status_flags for subtree rendering
                            sc = subtree_cache.get(each_pid)
                            if isinstance(sc, dict) and "status_flags" in sc:
                                sc.pop("status_flags", None)

                except Exception as e:
                    logger.warning(f"[ExecSum] cache sync after patch failed: {e}")

                    
                # update visible table
                patched_set = set(pids)
                new_table = []
                for row in pid_table_data_:
                    if not isinstance(row, dict):
                        continue
                    rpid = str(row.get("pid") or "").strip()
                    if rpid and rpid in patched_set:
                        rr = dict(row)
                        rr["status"] = status_label
                        rr["certified"] = "✅" if cert_val_ else "❌"
                        rr["uploaded"]  = "✅" if upl_val_ else "❌"
                        new_table.append(rr)
                    else:
                        new_table.append(row)

                _execsum_sig_jobs[job_id]["new_es"] = new_es
                _execsum_sig_jobs[job_id]["new_table"] = new_table
                _execsum_sig_jobs[job_id]["msg"] = f"Uploaded signature for {name}. {patch_msg}"
                _execsum_sig_jobs[job_id]["done"] = True

            except Exception as e:
                _execsum_sig_jobs[job_id]["error"] = str(e)
                _execsum_sig_jobs[job_id]["done"] = True

        threading.Thread(target=_worker, daemon=True).start()

        # Immediate UI change: mark busy + enable poll interval
        return job_id, False, {"name": name}, ""

   
    
    # ----------------------------
    # Poll signature job
    # ----------------------------
    @app.callback(
        Output("execsum-es-existing", "data", allow_duplicate=True),
        Output("execsum-generate-status", "children", allow_duplicate=True),
        Output("execsum-pid-table", "data", allow_duplicate=True),
        Output("execsum-sig-job", "data", allow_duplicate=True),
        Output("execsum-sig-interval", "disabled", allow_duplicate=True),
        Output("execsum-sig-busy", "data", allow_duplicate=True),
        Input("execsum-sig-interval", "n_intervals"),
        State("execsum-sig-job", "data"),
        prevent_initial_call=True,
    )
    def poll_signature_job(_n, job_id):
        if not job_id or job_id not in _execsum_sig_jobs:
            raise PreventUpdate

        job = _execsum_sig_jobs[job_id]
        if not job.get("done"):
            raise PreventUpdate

        err = job.get("error")
        if err:
            _execsum_sig_jobs.pop(job_id, None)
            # clear busy so button returns to normal blue
            return no_update, f"Upload failed: {err}", no_update, None, True, None

        new_es = job.get("new_es") or []
        msg = job.get("msg") or "Done."
        new_table = job.get("new_table")

        _execsum_sig_jobs.pop(job_id, None)

        # clear busy so button returns to normal blue
        return new_es, msg, (new_table if new_table is not None else no_update), None, True, None


    if ENABLE_SCANNER:
        _register_scanner_callbacks(app)


# ============================================================
# Callbacks for scanner
# ============================================================
def _register_scanner_callbacks(app):
    # ---- put ONLY scanner-related callbacks here ----

    # ----------------------------
    # Toggle the color of the camera button
    # ----------------------------
    @app.callback(
        Output("execsum-scan-open", "style"),
        Input("execsum-scan-token", "data"),
        Input("execsum-scan-poll", "disabled"),
    )
    def style_scan_button(token, poll_disabled):
        tok = (token or "").strip()
        scan_active = bool(tok) and (poll_disabled is False)
        colors = SCAN_BTN_ACTIVE if scan_active else SCAN_BTN_LIGHT
        return dict(SCAN_BTN_BASE, **colors)


    # ----------------------------
    # Scanner
    # ----------------------------
    @app.callback(
        Output("execsum-scan-modal", "is_open"),
        Output("execsum-scan-token", "data"),
        Output("execsum-scan-url", "data"),
        Output("execsum-scan-poll", "disabled"),
        Output("execsum-scan-status", "children"),
        Output("execsum-scan-link", "children"),
        Output("execsum-scan-qr-img", "src"),
        Output("execsum-scan-qr-img", "style"),
        Output("execsum-scan-open-url", "data"),
        Input("execsum-scan-open", "n_clicks"),
        Input("execsum-scan-close", "n_clicks"),
        State("execsum-scan-modal", "is_open"),
        State("execsum-scan-token", "data"),
        State("execsum-scan-url", "data"),
        State("execsum-scan-poll", "disabled"),
        prevent_initial_call=True,
    )
    def open_close_scan_modal(n_open, n_close, is_open, token_now, url_now, poll_disabled):
        
        trig = ctx.triggered_id

        # Close button => cancel scan session too
        if trig == "execsum-scan-close":
            _scanner_best_effort_cancel(token_now)
            return False, None, None, True, "Canceled.", "", "", {"display": "none"}, None

        if trig != "execsum-scan-open":
            raise PreventUpdate

        # TOGGLE-OFF condition for LAN mode:
        # If we currently have an active scan (token exists AND polling is running),
        # clicking the camera icon again should cancel.
        token_now_s = (token_now or "").strip()
        scan_active = bool(token_now_s) and (poll_disabled is False)

        if scan_active:
            _scanner_best_effort_cancel(token_now_s)
            return False, None, None, True, "Canceled.", "", "", {"display": "none"}, None


        # If modal is already open, treat this as a TOGGLE-OFF cancel
        if is_open:
            _scanner_best_effort_cancel(token_now)
            return False, None, None, True, "Canceled.", "", "", {"display": "none"}, None
        
        # Determine how the *client* is accessing Dash (this is the key)
        dash_scheme = _dash_request_scheme()  # 'https' in LAN mode
        dash_host = _dash_request_host()      # e.g. 192.168.x.x when phone is on LAN
        lan_mode = _is_lan_mode_request()

        # Basic scanner diagnostics (still useful)
        diag = scanner_srv.get_server_diagnostics()
        start_err = (diag or {}).get("start_error")
        if start_err:
            # server thread failed to start at all -> show the real reason
            wsl_ok, wsl_card_children, _wsl_phone_urls = _render_wsl2_portproxy_card(
                (diag or {}).get("wsl2_portproxy") or {},
                port=SCANNER_PORT,
            )

            msg = "Scanner server failed to start on this machine."
            msg += f"\n\nStart error:\n{start_err}"

            status_children = [html.Pre(msg, style={"whiteSpace": "pre-wrap", "color": "#a33"})]
            if wsl_ok:
                status_children += wsl_card_children

            return (True, None, None, True, status_children, "", "", {"display": "none"}, None)

        # Preflight: is scanner server reachable locally?
        ok, base, hj = _scanner_healthcheck()
        if not ok:
            msg = "Scanner server is not running on this machine."
            detail = ""
            if isinstance(hj, dict):
                detail = hj.get("error") or hj.get("start_error") or ""
            if detail:
                msg += f"\n\nDetails:\n{detail}"

            diag = scanner_srv.get_server_diagnostics()
            if (diag or {}).get("start_error"):
                msg += f"\n\nStart error:\n{diag.get('start_error')}"

            link_children = html.Div(
                [
                    html.Div("Try these local checks in the terminal:", style={"fontWeight": "800", "marginTop": "6px"}),
                    html.Pre(
                        "\n".join([
                            f"curl -vk https://127.0.0.1:{SCANNER_PORT}/health",
                            f"curl -v  http://127.0.0.1:{SCANNER_PORT}/health",
                            "",
                            "# If both fail, the scanner server did not bind.",
                            "# See start_error above for details.",
                        ]),
                        style={
                            "whiteSpace": "pre-wrap",
                            "fontFamily": "Menlo, Monaco, Consolas, monospace",
                            "fontSize": "12px",
                            "padding": "8px 10px",
                            "borderRadius": "10px",
                            "border": "1px solid #E0E6EF",
                            "backgroundColor": "#F6F8FB",
                        },
                    ),
                ]
            )
            return (True, None, None, True, html.Pre(msg, style={"whiteSpace": "pre-wrap", "color": "#a33"}), link_children, "", _QR_STYLE_HIDDEN, None)

        # Create a scan session token (the scan/<token> page uses this directly)
        sess = new_scan_session(mode="component_type", ttl_s=120.0)

        # -----------------------------
        # LAN mode: persistent /phone page (recommended)
        #   - Arm active job on local scanner server
        #   - Open /phone on the phone (same host as Dash)
        #   - Keep polling for result from token (same as before)
        # -----------------------------
        if lan_mode:
            # 1) Arm active job on the local scanner server (loopback only)
            # Use local bases so this works regardless of what host the phone uses.
            armed_ok = False
            last_err = None
            for base2 in _scanner_local_bases():
                try:
                    r = _SCANNER_HTTP.post(
                        f"{base2}/api/active",
                        json={
                            "token": sess.token,
                            "mode": "component_type",
                            "ttl_s": 120.0,
                            "label": "Executive Summary: TypeID",
                        },
                        timeout=(2.5, 5.0),
                        verify=False,
                    )
                    if r.ok:
                        armed_ok = True
                        break
                    else:
                        snippet = (r.text or "").strip().replace("\\n", " ")
                        if len(snippet) > 200:
                            snippet = snippet[:200] + "…"
                        last_err = f"{r.status_code} {snippet}"
                except Exception as e:
                    last_err = str(e)

            if not armed_ok:
                msg = f"Failed to arm scanner job (LAN mode): {last_err or 'unknown'}"
                # fall back to showing the modal with error
                return (
                    True, # modal OPEN so user sees error
                    None,
                    None,
                    True,
                    html.Pre(msg, style={"whiteSpace": "pre-wrap", "color": "#a33"}),
                    "",
                    "",
                    _QR_STYLE_HIDDEN,
                    None,
                )

            # 2) Build the phone URL using the same host the phone is already using for Dash
            host_for_phone = dash_host or "127.0.0.1"
            phone_url = f"{dash_scheme}://{host_for_phone}:{SCANNER_PORT}/phone"

            # 3) Auto-open /phone in a re-used tab, keep modal closed
            return (
                False,           # modal CLOSED (skip this step in LAN mode)
                sess.token,      # token for polling result
                phone_url,       # store "scan url" (now /phone)
                False,           # enable polling
                "",              # status (unused because modal closed)
                "",              # link   (unused)
                "",              # no QR
                _QR_STYLE_HIDDEN,
                phone_url,       # <-- triggers clientside window.open(reuse tab)
            )






        # -----------------------------
        # Non-LAN mode: keep your existing /phone + QR flow
        # -----------------------------
        # Use scheme based on which /health URL worked
        scheme = "https"
        try:
            if isinstance(base, str) and base.strip().lower().startswith("http://"):
                scheme = "http"
        except Exception:
            scheme = "https"

        # Arm the active job for /phone UX (existing behavior)
        try:
            r = _SCANNER_HTTP.post(
                f"{base}/api/active",
                json={
                    "token": sess.token,
                    "mode": "component_type",
                    "ttl_s": 120.0,
                    "label": "Executive Summary: TypeID",
                },
                timeout=(2.5, 5.0),
                verify=False,
            )
            if not r.ok:
                snippet = (r.text or "").strip().replace("\n", " ")
                if len(snippet) > 200:
                    snippet = snippet[:200] + "…"
                raise RuntimeError(f"{r.status_code} {snippet}")
        except Exception as e:
            msg = f"Failed to arm scanner job on this machine: {e}"
            msg += " (Check scanner server logs or /health for start_error.)"
            return (True, None, None, True, msg, "", "", _QR_STYLE_HIDDEN)

        # WSL2 portproxy help (if available)
        wsl_ok, wsl_card_children, wsl_phone_urls = _render_wsl2_portproxy_card(hj or {}, port=SCANNER_PORT)

        # Build /phone URLs
        phone_urls: list[str] = []
        if wsl_ok and wsl_phone_urls:
            phone_urls = [str(u) for u in wsl_phone_urls if isinstance(u, str) and u.strip()]
            extra = []
            for u in phone_urls:
                uu = u.strip()
                if uu.lower().startswith("https://"):
                    extra.append("http://" + uu[len("https://"):])
            phone_urls += extra
        else:
            hosts = lan_host_candidates() or []
            phone_urls = [_phone_home_url(host=h, port=SCANNER_PORT, scheme=scheme) for h in hosts if h]
            other = "http" if scheme == "https" else "https"
            phone_urls += [_phone_home_url(host=h, port=SCANNER_PORT, scheme=other) for h in hosts if h]

        seen = set()
        phone_urls = [u for u in phone_urls if u and not (u in seen or seen.add(u))]

        #phone_primary = phone_urls[0] if phone_urls else _phone_home_url(host="127.0.0.1", port=SCANNER_PORT, scheme=scheme)
        phone_primary = _pick_phone_primary(phone_urls) or (
            _phone_home_url(host="127.0.0.1", port=SCANNER_PORT, scheme=scheme)
        )

        logger.info(f"[ExecSum Scanner] non-LAN phone_urls={phone_urls[:8]}")
        logger.info(f"[ExecSum Scanner] non-LAN phone_primary={phone_primary}")
        
        qr_src = _make_qr_data_uri(phone_primary)

        img_style = dict(_QR_STYLE_VISIBLE_BASE, **{
            "display": "block" if qr_src else "none",
        })

        status_children = [
            html.Div(
                "Open /phone on your phone. If the QR does not load, try the next URL(s) below (IPs usually work best).",
                style={"whiteSpace": "pre-wrap"},
            )
        ]
        if wsl_ok:
            status_children += wsl_card_children
        if not qr_src:
            status_children.insert(0, html.Div("QR generation unavailable in this build; use the URL list below.", style={"color":"#a66","fontWeight":"800"}))

        link_children = html.Div(
            [
                html.Div("Scanner URLs:", style={"fontWeight": "800", "marginTop": "6px"}),
                html.Pre(
                    "\n".join(phone_urls[:8]) if phone_urls else phone_primary,
                    style={
                        "whiteSpace": "pre-wrap",
                        "fontFamily": "Menlo, Monaco, Consolas, monospace",
                        "fontSize": "12px",
                        "padding": "8px 10px",
                        "borderRadius": "10px",
                        "border": "1px solid #E0E6EF",
                        "backgroundColor": "#F6F8FB",
                    },
                ),
            ]
        )

        return (
            True,
            sess.token,
            phone_primary,
            False,          # enable polling
            status_children,
            link_children,
            qr_src or "",
            img_style if qr_src else _QR_STYLE_HIDDEN,
            None,   # no auto-open in non-LAN (we can enable it later if we want...)
        )




    @app.callback(
        Output("execsum-typeid", "value", allow_duplicate=True),
        Output("execsum-scan-status", "children", allow_duplicate=True),
        Output("execsum-scan-modal", "is_open", allow_duplicate=True),
        Output("execsum-scan-poll", "disabled", allow_duplicate=True),
        Input("execsum-scan-poll", "n_intervals"),
        State("execsum-scan-token", "data"),
        prevent_initial_call=True,
    )
    def poll_for_scan(_n, token):
        if not token:
            raise PreventUpdate

        # Ask scanner server (local) whether token has a result
        try:
            #r = requests.get(f"{SCANNER_LOCAL_API}/api/scan/{token}", timeout=(2, 3), verify=False)
            #j = r.json() if r.ok else {}
            # Ask scanner server (local) whether token has a result
            last_err = None
            j = None
            for base in _scanner_local_bases():
                try:
                    r = _SCANNER_HTTP.get(f"{base}/api/scan/{token}", timeout=(2.5, 5.0), verify=False)
                    if r.ok:
                        j = r.json() if r.content else {}
                        break
                except Exception as e:
                    last_err = e
                    continue

            if j is None:
                return no_update, f"Scanner server not reachable: {last_err}", no_update, True
        except Exception as e:
            return no_update, f"Scanner server not reachable: {e}", no_update, True

        if not j.get("ok"):
            # expired or invalid
            return no_update, "Scan token expired. Click 📷 again.", True, True

        if not j.get("used"):
            raise PreventUpdate

        extracted = (j.get("extracted") or "").strip()
        if not extracted:
            return no_update, "Scanned, but PID could not be parsed. Try again.", True, False
            #return no_update, "Scanned, but PID could not be parsed. Try again.", no_update, False

        # Success: fill typeid field, close modal, stop polling
        return extracted, f"Received: {extracted}", False, True




    clientside_callback(
        """
        function(url){
        if (!url) return "";
        // Reuse the same tab/window every time:
        window.open(url, "hwdb_scanner_phone");
        return "";
        }
        """,
        Output("execsum-scan-open-url-sink", "children"),
        Input("execsum-scan-open-url", "data"),
        prevent_initial_call=True,
    )
