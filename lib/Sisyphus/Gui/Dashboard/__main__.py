from Sisyphus.Gui.Dashboard.utils import silence_warnings

import threading, webbrowser
from threading import Timer
from dash import Dash, html
import dash_bootstrap_components as dbc
from pathlib import Path

import time, requests
from Sisyphus.RestApiV1 import whoami

import os, sys, io, contextlib
import logging
os.environ["FLASK_RUN_FROM_CLI"] = "false"
logging.getLogger("werkzeug").disabled = True


from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Gui.Dashboard.layout.layout_main import layout, register_layout_callbacks
from Sisyphus.Gui.Dashboard.shippingworkflow import register_shipping_workflow_routes
from Sisyphus.Gui.Dashboard.callbacks.callbacks_preferences import register_preferences_callbacks
from Sisyphus.Gui.Dashboard.callbacks.callbacks_jsonselect import register_jsonselect_callbacks
from Sisyphus.Gui.Dashboard.callbacks.callbacks_typegetter import register_typegetter_callbacks
from Sisyphus.Gui.Dashboard.callbacks.callbacks_downloader import register_downloader_callbacks
from Sisyphus.Gui.Dashboard.callbacks.callbacks_executive_summary import register_executive_summary_callbacks

from Sisyphus.Gui.Dashboard.callbacks import (
    register_conditions_callbacks,
    register_filter_callbacks,
    register_valuefilter_callbacks,
    register_hidecharts_callbacks,
    register_load_callbacks,
    register_plot_callbacks,
    register_sync_callbacks,
    register_updatemenu_callbacks,
    register_shipment_callbacks,
    register_overlay_callbacks,
)

# For scanner
from Sisyphus.Gui.Dashboard.utils.scanner_server import ScannerServerThread
from Sisyphus.Gui.Dashboard.utils.scanner_certs import ensure_scanner_cert
_sc = requests.Session()
_sc.trust_env = False

# For the LAN mode
import argparse, secrets
from Sisyphus.Gui.Dashboard.utils.dashboard_certs import ensure_dashboard_cert

parser = argparse.ArgumentParser(prog="hwdb-dash")
parser.add_argument("--lan", action="store_true", help="Serve dashboard on LAN (HTTPS + pairing).")
parser.add_argument("--port", type=int, default=8050)
args, _unknown = parser.parse_known_args()

LAN_MODE = bool(args.lan)
logger.info(f"[LAN] LAN_MODE={LAN_MODE} argv={sys.argv!r}")
port = int(args.port)

host = "0.0.0.0" if LAN_MODE else "127.0.0.1"

LAN_SECRET = ""
if LAN_MODE:
    # rotate per-launch (recommended)
    LAN_SECRET = secrets.token_urlsafe(24)


def get_path(rel: str) -> str:
    """
    Resolve a path relative to the runtime root.

    Frozen (PyInstaller onedir):
      <dist>/HWDBTools/_internal/<rel>

    Non-frozen (repo checkout):
      <repo_root>/<rel>
    """
    rel = rel.lstrip("/").replace("\\", "/")

    if getattr(sys, "frozen", False):
        # In onedir, the EXE lives in <dist>/HWDBTools/
        # and _internal is a sibling folder.
        runtime_root = Path(sys.executable).resolve().parent / "_internal"
        return str(runtime_root / rel)

    # Non-frozen: infer repo root from this file location:
    # lib/Sisyphus/Gui/Dashboard/__main__.py -> repo root is 5 parents up
    # (__main__.py -> Dashboard -> Gui -> Sisyphus -> lib -> PROJECT_ROOT)
    runtime_root = Path(__file__).resolve().parents[4]
    return str(runtime_root / rel)

#------------- create the website and interface -------
dash_kwargs = dict(
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

if getattr(sys, "frozen", False):
    # Frozen: our spec places Dashboard assets into _internal/assets/
    dash_kwargs.update(
        assets_folder=get_path("assets"),
        assets_url_path="/assets",   # optional; Dash default is already "/assets"
    )

#app = Dash(__name__, **dash_kwargs)
app = Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    **dash_kwargs,
)

#------------- a /pair route, which allows QR+URLs -------------
from flask import request, Response, jsonify
from Sisyphus.Gui.Dashboard.utils.netutil import lan_host_candidates
from Sisyphus.Gui.Dashboard.utils.scanner import is_private_or_local_ip

