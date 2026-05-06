# Sisyphus/Gui/Dashboard/utils/scanner.py
from __future__ import annotations

import secrets
import time
import re
import ipaddress
from dataclasses import dataclass
from typing import Optional, Dict, Any


# ----------------------------
# PID parsing
# ----------------------------
# Matches core PID like Z00100300001-07039 (Project + 3 + 3 + 5 + "-" + 5)
_PID_RE = re.compile(r"\b([A-Z]\d{11}-\d{5})\b")

# Also allow suffixes after PID, e.g. Z...-07039-US186 (barcode label)
_PID_WITH_SUFFIX_RE = re.compile(r"\b([A-Z]\d{11}-\d{5})(?:-[A-Za-z0-9]+)*\b")

# HWDB URL forms:
# https://dbweb0.fnal.gov/cdbdev/view/component/<PID>
# https://dbweb0.fnal.gov/cdb/view/component/<PID>
_HWDB_URL_RE = re.compile(r"https?://[^/\s]+/(?:cdbdev|cdb)/view/component/([A-Z]\d{11}-\d{5})", re.IGNORECASE)


def extract_pid(text: str) -> str:
    """
    Extract PID from:
      - HWDB URL
      - bare PID
      - PID with suffix (e.g. ...-US186)
    Returns "" if not found.
    """
    t = (text or "").strip()
    if not t:
        return ""

    m = _HWDB_URL_RE.search(t)
    if m:
        return (m.group(1) or "").strip()

    m = _PID_RE.search(t)
    if m:
        return (m.group(1) or "").strip()

    m = _PID_WITH_SUFFIX_RE.search(t)
    if m:
        return (m.group(1) or "").strip()

    return ""


def pid_to_component_type_id(pid: str) -> str:
    """
    Z00100300001-07039 -> Z00100300001
    """
    pid = (pid or "").strip()
    if not pid:
        return ""
    return pid.split("-", 1)[0].strip()


def component_type_to_type_id(component_type_id: str) -> str:
    """
    Z00100300001 -> 00001
    """
    s = (component_type_id or "").strip()
    if len(s) < 5:
        return ""
    return s[-5:]


def component_type_to_subsystem_id(component_type_id: str) -> str:
    """
    Z00100300001 -> subsystem is digits [4:7) i.e. positions:
      Project(1) + System(3) + Subsystem(3) + Type(5)
      Indexing: 0 1 2 3 4 5 6 7...
      subsystem digits start at index 4 (0-based) for length 3
    """
    s = (component_type_id or "").strip()
    if len(s) < 7:
        return ""
    return s[4:7]


def component_type_to_system_id(component_type_id: str) -> str:
    s = (component_type_id or "").strip()
    if len(s) < 4:
        return ""
    return s[1:4]


def component_type_to_project(component_type_id: str) -> str:
    s = (component_type_id or "").strip()
    if len(s) < 1:
        return ""
    return s[0:1]


def extract_mode_value(scanned_text: str, mode: str) -> str:
    """
    mode in:
      - "pid"
      - "component_type"
      - "type"
      - "subsystem"
      - "system"
      - "project"
    """
    mode = (mode or "").strip().lower()
    pid = extract_pid(scanned_text)
    if not pid:
        return ""

    ctype = pid_to_component_type_id(pid)

    if mode == "pid":
        return pid
    if mode in ("component_type", "componenttype", "component_type_id"):
        return ctype
    if mode == "type":
        return component_type_to_type_id(ctype)
    if mode == "subsystem":
        return component_type_to_subsystem_id(ctype)
    if mode == "system":
        return component_type_to_system_id(ctype)
    if mode == "project":
        return component_type_to_project(ctype)

    # default: return whole PID
    return pid


# ----------------------------
# Scan session registry
# ----------------------------
@dataclass
class ScanSession:
    token: str
    created_ts: float
    expires_ts: float
    mode: str
    used: bool = False
    raw_text: str = ""
    extracted: str = ""
    remote_addr: str = ""

import threading
_SESS_LOCK = threading.Lock()

_SESSIONS: Dict[str, ScanSession] = {}
_DEFAULT_TTL_S = 120.0  # 2 minutes


# ----------------------------
# Active scan job registry (for /phone UX) + claiming
# ----------------------------
import threading

_ACTIVE_LOCK = threading.RLock()   # <-- IMPORTANT: re-entrant
_CLAIM_TTL_S = 30.0                # seconds; claim expires if not refreshed

@dataclass
class ActiveJob:
    token: str
    created_ts: float
    expires_ts: float
    mode: str
    label: str = ""
    claimed_by: str = ""     # phone_id
    claimed_ts: float = 0.0  # when claimed (epoch seconds)

_ACTIVE_JOB: ActiveJob | None = None


def set_active_job(*, token: str, mode: str, ttl_s: float = _DEFAULT_TTL_S, label: str = "") -> dict:
    global _ACTIVE_JOB
    token = (token or "").strip()
    mode = (mode or "component_type").strip().lower()
    now = time.time()

    with _ACTIVE_LOCK:
        # New job => clear any prior claim
        _ACTIVE_JOB = ActiveJob(
            token=token,
            created_ts=now,
            expires_ts=now + float(ttl_s),
            mode=mode,
            label=(label or "").strip(),
            claimed_by="",
            claimed_ts=0.0,
        )

    return get_active_job_status()


def clear_active_job() -> None:
    global _ACTIVE_JOB
    with _ACTIVE_LOCK:
        _ACTIVE_JOB = None


