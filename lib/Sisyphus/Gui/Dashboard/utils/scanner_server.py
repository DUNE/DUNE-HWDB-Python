from __future__ import annotations

import threading
from flask import Flask, request, jsonify, Response
from werkzeug.serving import make_server
from pathlib import Path
import time
import traceback

from .scanner import (
    get_scan_status,
    set_scan_result,
    cleanup_sessions,
    is_private_or_local_ip,
    get_active_job_status,
    set_active_job,
    claim_active_job,
    release_active_job,
    clear_active_job,
    cancel_scan_session, 
)

from .scanner_certs import ensure_scanner_cert

import os
import re
import subprocess
import sys
import socket


# --- server startup diagnostics ---
_SERVER_STARTED_TS: float | None = None
_SERVER_START_ERROR: str | None = None
_SERVER_BIND_HOST: str | None = None
_SERVER_BIND_PORT: int | None = None

SCAN_HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>HWDB Dashboard Scanner</title>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; padding: 12px; }
    #reader { width: 100%; max-width: 520px; margin: 0 auto; }
    .box { max-width: 520px; margin: 12px auto; padding: 10px; border: 1px solid #ddd; border-radius: 12px; }
    .ok { color: #0a7; font-weight: 800; }
    .bad { color: #a33; font-weight: 800; }
    code { word-break: break-word; }
    button { padding:10px 14px; border-radius:10px; border:1px solid #ccc; font-weight:800; }
    .row { display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; align-items:center; }
    .muted { color:#666; font-size:13px; }
  </style>
  <script src="/static/html5-qrcode.min.js"></script>
</head>
<body>
  <div style="text-align:center; margin-bottom:10px;">
    <img
      src="/static/IconBig.png"
      alt="HWDB Dashboard"
      style="width:84px; height:84px; object-fit:contain; border-radius:18px;"
    />
  </div>
  <div class="box">
    <div><b>HWDB Dashboard scanner</b></div>
    <div class="muted">Point your camera at a QR code or barcode.</div>
    <div style="margin-top:6px; font-size: 13px; color:#555">
      Token: <code id="tok"></code><br/>
      Mode: <code id="mode"></code>
    </div>
  </div>

  <div id="reader"></div>

  <div class="box" id="statusBox">
    <div id="status" style="color:#555">Tap Start camera.</div>

    <div class="row">
      <button id="startBtn">Start camera</button>
      <button id="stopBtn">Stop camera</button>
      <button id="refocusBtn">Refocus</button>
    </div>

    <div id="zoomWrap" style="margin-top:10px; display:none;">
      <div style="font-weight:800; margin-bottom:6px;">Zoom</div>
      <input id="zoomSlider" type="range" min="1" max="1" step="0.1" value="1" style="width:100%;">
    </div>

    <pre id="dbg" style="white-space:pre-wrap; font-size:12px; color:#444; margin-top:10px;"></pre>
  </div>

<script>
(function(){
  const token = "{{TOKEN}}";
  const mode  = "{{MODE}}";

  document.getElementById("tok").textContent = token;
  document.getElementById("mode").textContent = mode;

  const statusEl = document.getElementById("status");
  const dbg = document.getElementById("dbg");

  // debug=1 enables logs; default off
  const DEBUG = new URLSearchParams(window.location.search).get("debug") === "1";
  if (!DEBUG) dbg.style.display = "none";
  function log(x){ if (DEBUG) dbg.textContent += x + "\n"; }

  function setStatus(msg, cls){
    statusEl.className = cls || "";
    statusEl.textContent = msg;
  }

  let html5 = null;
  let cameraStarted = false;
  let manualStop = false;

  const apiUrl = "/api/scan/" + encodeURIComponent(token);

  const config = {
    fps: 12,
    qrbox: { width: 300, height: 300 },
    rememberLastUsedCamera: true
  };

  async function stopCamera(){
    try{
      if (html5) {
        try { await html5.stop(); } catch(e) {}
        try { html5.clear(); } catch(e) {}
      }
    } finally {
      html5 = null;
      cameraStarted = false;
    }
  }

  async function setupZoomIfAvailable(){
    try{
      const video = document.querySelector("#reader video");
      if (!video || !video.srcObject) return;

      const track = video.srcObject.getVideoTracks()[0];
      if (!track || !track.getCapabilities) return;

      const caps = track.getCapabilities();
      log("caps=" + JSON.stringify(caps));

      // continuous focus if supported
      try{
        if (caps && caps.focusMode && Array.isArray(caps.focusMode) && caps.focusMode.includes("continuous")) {
          await track.applyConstraints({ advanced: [{ focusMode: "continuous" }] });
          log("Applied focusMode=continuous");
        }
      }catch(e){
        log("Focus constraints failed: " + (e && e.message ? e.message : e));
      }

      // zoom slider if supported
      if (!caps || !caps.zoom) return;
      const z = caps.zoom;

      const wrap = document.getElementById("zoomWrap");
      const slider = document.getElementById("zoomSlider");
      wrap.style.display = "block";
      slider.min = z.min;
      slider.max = z.max;
      slider.step = z.step || 0.1;

      slider.oninput = async () => {
        try{
          await track.applyConstraints({ advanced: [{ zoom: parseFloat(slider.value) }]});
        }catch(e){}
      };
    }catch(e){}
  }

  async function startScanner(){
    if (cameraStarted) return;
    if (typeof Html5Qrcode === "undefined"){
      setStatus("❌ html5-qrcode did not load.", "bad");
      return;
    }

    setStatus("Starting scanner…", "");
    html5 = new Html5Qrcode("reader");

    async function onScanSuccess(decodedText){
      setStatus("Scanned! Sending to Dashboard…", "");

      try{
        const r = await fetch(apiUrl, {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({ text: decodedText })
        });
        const j = await r.json().catch(()=> ({}));
        if (j && j.ok) {
          setStatus("✅ Sent. You can go back to the Dashboard.", "ok");
          try { await stopCamera(); } catch(e) {}
        } else {
          setStatus("❌ Failed to send: " + (j.error || "unknown"), "bad");
        }
      }catch(e){
        setStatus("❌ Failed to send: " + (e && e.message ? e.message : e), "bad");
      }
    }
    function onScanFailure(_err){ /* ignore */ }

    const cameraConfig = { facingMode: "environment" };

    let cams = null;
    try { cams = await Html5Qrcode.getCameras(); } catch(e) { cams = null; }

    function pickBestCameraId(cams){
      if (!cams || !cams.length) return null;
      const byLabel = cams.find(c => /back|rear|environment/i.test(c.label || ""));
      return (byLabel || cams[cams.length - 1]).id;
    }
    const bestId = pickBestCameraId(cams);

    try {
      await html5.start(cameraConfig, config, onScanSuccess, onScanFailure);
    } catch (e1) {
      if (bestId) {
        await html5.start(bestId, config, onScanSuccess, onScanFailure);
      } else {
        throw e1;
      }
    }

    cameraStarted = true;
    manualStop = false;
    setStatus("Camera ready. Scan a code.", "");
    setupZoomIfAvailable().catch(()=>{});
  }

  document.getElementById("startBtn").onclick = async () => {
    manualStop = false;
    try { await startScanner(); }
    catch(e){
      setStatus("❌ Start failed: " + (e && e.message ? e.message : e), "bad");
      log("ERROR: " + (e && e.stack ? e.stack : e));
    }
  };

  document.getElementById("stopBtn").onclick = async () => {
    manualStop = true;
    await stopCamera();
    setStatus("Camera stopped. Tap Start camera.", "");
  };

  document.getElementById("refocusBtn").onclick = async () => {
    try{
      const video = document.querySelector("#reader video");
      const track = (video && video.srcObject) ? video.srcObject.getVideoTracks()[0] : null;
      if (!track || !track.getCapabilities) {
        setStatus("Refocus not available.", "");
        return;
      }
      const caps = track.getCapabilities();
      if (caps && caps.focusMode && Array.isArray(caps.focusMode) && caps.focusMode.includes("continuous")) {
        await track.applyConstraints({ advanced: [{ focusMode: "continuous" }] });
        setStatus("Refocus requested.", "");
      } else {
        setStatus("Refocus not supported on this device.", "");
      }
    }catch(e){
      setStatus("Refocus failed.", "bad");
    }
  };

  setStatus("Tap “Start camera”. If prompted, allow camera access.", "");
})();
</script>
</body>
</html>
"""


PHONE_HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>HWDB Dashboard Scanner</title>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; padding: 12px; }
    #reader { width: 100%; max-width: 520px; margin: 0 auto; }
    .box { max-width: 520px; margin: 12px auto; padding: 10px; border: 1px solid #ddd; border-radius: 12px; }
    .ok { color: #0a7; font-weight: 800; }
    .bad { color: #a33; font-weight: 800; }
    code { word-break: break-word; }
    button { padding:10px 14px; border-radius:10px; border:1px solid #ccc; font-weight:800; }
    .row { display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; align-items:center; }
    .muted { color:#666; font-size:13px; }
  </style>
  <script src="/static/html5-qrcode.min.js"></script>
</head>
<body>
  <div style="text-align:center; margin-bottom:10px;">
    <img
      src="/static/IconBig.png"
      alt="HWDB Dashboard"
      style="width:84px; height:84px; object-fit:contain; border-radius:18px;"
    />
  </div>
  <div class="box">
    <div><b>HWDB Dashboard scanner</b></div>
    <div class="muted">Keep this page open. Click 📷 in the Dashboard to start a scan.</div>
    <div style="margin-top:6px; font-size: 13px; color:#555">
      Active token: <code id="tok">—</code><br/>
      Mode: <code id="mode">—</code><br/>
      Label: <code id="label">—</code><br/>
      Expires in: <code id="exp">—</code> s<br/>
      Claimed: <code id="claimed">—</code>
    </div>
  </div>

  <div id="reader"></div>

  <div class="box" id="statusBox">
    <div id="status" style="color:#555">Waiting for a scan request from Dashboard…</div>

    <div class="row">
      <button id="startBtn">Start camera</button>
      <button id="stopBtn">Stop camera</button>
      <button id="refocusBtn">Refocus</button>
    </div>

    <div id="zoomWrap" style="margin-top:10px; display:none;">
      <div style="font-weight:800; margin-bottom:6px;">Zoom</div>
      <input id="zoomSlider" type="range" min="1" max="1" step="0.1" value="1" style="width:100%;">
    </div>

    <pre id="dbg" style="white-space:pre-wrap; font-size:12px; color:#444; margin-top:10px;"></pre>
  </div>

<script>
(function(){
  const statusEl = document.getElementById("status");
  const dbg = document.getElementById("dbg");
  const tokEl = document.getElementById("tok");
  const modeEl = document.getElementById("mode");
  const labelEl = document.getElementById("label");
  const expEl = document.getElementById("exp");
  const claimedEl = document.getElementById("claimed");

  // debug=1 enables logs; default off
  const DEBUG = new URLSearchParams(window.location.search).get("debug") === "1";
  if (!DEBUG) dbg.style.display = "none";
  function log(x){ if (DEBUG) dbg.textContent += x + "\n"; }

  function setStatus(msg, cls){ statusEl.className = cls || ""; statusEl.textContent = msg; }

  // Stable phone id (multi-phone support / claiming)
  const phoneIdKey = "hwdb_scanner_phone_id";
  let phoneId = localStorage.getItem(phoneIdKey);
  if (!phoneId) {
    phoneId = (crypto && crypto.randomUUID) ? crypto.randomUUID() : ("p_" + Math.random().toString(16).slice(2));
    localStorage.setItem(phoneIdKey, phoneId);
  }

  let html5 = null;
  let cameraStarted = false;
  let manualStop = false;

  let currentToken = null;
  let lastActiveSeen = false;

  let lastTokenSeen = null;
  let lastClaimedByMe = false;
  let startInFlight = false;

  const config = { fps: 12, qrbox: { width: 300, height: 300 }, rememberLastUsedCamera: true };

  async function stopCamera(){
    try{
      if (html5) {
        try { await html5.stop(); } catch(e) {}
        try { html5.clear(); } catch(e) {}
      }
    } finally {
      html5 = null;
      cameraStarted = false;
    }
  }

  async function setupZoomIfAvailable(){
    try{
      const video = document.querySelector("#reader video");
      if (!video || !video.srcObject) return;

      const track = video.srcObject.getVideoTracks()[0];
      if (!track || !track.getCapabilities) return;

      const caps = track.getCapabilities();
      log("caps=" + JSON.stringify(caps));

      // continuous focus if supported
      try{
        if (caps && caps.focusMode && Array.isArray(caps.focusMode) && caps.focusMode.includes("continuous")) {
          await track.applyConstraints({ advanced: [{ focusMode: "continuous" }] });
          log("Applied focusMode=continuous");
        }
      }catch(e){
        log("Focus constraints failed: " + (e && e.message ? e.message : e));
      }

      // zoom slider if supported
      if (!caps || !caps.zoom) return;
      const z = caps.zoom;

      const wrap = document.getElementById("zoomWrap");
      const slider = document.getElementById("zoomSlider");
      wrap.style.display = "block";
      slider.min = z.min;
      slider.max = z.max;
      slider.step = z.step || 0.1;

      slider.oninput = async () => {
        try{
          await track.applyConstraints({ advanced: [{ zoom: parseFloat(slider.value) }]});
        }catch(e){}
      };
    }catch(e){}
  }

  async function startScanner(){
    if (cameraStarted) return;
    if (typeof Html5Qrcode === "undefined"){
      setStatus("❌ html5-qrcode did not load.", "bad");
      return;
    }
    if (!currentToken){
      setStatus("Click 📷 in Dashboard first (no active token).", "bad");
      return;
    }

    setStatus("Starting scanner…", "");
    html5 = new Html5Qrcode("reader");

    // Fast + reliable on iOS: don’t enumerate cameras
    async function onScanSuccess(decodedText){
      if (!currentToken) {
        setStatus("Scanned, but no active token. Click 📷 in Dashboard.", "bad");
        return;
      }

      setStatus("Scanned! Sending to Dashboard…", "");
      const apiUrl = "/api/scan/" + encodeURIComponent(currentToken);

      try{
        const r = await fetch(apiUrl, {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({ text: decodedText })
        });
        const j = await r.json().catch(()=> ({}));
        if (j && j.ok) {
          setStatus("✅ Sent. Click 📷 again for another scan.", "ok");
          // Keep camera running on /phone
        } else {
          setStatus("❌ Send failed: " + (j.error || "unknown"), "bad");
        }
      } catch(e){
        setStatus("❌ Send failed: " + (e && e.message ? e.message : e), "bad");
      }
    }
    function onScanFailure(_err){ /* ignore */ }

    const cameraConfig = { facingMode: "environment" };

    let cams = null;
    try { cams = await Html5Qrcode.getCameras(); } catch(e) { cams = null; }

    function pickBestCameraId(cams){
      if (!cams || !cams.length) return null;
      const byLabel = cams.find(c => /back|rear|environment/i.test(c.label || ""));
      return (byLabel || cams[cams.length - 1]).id;
    }
    const bestId = pickBestCameraId(cams);

    try {
      await html5.start(cameraConfig, config, onScanSuccess, onScanFailure);
    } catch (e1) {
      if (bestId) {
        await html5.start(bestId, config, onScanSuccess, onScanFailure);
      } else {
        throw e1;
      }
    }





  

    cameraStarted = true;
    manualStop = false;
    setStatus("Camera ready. Waiting for scan…", "");
    setupZoomIfAvailable().catch(()=>{});
  }

  async function claimActive(){
    const r = await fetch("/api/active/claim", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ phone_id: phoneId })
    });
    return await r.json().catch(()=> ({}));
  }

  async function releaseActive(){
    try{
      await fetch("/api/active/release", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ phone_id: phoneId })
      });
    }catch(e){}
  }

  document.getElementById("startBtn").onclick = async () => {
    if (startInFlight) return;
    startInFlight = true;

    try{
      manualStop = false;

      if (!currentToken){
        setStatus("Click 📷 in Dashboard first (no active token).", "bad");
        return;
      }

      // Claim the job so multiple phones don't race (and so two taps don't race either)
      const j = await claimActive();
      if (!j || !j.ok || !j.active) {
        setStatus("No active scan request. Click 📷 in Dashboard.", "bad");
        return;
      }
      if (!j.can_scan) {
        setStatus("This scan is already being used on another phone.", "bad");
        return;
      }

      // Ensure we use the server's current token
      currentToken = j.token || currentToken;

      await startScanner();

    } catch(e){
      setStatus("❌ Start failed: " + (e && e.message ? e.message : e), "bad");
      log("ERROR: " + (e && e.stack ? e.stack : e));
    } finally {
      startInFlight = false;
    }
  };

  document.getElementById("stopBtn").onclick = async () => {
    manualStop = true;
    await stopCamera();
    await releaseActive();
    setStatus("Camera stopped. Tap Start camera.", "");
  };

  document.getElementById("refocusBtn").onclick = async () => {
    try{
      const video = document.querySelector("#reader video");
      const track = (video && video.srcObject) ? video.srcObject.getVideoTracks()[0] : null;
      if (!track || !track.getCapabilities) {
        setStatus("Refocus not available.", "");
        return;
      }
      const caps = track.getCapabilities();
      if (caps && caps.focusMode && Array.isArray(caps.focusMode) && caps.focusMode.includes("continuous")) {
        await track.applyConstraints({ advanced: [{ focusMode: "continuous" }] });
        setStatus("Refocus requested.", "");
      } else {
        setStatus("Refocus not supported on this device.", "");
      }
    }catch(e){
      setStatus("Refocus failed.", "bad");
    }
  };

  async function pollActive(){
    try{
      const r = await fetch("/api/active?phone_id=" + encodeURIComponent(phoneId), { method: "GET" });
      const j = await r.json().catch(()=> ({}));

      if (!j || !j.ok || !j.active) {
        if (lastClaimedByMe) {
          releaseActive().catch(()=>{});
        }
        lastClaimedByMe = false;
        lastTokenSeen = null;

        tokEl.textContent = "—";
        modeEl.textContent = "—";
        labelEl.textContent = "—";
        expEl.textContent = "—";
        claimedEl.textContent = "—";
        currentToken = null;

        // Auto-stop camera when Dashboard cancels the job
        if (cameraStarted && !manualStop) {
          await stopCamera();
          setStatus("Scan canceled by Dashboard. Tap Start camera for next scan.", "");
        }

        lastActiveSeen = false;
        return;
      }

      tokEl.textContent = j.token || "—";
      modeEl.textContent = j.mode || "—";
      labelEl.textContent = j.label || "—";
      expEl.textContent = Math.floor(j.expires_in_s || 0);

      const claimed = !!j.claimed;
      const claimedByMe = !!j.claimed_by_me;
      lastClaimedByMe = claimedByMe;
      claimedEl.textContent = claimed ? (claimedByMe ? "yes (this phone)" : "yes (other phone)") : "no";

      //currentToken = j.token || null;
      const newToken = j.token || null;
      if (lastTokenSeen && newToken && newToken !== lastTokenSeen) {
        // token changed; release old claim
        //releaseActive().catch(()=>{});
        if (lastClaimedByMe) releaseActive().catch(()=>{});
      }
      lastTokenSeen = newToken;
      currentToken = newToken;

      // Status message only when transitions happen (avoid flicker)
      if (!lastActiveSeen) {
        setStatus("Scan request received. Tap Start camera.", "");
      }
      lastActiveSeen = true;

      // do NOT auto-start camera here (prevents “Stop” auto-restarting).
      // User gesture on Start is best for iOS permissions anyway.
    } catch(e){
      // keep quiet
    }
  }

  setInterval(pollActive, 300);
  pollActive();

  setStatus("Waiting for a scan request from Dashboard…", "");
})();
</script>
</body>
</html>
"""



def create_scanner_app(*, lan_mode: bool = False) -> Flask:
    static_dir = Path(__file__).with_name("static")
    app = Flask("hwdb_scanner", static_folder=str(static_dir), static_url_path="/static")
    
    @app.before_request
    def _scanner_gate():
        # Always keep your IP restriction
        ra = request.remote_addr or ""
        if not is_private_or_local_ip(ra):
            return Response("Forbidden", status=403)

        # In LAN mode, additionally require the same "paired" cookie the Dashboard sets
        #if lan_mode:
        #    if request.cookies.get("HWDB_LAN_OK") != "1":
        #        return Response("Not paired", status=401)

        # allow
        return None
    
    @app.get("/health")
    def health():
        cleanup_sessions()

        #portproxy = _portproxy_commands_for_wsl(port=_SERVER_BIND_PORT or 8766)
        portproxy = _portproxy_commands_for_wsl_multi(ports=[8050, _SERVER_BIND_PORT or 8766])
        mirrored = _mirrored_networking_instructions_for_wsl(ports=[8050, _SERVER_BIND_PORT or 8766])
        
        # Provide basic diagnostics so the Dash side (and users) can see why it fails
        return jsonify({
            "ok": True,
            "started_ts": _SERVER_STARTED_TS,
            "uptime_s": (time.time() - _SERVER_STARTED_TS) if _SERVER_STARTED_TS else None,
            "bind_host": _SERVER_BIND_HOST,
            "bind_port": _SERVER_BIND_PORT,
            "start_error": _SERVER_START_ERROR,
            "wsl2_portproxy": portproxy,
            "wsl2_mirrored": mirrored,
            "wsl2_troubleshooting": [
                "Run curl tests from Windows (NOT inside WSL) to verify portproxy is listening:",
                "  curl.exe -vk https://127.0.0.1:8766/health",
                "  curl.exe -vk https://<WIN_IP>:8766/health   (or http:// for http mode)",
                "If those work on Windows but phone cannot connect, it is usually Windows Firewall / network profile.",
                "Make sure the firewall rules exist for ports 8050 and 8766, and your network is not blocking inbound LAN.",
            ],
        })

    @app.get("/scan/<token>")
    def scan_page(token: str):
        ra = request.remote_addr or ""
        if not is_private_or_local_ip(ra):
            return Response("Forbidden", status=403)

        st = get_scan_status(token)
        if not st.get("ok"):
            return Response("Invalid or expired token.", status=404)

        mode = st.get("mode") or "component_type"
        html = SCAN_HTML.replace("{{TOKEN}}", token).replace("{{MODE}}", str(mode))
        return Response(html, mimetype="text/html")

    @app.get("/api/scan/<token>")
    def api_get(token: str):
        ra = request.remote_addr or ""
        if not is_private_or_local_ip(ra):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        return jsonify(get_scan_status(token))

    @app.post("/api/scan/<token>")
    def api_post(token: str):
        ra = request.remote_addr or ""
        if not is_private_or_local_ip(ra):
            return jsonify({"ok": False, "error": "forbidden"}), 403

        payload = request.get_json(silent=True) or {}
        text = (payload.get("text") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "missing_text"}), 400

        sess = set_scan_result(token, raw_text=text, remote_addr=ra)
        if not sess:
            return jsonify({"ok": False, "error": "invalid_or_expired"}), 404

        return jsonify({"ok": True, "used": True, "extracted": sess.extracted})

    @app.get("/phone")
    def phone_page():
        ra = request.remote_addr or ""
        if not is_private_or_local_ip(ra):
            return Response("Forbidden", status=403)
        return Response(PHONE_HTML, mimetype="text/html")

    @app.get("/api/active")
    def api_active_get():
        ra = request.remote_addr or ""
        if not is_private_or_local_ip(ra):
            return jsonify({"ok": False, "error": "forbidden"}), 403

        cleanup_sessions()
        phone_id = (request.args.get("phone_id") or "").strip()
        return jsonify(get_active_job_status(phone_id=phone_id))

    @app.post("/api/active")
    def api_active_post():
        ra = request.remote_addr or ""
        if not is_private_or_local_ip(ra):
            return jsonify({"ok": False, "error": "forbidden"}), 403

        payload = request.get_json(silent=True) or {}
        token = (payload.get("token") or "").strip()
        mode = (payload.get("mode") or "component_type").strip().lower()
        label = (payload.get("label") or "").strip()
        ttl_s = float(payload.get("ttl_s") or 120.0)

        if not token:
            return jsonify({"ok": False, "error": "missing_token"}), 400

        st = get_scan_status(token)
        if not st.get("ok"):
            return jsonify({"ok": False, "error": "invalid_or_expired_token"}), 404

        return jsonify(set_active_job(token=token, mode=mode, ttl_s=ttl_s, label=label))

    @app.post("/api/active/claim")
    def api_active_claim():
        ra = request.remote_addr or ""
        if not is_private_or_local_ip(ra):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        payload = request.get_json(silent=True) or {}
        phone_id = (payload.get("phone_id") or "").strip()
        return jsonify(claim_active_job(phone_id))

    @app.post("/api/active/release")
    def api_active_release():
        ra = request.remote_addr or ""
        if not is_private_or_local_ip(ra):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        payload = request.get_json(silent=True) or {}
        phone_id = (payload.get("phone_id") or "").strip()
        return jsonify(release_active_job(phone_id))


    @app.post("/api/active/clear")
    def api_active_clear():
        ra = request.remote_addr or ""
        if not is_private_or_local_ip(ra):
            return jsonify({"ok": False, "error": "forbidden"}), 403

        clear_active_job()
        return jsonify({"ok": True, "active": False})

    @app.post("/api/scan/<token>/cancel")
    def api_scan_cancel(token: str):
        ra = request.remote_addr or ""
        if not is_private_or_local_ip(ra):
            return jsonify({"ok": False, "error": "forbidden"}), 403

        ok = cancel_scan_session(token)
        # even if it didn't exist, treat as ok (idempotent cancel)
        return jsonify({"ok": True, "canceled": bool(ok)})

    
    return app


def _normalize_bind_host(host: str | None) -> str:
    """
    Phone-accessible default:
      - If host is None/""/"auto": bind 0.0.0.0 (all interfaces)
      - Else: bind exactly what caller requested
    """
    h = (host or "").strip()
    if not h or h.lower() == "auto":
        return "0.0.0.0"
    return h


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""

def _is_wsl() -> bool:
    if os.environ.get("WSL_INTEROP") or os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        t = _run(["cat", "/proc/version"]).lower()
        return ("microsoft" in t) or ("wsl" in t)
    except Exception:
        return False

def _wsl_eth0_ip() -> str:
    """
    Best effort: return WSL VM IPv4 (eth0).
    """
    # Prefer `ip` output (usually available)
    out = _run(["bash", "-lc", "ip -4 addr show dev eth0"])
    m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)/", out)
    if m:
        return m.group(1)

    # fallback: hostname -I
    out = _run(["bash", "-lc", "hostname -I"])
    for tok in (out or "").split():
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", tok):
            return tok
    return ""

def _windows_lan_ipv4s_from_wsl() -> list[str]:
    """
    Ask Windows for its IPv4 addresses (via powershell.exe), and return plausible
    LAN IPs with a strong preference for the adapter that has an IPv4 default gateway.
    Also filters out common WSL/Hyper-V virtual switch ranges like 172.27.*.
    """
    def is_good(ip: str) -> bool:
        if not re.match(r"^\d+\.\d+\.\d+\.\d+$", ip or ""):
            return False
        if ip.startswith("127.") or ip.startswith("169.254."):
            return False

        # Private ranges we generally want
        is_private = ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172.")
        if not is_private:
            return False

        # Filter out WSL/Hyper-V-ish ranges that often show up on Windows hosts
        # (The specific complaint you saw was 172.27.*)
        if ip.startswith("172.27."):
            return False

        # WSL/Hyper-V can also use other 172.* ranges on some systems (172.28/29/etc)....!!??
        #if ip.startswith(("172.27.", "172.28.", "172.29.", "172.30.", "172.31.")):
        #    return False

        return True

    # 1) BEST: IPs on adapters that have an IPv4 default gateway (i.e., real Wi-Fi/Ethernet)
    ps_gateway = _run([
        "powershell.exe", "-NoProfile", "-Command",
        r"""
        $cfg = Get-NetIPConfiguration |
          Where-Object { $_.IPv4DefaultGateway -ne $null -and $_.NetAdapter.Status -eq 'Up' } |
          ForEach-Object { $_.IPv4Address.IPAddress }
        $cfg
        """.strip()
    ])

    gateway_ips: list[str] = []
    for line in (ps_gateway or "").splitlines():
        ip = line.strip()
        if is_good(ip):
            gateway_ips.append(ip)

    # 2) Fallback: all IPv4s (less trustworthy ordering)
    ps_all = _run([
        "powershell.exe", "-NoProfile", "-Command",
        r"Get-NetIPAddress -AddressFamily IPv4 "
        r"| Where-Object { $_.IPAddress -match '^\d+\.' -and $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } "
        r"| Select-Object -ExpandProperty IPAddress"
    ])

    all_ips: list[str] = []
    for line in (ps_all or "").splitlines():
        ip = line.strip()
        if is_good(ip):
            all_ips.append(ip)

    # Combine: gateway IPs first, then any remaining good IPs
    out: list[str] = []
    seen: set[str] = set()
    for ip in gateway_ips + all_ips:
        if ip and ip not in seen:
            seen.add(ip)
            out.append(ip)

    return out



def _mirrored_networking_instructions_for_wsl(*, ports: list[int]) -> dict:
    """
    Windows 11 + a reasonably up-to-date WSL can use *mirrored networking* so the
    Dash (8050) and Scanner (8766) ports are reachable on the Windows **LAN IP**
    WITHOUT netsh portproxy.

    This returns a structured set of instructions and URLs to try.
    """
    # normalize ports
    norm_ports: list[int] = []
    for p in (ports or []):
        try:
            p = int(p)
            if 1 <= p <= 65535:
                norm_ports.append(p)
        except Exception:
            pass
    # de-dupe preserve order
    seenp: set[int] = set()
    norm_ports = [p for p in norm_ports if not (p in seenp or seenp.add(p))]

    if not norm_ports:
        return {"ok": False, "reason": "no_ports"}

    if not _is_wsl():
        return {"ok": False, "reason": "not_wsl", "ports": norm_ports}

    # Best-effort Windows LAN IP discovery (for display / copy-paste).
    # This is only for printing; mirrored networking itself does not depend on this.
    win_ips = _windows_lan_ipv4s_from_wsl()
    if not win_ips:
        win_ips = ["<WINDOWS_LAN_IP>"]

    # Helpful example URLs (users still choose the correct WIN_IP)
    scanner_urls = [f"https://{ip}:{norm_ports[-1]}/phone" for ip in win_ips if ip and "<" not in ip]
    dash_urls = [f"https://{ip}:{norm_ports[0]}/" for ip in win_ips if ip and "<" not in ip]

    # NOTE: mirrored networking is Windows 11 only.
    steps = [
        "Windows 11 only. Update WSL: run `wsl --update`, then `wsl --shutdown`.",
        "Enable mirrored networking: create/edit `%UserProfile%\\.wslconfig` and add:",
        "    [wsl2]\n    networkingMode=mirrored\n    dnsTunneling=true",
        "Restart WSL: `wsl --shutdown` then open your WSL distro again.",
        "Start the app in WSL: `hwdb-dash --lan` (Dash=8050, Scanner=8766).",
        "On your phone/tablet (same Wi‑Fi), open:",
        "    https://<WINDOWS_LAN_IP>:8766/phone",
        "If the browser warns about the self-signed cert, choose Advanced → Proceed.",
        "If this fails, use the Portproxy fallback below."
    ]

    verify = [
        "Find your Windows LAN IP (PowerShell): `ipconfig` (look for Wi‑Fi/Ethernet IPv4).",
        "Check scanner from WSL: `curl -k https://<WINDOWS_LAN_IP>:8766/health`",
        "Check Dash from phone/laptop: `https://<WINDOWS_LAN_IP>:8050/`",
    ]

    return {
        "ok": True,
        "mode": "mirrored",
        "ports": norm_ports,
        "windows_ips": win_ips,
        "phone_urls": scanner_urls,
        "dash_urls": dash_urls,
        "steps": steps,
        "verify": verify,
        "note": "Recommended for Windows 11 + WSL (mirrored networking). No netsh portproxy needed.",
    }

def _portproxy_commands_for_wsl_multi(*, ports: list[int]) -> dict:
    """
    Multi-port version of _portproxy_commands_for_wsl().

    Returns a dict with:
      - ok: bool
      - wsl_ip: str
      - windows_ips: list[str]
      - ports: list[int]
      - commands: list[str]   (PowerShell lines to run as Admin)
      - phone_urls: list[str] (https://<WIN_IP>:<port>/phone for each port)
      - note: str (optional)

    Behavior:
      - If not WSL -> ok False
      - If WSL eth0 IP not found -> ok False
      - If Windows LAN IPs cannot be discovered -> uses ["<WINDOWS_LAN_IP>"] placeholder
      - Produces blocks for each WIN_IP, and inside each block produces rules for all ports.
      - Uses listenaddress=$WIN_IP (not 0.0.0.0) to stay consistent with your current approach.
    """
    # normalize ports
    norm_ports: list[int] = []
    for p in (ports or []):
        try:
            ip = int(p)
            if 1 <= ip <= 65535:
                norm_ports.append(ip)
        except Exception:
            pass
    # de-dupe preserve order
    seenp = set()
    norm_ports = [p for p in norm_ports if not (p in seenp or seenp.add(p))]

    if not norm_ports:
        return {"ok": False, "reason": "no_ports"}

    if not _is_wsl():
        return {"ok": False, "reason": "not_wsl", "ports": norm_ports}

    wsl_ip = _wsl_eth0_ip()
    win_ips = _windows_lan_ipv4s_from_wsl()

    if not wsl_ip:
        return {
            "ok": False,
            "reason": "no_wsl_ip",
            "wsl_ip": "",
            "windows_ips": win_ips,
            "ports": norm_ports,
        }

    # If Windows IP can't be discovered, user can fill it in manually
    if not win_ips:
        win_ips = ["<WINDOWS_LAN_IP>"]

    cmds: list[str] = []
    cmds.append("### Portproxy fallback (if mirrored networking is unavailable) ###")
    cmds.append("### Run in *Windows PowerShell as Administrator* ###")
    cmds.append(f"$WSL_IP = \"{wsl_ip}\"")
    cmds.append("")

    # --- LOOPBACK HELPER (so /pair always works from Windows browser) ---
    # Even if the user picked the wrong WIN_IP, this makes:
    #   https://127.0.0.1:8050/pair
    # work reliably on Windows.
    if 8050 in norm_ports:
        cmds.append("# --- LOOPBACK helper (recommended) ---")
        cmds.append("# This makes the pairing page always reachable from Windows:")
        cmds.append("#   https://127.0.0.1:8050/pair")
        cmds.append("netsh interface portproxy delete v4tov4 listenaddress=127.0.0.1 listenport=8050")
        cmds.append("netsh interface portproxy add    v4tov4 listenaddress=127.0.0.1 listenport=8050 connectaddress=$WSL_IP connectport=8050")
        cmds.append("")
    
    cmds.append("# Optional cleanup of common stale listenaddresses (safe even if they do not exist):")
    cmds.append("#   netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=<PORT>")
    cmds.append("#   netsh interface portproxy delete v4tov4 listenaddress=172.27.64.1 listenport=<PORT>   (common Hyper-V vSwitch)")
    cmds.append("")
    cmds.append("# Optional cleanup of common stale listenaddresses (safe even if they do not exist):")
    cmds.append("#   netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=<PORT>")
    cmds.append("#   netsh interface portproxy delete v4tov4 listenaddress=172.27.64.1 listenport=<PORT>   (common Hyper-V vSwitch)")
    cmds.append("")
    cmds.append("# Try ONE of the WIN_IP blocks below. Pick the IP that matches your Wi-Fi/Ethernet adapter.")
    cmds.append("# If the phone still can’t connect, try the next WIN_IP block.")
    cmds.append("")

    cmds.append("# Tip: if you previously tried other instructions, remove any stale rules first:")
    cmds.append("#   netsh interface portproxy show v4tov4")
    cmds.append("#   (delete any listenaddress in 172.27.* or wrong adapter IPs for these ports)")
    cmds.append("")

    # --- EASIEST OPTION: listen on all interfaces (0.0.0.0) ---
    # This avoids picking the "right" Windows adapter IP.
    cmds.append("# --- WIN_IP = 0.0.0.0 (listen on all interfaces) ---")
    cmds.append("$WIN_IP = \"0.0.0.0\"")
    for port in norm_ports:
        cmds.append(f"netsh interface portproxy delete v4tov4 listenaddress=$WIN_IP listenport={port}")
        cmds.append(f"netsh interface portproxy add    v4tov4 listenaddress=$WIN_IP listenport={port} connectaddress=$WSL_IP connectport={port}")
    cmds.append("")

    for ip in win_ips:
        cmds.append(f"# --- WIN_IP = {ip} ---")
        cmds.append(f"$WIN_IP = \"{ip}\"")
        for port in norm_ports:
            cmds.append(f"netsh interface portproxy delete v4tov4 listenaddress=$WIN_IP listenport={port}")
            cmds.append(f"netsh interface portproxy add    v4tov4 listenaddress=$WIN_IP listenport={port} connectaddress=$WSL_IP connectport={port}")
        cmds.append("")

    cmds.append("# Allow inbound firewall (only needs to be done once per port):")
    for port in norm_ports:
        cmds.append(
            "New-NetFirewallRule -DisplayName \"HWDB Port {}\" -Direction Inbound -Action Allow "
            "-Protocol TCP -LocalPort {} -ErrorAction SilentlyContinue".format(port, port)
        )

    cmds.append("")
    cmds.append("# Then open on phone (pick the right WIN_IP):")
    # If you want more generic guidance, keep /phone. It’s fine for scanner; for Dash, user will use /?k=...
    for port in norm_ports:
        cmds.append(f"#   https://<WIN_IP>:{port}/phone   (scanner UX)")
        cmds.append(f"#   https://<WIN_IP>:{port}/       (dashboard if this port is Dash)")
    cmds.append("")

    phone_urls: list[str] = []
    for ip in win_ips:
        if not ip or "<" in ip:
            continue
        for port in norm_ports:
            phone_urls.append(f"https://{ip}:{port}/phone")

    return {
        "ok": True,
        "wsl_ip": wsl_ip,
        "windows_ips": win_ips,
        "ports": norm_ports,
        "commands": cmds,
        "phone_urls": phone_urls,
        "note": "Fallback for Windows 10 / older WSL: use portproxy. Run ONE WIN_IP block that matches your Wi‑Fi/Ethernet adapter.",
    }

def _portproxy_commands_for_wsl(*, port: int) -> dict:
    """
    Returns a dict with:
      - ok
      - wsl_ip
      - windows_ips
      - commands: list[str] (PowerShell/cmd lines)
      - phone_urls: list[str] that should work AFTER portproxy is set
    """
    if not _is_wsl():
        return {"ok": False, "reason": "not_wsl"}

    wsl_ip = _wsl_eth0_ip()
    win_ips = _windows_lan_ipv4s_from_wsl()

    if not wsl_ip:
        return {"ok": False, "reason": "no_wsl_ip", "wsl_ip": "", "windows_ips": win_ips}

    # If Windows IP can't be discovered, user can fill it in manually
    if not win_ips:
        win_ips = ["<WINDOWS_LAN_IP>"]

    cmds = []
    #cmds.append("### Run in *Windows PowerShell as Administrator* ###")
    #cmds.append("# 1) Pick ONE Windows LAN IP from the list below (Wi-Fi/Ethernet):")
    #cmds.append("#    " + ", ".join(win_ips))
    #cmds.append(f"$WIN_IP = \"{win_ips[0]}\"")
    #cmds.append(f"$WSL_IP = \"{wsl_ip}\"")
    #cmds.append("")
    #cmds.append("# 2) Recreate the portproxy rule (safe to re-run):")
    #cmds.append(f"netsh interface portproxy delete v4tov4 listenaddress=$WIN_IP listenport={int(port)}")
    #cmds.append(f"netsh interface portproxy add    v4tov4 listenaddress=$WIN_IP listenport={int(port)} connectaddress=$WSL_IP connectport={int(port)}")
    #cmds.append("")
    #cmds.append("# 3) Allow inbound firewall (only needs to be done once):")
    #cmds.append(f"New-NetFirewallRule -DisplayName \"HWDB Scanner {int(port)}\" -Direction Inbound -Action Allow -Protocol TCP -LocalPort {int(port)}")
    #cmds.append("")
    #cmds.append("# 4) Then open on phone:")
    #cmds.append(f"#    https://{win_ips[0]}:{int(port)}/phone")

    cmds.append("### Run in *Windows PowerShell as Administrator* ###")
    cmds.append(f"$WSL_IP = \"{wsl_ip}\"")
    cmds.append("")
    cmds.append("# Try ONE of the blocks below. Pick the IP that matches your Wi-Fi/Ethernet adapter.")
    cmds.append("# If the phone still can’t connect, try the next WIN_IP block.")
    cmds.append("")

    for ip in win_ips:
        cmds.append(f"# --- WIN_IP = {ip} ---")
        cmds.append(f"$WIN_IP = \"{ip}\"")
        cmds.append(f"netsh interface portproxy delete v4tov4 listenaddress=$WIN_IP listenport={int(port)}")
        cmds.append(f"netsh interface portproxy add    v4tov4 listenaddress=$WIN_IP listenport={int(port)} connectaddress=$WSL_IP connectport={int(port)}")
        cmds.append("")
    cmds.append("# Allow inbound firewall (only needs to be done once):")
    cmds.append(f"New-NetFirewallRule -DisplayName \"HWDB Scanner {int(port)}\" -Direction Inbound -Action Allow -Protocol TCP -LocalPort {int(port)}")
    cmds.append("")
    cmds.append("# Then open on phone:")
    cmds.append("#   https://<WIN_IP>:{}/phone".format(int(port)))

    phone_urls = [f"https://{ip}:{int(port)}/phone" for ip in win_ips if ip and "<" not in ip]

    return {
        "ok": True,
        "wsl_ip": wsl_ip,
        "windows_ips": win_ips,
        "commands": cmds,
        "phone_urls": phone_urls,
        "wsl_helper": f"python3 -c 'import socket; import re, subprocess; "
              f"wsl_ip=subprocess.check_output([\"bash\",\"-lc\",\"ip -4 addr show dev eth0\"],text=True); "
              f"m=re.search(r\"inet\\s+(\\d+\\.\\d+\\.\\d+\\.\\d+)/\", wsl_ip); "
              f"print(\"WSL_IP=\", m.group(1) if m else \"?\")'",
    }


class ScannerServerThread(threading.Thread):
    def __init__(self, host: str | None, port: int, *, ssl_context=None, lan_mode: bool = False):
        super().__init__(daemon=True)
        self.host = _normalize_bind_host(host)
        self.port = int(port)

        self._ready_evt = threading.Event()
        self._server = None

        # If caller didn't supply ssl_context, use persistent self-signed cert
        # If cert generation fails (openssl missing, etc), let's fall back
        # to an ad-hoc SSL context (Werkzeug) so server can still start.
        if ssl_context is None:
            try:
                paths = ensure_scanner_cert()
                ssl_context = (str(paths.cert_pem), str(paths.key_pem))
            except Exception:
                # Werkzeug supports "adhoc" (generates ephemeral self-signed)
                ssl_context = "adhoc"

        self.ssl_context = ssl_context
        self.lan_mode = bool(lan_mode)
        self.app = create_scanner_app(lan_mode=self.lan_mode)

    def wait_ready(self, timeout: float = 2.0) -> bool:
        return self._ready_evt.wait(timeout=timeout)

    def run(self):
        global _SERVER_STARTED_TS, _SERVER_START_ERROR, _SERVER_BIND_HOST, _SERVER_BIND_PORT

        _SERVER_BIND_HOST = self.host
        _SERVER_BIND_PORT = self.port
        _SERVER_START_ERROR = None
        _SERVER_STARTED_TS = None

        # Try HTTPS first (if configured), then fall back to plain HTTP.
        attempts = [
            ("https", self.ssl_context),
            ("http", None),
        ]

        last_exc = None

        for scheme, ssl_ctx in attempts:
            try:
                self._server = make_server(
                    self.host,
                    self.port,
                    self.app,
                    ssl_context=ssl_ctx,
                    threaded=True,
                )
                _SERVER_STARTED_TS = time.time()
                self._ready_evt.set()
                self._server.serve_forever()
                return
            except Exception as e:
                last_exc = e
                _SERVER_START_ERROR = (
                    f"{type(e).__name__}: {e}\n"
                    f"(attempted scheme={scheme})\n"
                    f"{traceback.format_exc()}"
                )
                # If HTTPS failed, loop to HTTP. If HTTP fails too, we exit.
                continue

        self._ready_evt.set()

        
    def shutdown(self):
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass





            
def get_server_diagnostics() -> dict:
    ports = [8050, _SERVER_BIND_PORT or 8766]
    return {
        "started_ts": _SERVER_STARTED_TS,
        "bind_host": _SERVER_BIND_HOST,
        "bind_port": _SERVER_BIND_PORT,
        "start_error": _SERVER_START_ERROR,
        "is_wsl": _is_wsl(),
        # Windows/WSL helper info (LAN mode)
        "wsl2_mirrored": _mirrored_networking_instructions_for_wsl(ports=ports),
        "wsl2_portproxy": _portproxy_commands_for_wsl_multi(ports=ports),
    }