def _make_qr_png_data_uri(text: str) -> str:
    import base64, io
    import qrcode
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    b64 = base64.b64encode(bio.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"

def _pairing_urls(port: int, secret: str) -> list[str]:
    # Prefer IPs first (phones are best with raw IP)
    hosts = lan_host_candidates() or []
    urls = []
    for h in hosts:
        h = (h or "").strip()
        if not h:
            continue
        urls.append(f"https://{h}:{port}/?k={secret}")
    # de-dupe preserve order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

@app.server.get("/pair")
def pair_page():
    # Only allow pairing page from local machine (prevents LAN users from discovering secret!)
    ra = request.remote_addr or ""
    if not (ra.startswith("127.") or ra == "::1"):
        return Response("Forbidden", status=403)

    if not LAN_MODE:
        return Response("Not in LAN mode.", status=404)

    urls = _pairing_urls(port=port, secret=LAN_SECRET)
    primary = urls[0] if urls else ""
    qr = _make_qr_png_data_uri(primary) if primary else ""

    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>HWDB Dashboard — Pair device</title>
  <style>
    body {{ font-family: -apple-system, system-ui, sans-serif; padding: 16px; }}
    .box {{ max-width: 720px; margin: 0 auto; padding: 14px; border: 1px solid #ddd; border-radius: 14px; }}
    code, pre {{ font-family: Menlo, Monaco, Consolas, monospace; }}
    img {{ width: 260px; height: 260px; border-radius: 12px; border: 1px solid #e0e6ef; background: #fff; }}
  </style>
</head>
<body>
  <div class="box">
    <h2 style="margin-top:0;">Pair your phone to HWDB Dashboard</h2>
    <ol>
      <li>Scan this QR code with your phone camera.</li>
      <li>If your browser warns about a certificate, accept it (self-signed LAN cert).</li>
    </ol>
    <div style="text-align:center; margin: 10px 0;">
      {"<img src='" + qr + "'/>" if qr else "<b>QR generation unavailable in this build.</b>"}
    </div>
    <h3>URLs (try in this order)</h3>
    <pre style="white-space:pre-wrap;">{chr(10).join(urls[:10])}</pre>
    <p style="color:#666;">This page is only accessible from the laptop. The secret key is embedded in the URL and will be remembered via a cookie once you connect.</p>
  </div>
</body>
</html>
"""
    return Response(html, mimetype="text/html")

@app.server.get("/unpair")
def unpair():
    # Only allow from the local machine (same restriction style as /pair)
    ra = request.remote_addr or ""
    if not (ra.startswith("127.") or ra == "::1"):
        return Response("Forbidden", status=403)

    resp = Response("Unpaired. Close this tab and revisit /pair.", mimetype="text/plain")
    # Clear cookie
    resp.set_cookie("HWDB_LAN_OK", "", expires=0)
    return resp

@app.server.get("/health")
def dashboard_health():
    """
    Local troubleshooting page for LAN / Windows / WSL users.

    This is intentionally restricted to the local machine, because it may show
    local networking diagnostics and helper commands.
    """
    ra = request.remote_addr or ""
    if not (ra.startswith("127.") or ra == "::1"):
        return Response("Forbidden", status=403)

    scanner_diag = {}
    try:
        from Sisyphus.Gui.Dashboard.utils import scanner_server as scanner_srv
        scanner_diag = scanner_srv.get_server_diagnostics()
    except Exception as e:
        scanner_diag = {"error": repr(e)}

    return jsonify({
        "ok": True,
        "lan_mode": LAN_MODE,
        "dashboard": {
            "bind_host": host,
            "port": port,
            "pairing_url": f"https://127.0.0.1:{port}/pair" if LAN_MODE else None,
            "health_url": f"https://127.0.0.1:{port}/health" if LAN_MODE else None,
        },
        "scanner": scanner_diag,
        "windows_wsl_note": [
            "If your phone cannot connect to the Dashboard in LAN mode, first open this page on the computer running hwdb-dash.",
            "For WSL2, check scanner.wsl2_mirrored and scanner.wsl2_portproxy below.",
            "Mirrored networking is usually preferred on newer Windows/WSL.",
            "If mirrored networking is unavailable, use the portproxy commands.",
            "Also check Windows Firewall for Dashboard port 8050 and Scanner port 8766.",
        ],
    })


#------------- Gate the HWDB Dashboard with "LAN + secret cookie" -------------
from flask import g, abort

@app.server.before_request
def _lan_gate():
    ra = request.remote_addr or ""

    if not LAN_MODE:
        # local-only mode: block non-loopback
        if not (ra.startswith("127.") or ra == "::1"):
            abort(403)
        return

    # LAN mode: only private/local IPs
    if not is_private_or_local_ip(ra):
        abort(403)

    # Allow pairing page (pair_page itself restricts to loopback)
    #if request.path == "/pair":
    #if request.path in ("/pair", "/unpair"):
    if request.path in ("/pair", "/unpair", "/health"):
        return

    # Always allow Dash assets + internal endpoints without secret
    p = request.path or ""
    if p.startswith("/assets/") or p.startswith("/_dash-") or p == "/favicon.ico":
        return

    # Cookie already paired?
    if request.cookies.get("HWDB_LAN_OK") == "1":
        return

    # First-time pairing: require correct key on ANY “real page” request
    k = (request.args.get("k") or "").strip()
    if k != LAN_SECRET:
        abort(401)

    g._hwdb_set_lan_cookie = True

@app.server.after_request
def _lan_gate_after(resp):
    try:
        if LAN_MODE and getattr(g, "_hwdb_set_lan_cookie", False):
            resp.set_cookie(
                "HWDB_LAN_OK",
                "1",
                httponly=True,
                samesite="Lax",
                secure=True,      # LAN mode is HTTPS
                max_age=8*3600,   # e.g. 8 hours
            )
    except Exception:
        pass
    return resp
#--------------------------------------------------------------


#------------- create the website and interface -------
#app = Dash(
#    __name__,
#    external_stylesheets=[dbc.themes.BOOTSTRAP],
#    suppress_callback_exceptions=True,
#    assets_folder=get_path("assets"),
#    assets_url_path="/assets",
#    )

app.title = "HWDB Dashboard"
register_shipping_workflow_routes(app, lan_mode=LAN_MODE)
app.layout = layout
# Force Dash to validate the layout before callback registration
#app.validation_layout = layout

#app.config.suppress_callback_exceptions = True


# Now register layout-switching callback
register_layout_callbacks(app)

# Register all callback modules
register_executive_summary_callbacks(app)
register_downloader_callbacks(app)
register_typegetter_callbacks(app)
register_preferences_callbacks(app)
register_conditions_callbacks(app)
register_filter_callbacks(app)
register_valuefilter_callbacks(app)
register_hidecharts_callbacks(app)
register_load_callbacks(app)
register_plot_callbacks(app)
register_sync_callbacks(app)
register_updatemenu_callbacks(app)
register_jsonselect_callbacks(app)
register_shipment_callbacks(app)
register_overlay_callbacks(app)

logger.info("Dashboard is starting up...")

#---------------
# browser...
import subprocess, shutil

def is_wsl() -> bool:
    if os.environ.get("WSL_INTEROP") or os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        with open("/proc/version", "r") as fp:
            return "microsoft" in fp.read().lower()
    except Exception:
        return False

def open_url(url: str) -> None:
    """
    Open URL in a browser.
    - WSL: use Windows openers (wslview / explorer.exe / cmd.exe start)
    - macOS: open
    - Linux: try xdg-open (best-effort)
    - fallback: Python webbrowser
    """
    try:
        if is_wsl():
            if shutil.which("wslview"):
                subprocess.Popen(["wslview", url])
                return
            if shutil.which("explorer.exe"):
                subprocess.Popen(["explorer.exe", url])
                return
            if shutil.which("cmd.exe"):
                subprocess.Popen(["cmd.exe", "/c", "start", "", url])
                return

        if sys.platform == "darwin":
            subprocess.Popen(["open", url])
            return

        if sys.platform.startswith("linux"):
            if (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) and shutil.which("xdg-open"):
                subprocess.Popen(["xdg-open", url])
                return
        #if sys.platform.startswith("linux") and shutil.which("xdg-open"):
        #    subprocess.Popen(["xdg-open", url])
        #    return

    except Exception as e:
        logger.warning(f"Browser auto-open failed: {e!r}")

    # final fallback (may be gio/xdg-open under the hood)
    import webbrowser
    webbrowser.open_new(url)


#------------ Probe the Dashboard based URL before opening/pair ------------
_DASH_PROBE = requests.Session()
_DASH_PROBE.trust_env = False

def _probe_dashboard_local(port: int, tries: int = 40, sleep_s: float = 0.15):
    """
    Try https then http on loopback until /pair responds.
    Returns (ok: bool, base_url: str, detail: str)
    """
    bases = [
        f"https://127.0.0.1:{port}",
        f"http://127.0.0.1:{port}",
        f"https://localhost:{port}",
        f"http://localhost:{port}",
    ]
    last = None
    for _ in range(tries):
        for base in bases:
            try:
                r = _DASH_PROBE.get(f"{base}/pair", timeout=(0.6, 0.8), verify=False, allow_redirects=False)
                if r.status_code in (200, 401, 403):  # 200 ok, 401 if gate misfires, 403 if loopback check fails
                    return True, base, f"HTTP {r.status_code}"
                last = f"{base}/pair -> HTTP {r.status_code}"
            except Exception as e:
                last = f"{base}/pair -> {type(e).__name__}: {e}"
        time.sleep(sleep_s)
    return False, "", (last or "unknown error")
def _probe_scanner_local(port: int, tries: int = 30, sleep_s: float = 0.15):
    """
    Try both https and http on loopback to confirm scanner is reachable.
    Returns (ok: bool, base_url: str, detail: str)
    """
    bases = [
        f"https://127.0.0.1:{port}",
        f"http://127.0.0.1:{port}",
        f"https://localhost:{port}",
        f"http://localhost:{port}",
    ]
    last = None
    for _ in range(tries):
        for base in bases:
            try:
                r = _sc.get(f"{base}/health", timeout=(0.6, 0.8), verify=False)
                if r.ok:
                    return True, base, ""
                last = f"{base} -> HTTP {r.status_code}"
            except Exception as e:
                last = f"{base} -> {type(e).__name__}: {e}"
        time.sleep(sleep_s)
    return False, "", (last or "unknown error")

    
def kickoff_auth_refresh(delay_s: float = 0.75) -> None:
    """
    Force an early REST call so expired tokens trigger refresh immediately.
    Runs in a background thread so it doesn't block Dash startup.
    """
    def _worker():
        try:
            time.sleep(delay_s)
            # This should trigger refresh if needed, and your RestApiSession.py
            # will print/open the device URL.
            whoami()
        except Exception as e:
            # Don't crash the app; just log.
            logger.warning(f"Startup auth kickoff failed: {e!r}")
    threading.Thread(target=_worker, daemon=True).start()

#---------------


# Run the app
#host = "127.0.0.1"
#host = "0.0.0.0"
#port = 8050

def open_browser():
    #webbrowser.open_new(f"http://{host}:{port}")
    #open_url(f"http://{host}:{port}")
    scheme = "https" if LAN_MODE else "http"
    host_for_open = "127.0.0.1"  # always open loopback locally
    open_url(f"{scheme}://{host_for_open}:{port}")

#---
import sys
import re
import contextlib

class FilteredTee(io.TextIOBase):
    """
    Swallows most prints, but passes through lines that match allow_patterns.
    Also forwards everything to an optional logger (at debug level), if desired.
    """
    def __init__(self, real_stream, *, allow_patterns=None, logger=None, log_level="debug"):
        self._real = real_stream
        self._buf = ""
        self._allow = [re.compile(p) for p in (allow_patterns or [])]
        self._logger = logger
        self._log_level = log_level

    def write(self, s: str):
        if not isinstance(s, str):
            s = str(s)

        self._buf += s
        # process full lines
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self._handle_line(line + "\n")
        return len(s)

    def flush(self):
        # flush any partial line (rare)
        if self._buf:
            self._handle_line(self._buf)
            self._buf = ""
        try:
            self._real.flush()
        except Exception:
            pass

    def _handle_line(self, line: str):
        text = line.rstrip("\n")

        # optional: log everything quietly
        if self._logger:
            try:
                getattr(self._logger, self._log_level)(text)
            except Exception:
                pass

        # pass through only allowed lines
        for pat in self._allow:
            if pat.search(text):
                try:
                    self._real.write(line)
                    self._real.flush()
                except Exception:
                    pass
                break


def quiet_startup_context():
    """
    Only let through very specific lines that users should see.
    Tune allow_patterns to your taste.
    """
    allow_patterns = [
        r"Dash is running on https?://.*:\d+/?",
        r"\[htgettoken\] authentication URL:",
        r"Authentication URL \(copy/paste in a browser\):",
        r"Authentication is still pending",
        r"Not authorized",
        r"Startup auth kickoff failed",
        r"\[LAN\] Pairing page",
        r"\[LAN\] Troubleshooting page",
        r"\[LAN\] If browser doesn’t open",
        r"\[LAN\] If you’re on Windows/WSL",
    ]

    stdout_filter = FilteredTee(sys.__stdout__, allow_patterns=allow_patterns, logger=logger, log_level="debug")
    stderr_filter = FilteredTee(sys.__stderr__, allow_patterns=allow_patterns, logger=logger, log_level="debug")

    return contextlib.redirect_stdout(stdout_filter), contextlib.redirect_stderr(stderr_filter)
#---
    
if __name__ == "__main__":

    # Start the scanner server (LAN) for phones
    SCANNER_HOST = "0.0.0.0"
    SCANNER_PORT = 8766

    # point these at real files on disk
    #CERT_FILE = get_path("scanner_certs/cert.pem")
    #KEY_FILE  = get_path("scanner_certs/key.pem")
    #CERT_FILE = get_path("scanner_certs/192.168.1.109+2.pem")
    #KEY_FILE  = get_path("scanner_certs/192.168.1.109+2-key.pem")
    paths = ensure_scanner_cert()
    CERT_FILE = str(paths.cert_pem)
    KEY_FILE  = str(paths.key_pem)

    #print("[Scanner] CERT:\n" + subprocess.check_output(["openssl","x509","-in",CERT_FILE,"-noout","-enddate","-ext","subjectAltName"], text=True).strip())

    if not Path(CERT_FILE).exists():
        logger.error(f"[Scanner] CERT file not found: {CERT_FILE}")
    if not Path(KEY_FILE).exists():
        logger.error(f"[Scanner] KEY file not found: {KEY_FILE}")
    
    scanner_thread = ScannerServerThread(
        SCANNER_HOST,
        SCANNER_PORT,
        ssl_context=(CERT_FILE, KEY_FILE),
        lan_mode=LAN_MODE,
    )
    scanner_thread.start()

    # Wait until the server thread either binds or records a start_error
    scanner_thread.wait_ready(timeout=3.0)

    ok, base, detail = _probe_scanner_local(SCANNER_PORT)
    if not ok:
        # Pull real startup diagnostics from scanner_server.py
        from Sisyphus.Gui.Dashboard.utils import scanner_server as scanner_srv
        diag = scanner_srv.get_server_diagnostics()
        logger.error(
            "[Scanner] NOT reachable on loopback. probe_last=%s\n[Scanner] diagnostics=%r",
            detail,
            diag,
        )
    else:
        logger.info(f"[Scanner] reachable at {base}/health")

    logger.info(f"[Scanner] Phone scanner server bind: https://{SCANNER_HOST}:{SCANNER_PORT} (or http fallback)")

    
    out_ctx, err_ctx = quiet_startup_context()
    with out_ctx, err_ctx:
    #with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):

        if LAN_MODE:
            print(f"[LAN] Pairing page (manual): https://127.0.0.1:{port}/pair")
            print(f"[LAN] Troubleshooting page:  https://127.0.0.1:{port}/health")
            print("[LAN] If browser doesn’t open: paste the /pair URL above into your browser on this computer.")
            print("[LAN] If you’re on Windows/WSL and phone can’t connect, open /health and follow mirrored/portproxy instructions.")
            
        def open_pair_when_ready():
            ok, base, detail = _probe_dashboard_local(port)
            if ok and base:
                open_url(f"{base}/pair")
            else:
                logger.warning(f"[LAN] Could not probe /pair on loopback: {detail}")

        # Launch browser after short delay so server starts first
        if LAN_MODE:
            threading.Timer(0.5, open_pair_when_ready).start()
        else:
            threading.Timer(2.0, open_browser).start()
        
        # Force early token refresh if needed
        kickoff_auth_refresh(delay_s=0.75)

        ssl_ctx = None
        
        # Auto-open for the LAN mode
        if LAN_MODE:
            paths = ensure_dashboard_cert()
            ssl_ctx = (str(paths.cert_pem), str(paths.key_pem))

        app.run(host=host, port=port, debug=False, use_reloader=False, ssl_context=ssl_ctx)
        
        #app.run(debug=False, use_reloader=False)
        #app.run(host=host, port=port, debug=False, use_reloader=False)