def get_active_job_status(phone_id: str | None = None) -> dict:
    global _ACTIVE_JOB
    now = time.time()

    with _ACTIVE_LOCK:
        if _ACTIVE_JOB is None:
            return {"ok": True, "active": False}

        if now > _ACTIVE_JOB.expires_ts:
            _ACTIVE_JOB = None
            return {"ok": True, "active": False}

        # expire claim if too old
        if _ACTIVE_JOB.claimed_by and (now - float(_ACTIVE_JOB.claimed_ts or 0.0)) > _CLAIM_TTL_S:
            _ACTIVE_JOB.claimed_by = ""
            _ACTIVE_JOB.claimed_ts = 0.0

        claimed_by = _ACTIVE_JOB.claimed_by

        return {
            "ok": True,
            "active": True,
            "token": _ACTIVE_JOB.token,
            "mode": _ACTIVE_JOB.mode,
            "label": _ACTIVE_JOB.label,
            "expires_in_s": max(0.0, _ACTIVE_JOB.expires_ts - now),
            "claimed_by": claimed_by,
            "claimed": bool(claimed_by),
            "claimed_by_me": bool(phone_id and claimed_by == phone_id),
        }


def claim_active_job(phone_id: str) -> dict:
    global _ACTIVE_JOB
    phone_id = (phone_id or "").strip()
    if not phone_id:
        return {"ok": False, "error": "missing_phone_id"}

    now = time.time()

    with _ACTIVE_LOCK:
        # If no active job, return inactive
        if _ACTIVE_JOB is None or now > _ACTIVE_JOB.expires_ts:
            _ACTIVE_JOB = None
            return {"ok": True, "active": False, "can_scan": False}

        # expire claim if too old
        if _ACTIVE_JOB.claimed_by and (now - float(_ACTIVE_JOB.claimed_ts or 0.0)) > _CLAIM_TTL_S:
            _ACTIVE_JOB.claimed_by = ""
            _ACTIVE_JOB.claimed_ts = 0.0

        # Claim if unclaimed
        if not _ACTIVE_JOB.claimed_by:
            _ACTIVE_JOB.claimed_by = phone_id
            _ACTIVE_JOB.claimed_ts = now

        # Refresh TTL if already claimed by me
        if _ACTIVE_JOB.claimed_by == phone_id:
            _ACTIVE_JOB.claimed_ts = now

        can_scan = (_ACTIVE_JOB.claimed_by == phone_id)

        return {
            **get_active_job_status(phone_id=phone_id),
            "can_scan": can_scan,
        }


def release_active_job(phone_id: str) -> dict:
    global _ACTIVE_JOB
    phone_id = (phone_id or "").strip()

    with _ACTIVE_LOCK:
        if _ACTIVE_JOB and _ACTIVE_JOB.claimed_by == phone_id:
            _ACTIVE_JOB.claimed_by = ""
            _ACTIVE_JOB.claimed_ts = 0.0

    return get_active_job_status(phone_id=phone_id)






def new_scan_session(*, mode: str, ttl_s: float = _DEFAULT_TTL_S) -> ScanSession:
    token = secrets.token_urlsafe(24)
    now = time.time()
    sess = ScanSession(
        token=token,
        created_ts=now,
        expires_ts=now + float(ttl_s),
        mode=(mode or "component_type").strip().lower(),
    )
    with _SESS_LOCK:
        _SESSIONS[token] = sess
    return sess


def get_scan_session(token: str) -> Optional[ScanSession]:
    token = (token or "").strip()
    if not token:
        return None

    with _SESS_LOCK:
        sess = _SESSIONS.get(token)
        if not sess:
            return None
        if time.time() > sess.expires_ts:
            _SESSIONS.pop(token, None)
            return None
        return sess

def cancel_scan_session(token: str) -> bool:
    """
    Cancel a scan session token (removes it).
    Returns True if it existed (or already expired), False if token missing.
    """
    token = (token or "").strip()
    if not token:
        return False

    with _SESS_LOCK:
        sess = _SESSIONS.pop(token, None)
        return bool(sess)

    
def set_scan_result(token: str, *, raw_text: str, remote_addr: str = "") -> Optional[ScanSession]:
    token = (token or "").strip()
    if not token:
        return None

    with _SESS_LOCK:
        sess = _SESSIONS.get(token)
        if not sess:
            return None
        if time.time() > sess.expires_ts:
            _SESSIONS.pop(token, None)
            return None
        if sess.used:
            return sess

        sess.raw_text = (raw_text or "").strip()
        sess.extracted = extract_mode_value(sess.raw_text, sess.mode)
        sess.remote_addr = (remote_addr or "").strip()
        sess.used = True
        return sess


def get_scan_status(token: str) -> Dict[str, Any]:
    sess = get_scan_session(token)
    if not sess:
        return {"ok": False, "error": "invalid_or_expired"}
    return {
        "ok": True,
        "token": sess.token,
        "mode": sess.mode,
        "used": bool(sess.used),
        "raw_text": sess.raw_text,
        "extracted": sess.extracted,
        "expires_in_s": max(0.0, sess.expires_ts - time.time()),
        "remote_addr": sess.remote_addr,
    }


def cleanup_sessions() -> None:
    now = time.time()
    with _SESS_LOCK:
        dead = [k for k, s in _SESSIONS.items() if now > s.expires_ts]
        for k in dead:
            _SESSIONS.pop(k, None)



        
# ----------------------------
# Security helpers
# ----------------------------
def is_private_or_local_ip(ip: str) -> bool:
    try:
        ip = (ip or "").split("%", 1)[0].strip()   # strip zone id if any
        if ip.startswith("::ffff:"):
            ip = ip.split("::ffff:", 1)[1]         # unwrap mapped v4
        if ip in ("::1",):
            return True
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback
    except Exception:
        return False

    
