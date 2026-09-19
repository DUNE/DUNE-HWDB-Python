#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""
from pathlib import Path

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus.Configuration as cfg # for config's keywords and exceptions

from .exceptions import *
from .keywords import *

import threading
import requests

from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Utils.Terminal.BoxDraw import MessageBox
import sys

from copy import copy

import subprocess
import os

import shutil
import re
import certifi

###############################################################################

# module globals
_AUTH_OPEN_LOCK = threading.Lock()
_LAST_AUTH_OPEN_TS = 0.0
_LAST_AUTH_OPEN_URL = None

# If True: we open the auth URL ourselves (throttled) and DO NOT ask htgettoken to auto-open.
# If False: we let htgettoken auto-open via --web-open-command (when available).
USE_INTERNAL_BROWSER_OPEN = True

# Latch "interactive auth pending" so we don't spawn new device codes repeatedly!!
_AUTH_PENDING_LOCK = threading.Lock()
_AUTH_PENDING_UNTIL = 0.0
_AUTH_PENDING_URL = None


# ----------------------------
# HTTP timeout defaults
# ----------------------------
# Requests timeout format:
#   timeout=<seconds> or timeout=(connect_timeout, read_timeout)
DEFAULT_HTTP_TIMEOUT = (10, 60)

class ProfileManager:
    def __init__(self, profile):
        logger.debug(f"STARTING ProfileManager.__init__ profile={profile.profile_name}")
        self.profile = profile
        self.lock = threading.RLock()

        if self.profile.authentication[cfg.KW_AUTH_TYPE] == cfg.KW_AUTH_CERT:
            logger.debug(f"{profile.profile_name} is using certificates.")
            return

        self.bearer_token = self.load_token()

        if _jwt_is_expired(self.bearer_token):
            self.bearer_token = None
            self.refresh(force=True)

        if self.bearer_token is None:
            # The file was empty. We need to refresh so the file can be
            # created and re-read
            self.refresh()
        
        logger.debug("FINISHED ProfileManager.__init__ profile={profile.profile_name}")


    #def refresh(self):
    #    # We need the old_bearer_token so we can see if the ProfileManager
    #    # has already been refreshed, by comparing the old to the new.
    #    old_bearer_token = self.bearer_token
    #
    #    with self.lock:
    #        if self.bearer_token == old_bearer_token:
    #            # If they're the same, it means that it hasn't been refreshed
    #            # yet, so we need to do it.
    #
    #            # Do Refresh Action
    #            refresh_token(self.profile)
    #
    #            # Reload
    #            self.bearer_token = self.load_token()
    #
    #        if self.bearer_token is None:
    #            raise RestApiException("Unable to obtain bearer token")
    def refresh(self, force: bool = False):
        """
        Refresh bearer token using htgettoken.
        - force=True refreshes even if a bearer token exists (e.g., expired token)
        - Only one thread performs refresh; others wait.
        """
        if not hasattr(self, "_refresh_cv"):
            self._refresh_cv = threading.Condition(self.lock)
            self._refresh_in_progress = False
            self._last_refresh_error = None
            self._last_refresh_end_ts = 0.0

        def _reload_or_none():
            self.bearer_token = self.load_token()
            return self.bearer_token

        with self.lock:
            while self._refresh_in_progress:
                self._refresh_cv.wait(timeout=30.0)

            # If not forcing, and current token is valid, do nothing.
            if not force and self.bearer_token and not _jwt_is_expired(self.bearer_token):
                return

            # If interactive auth is pending, don't spawn another htgettoken flow
            pending_until, pending_url = _auth_pending_get()
            if time.time() < pending_until:
                tok = _reload_or_none()
                if tok and not _jwt_is_expired(tok):
                    _auth_pending_clear()
                    return
                # Re-open the same URL, but throttled heavily (or just log it)
                #if pending_url:
                #    _open_auth_url_throttled(pending_url, cooldown_s=300.0)  # 5 min
                raise AuthenticationError(
                    f"Authentication is still pending. Please complete sign-in in the browser. URL: {pending_url}"
                )

            
            # Mark refresh in progress
            self._refresh_in_progress = True
            self._last_refresh_error = None

        opened_url_value = None
        err = None
        try:
            #refresh_token(self.profile)  # uses vault token; should be non-interactive if vault is valid
            opened_url_value = refresh_token(self.profile)
        except Exception as e:
            err = e

        with self.lock:
            tok = _reload_or_none()
            self._last_refresh_end_ts = time.time()
            if err is not None:
                self._last_refresh_error = err

            self._refresh_in_progress = False
            self._refresh_cv.notify_all()

            if tok and not _jwt_is_expired(tok):
                _auth_pending_clear()
                return

            # Latch auth pending so we don't generate more device codes
            # If refresh_token opened a URL, store that; otherwise leave None.
            # The solution: Have refresh_token return opened_url_value (see below).
            if opened_url_value:
                _auth_pending_set(opened_url_value, ttl_s=1800.0)


            
            if self._last_refresh_error is not None:
                raise self._last_refresh_error
            raise RestApiException("Unable to obtain bearer token")


    def load_token(self):
        try:
            txt = Path(self.profile.bearer_token_file).read_text().strip()
            return txt or None
        except FileNotFoundError:
            return None
        #try:
        #    with open(self.profile.bearer_token_file, 'r') as fp:
        #        return fp.read().strip()
        #except FileNotFoundError as err:
        #    return None



class SessionManager:
    '''handles requests.Session objects on a per-thread & per-profile basis'''
    #
    # Explanation of the RestApiSession class
    # =======================================
    # RestApi calls will always try to grab a RestApiSession before making the
    # request. The big trick that RestApiSession must do is decide whether it 
    # should create a new Session (from the requests library) or return an 
    # existing one.
    #
    # Python docs suggest that multiple threads should not share the same
    # Session object, so the rule will be that each thread should have its own
    # RestApiSession. It is also possible for the same thread to try using
    # more than one config profile (which defines which RestApi server to 
    # connect to), so we have to use (thread_id, profile) as the unique key.
    #
    # We also need a mechanism to invalidate sessions once any request using
    # the same profile hits a "signature expired" from the server. To be
    # clear, this means that if one thread using profile "A" hits a 
    # "signature expired," then *all* threads using profile "A" must be
    # invalidated. However, only *one* of them should to refresh htgettoken.
    # The rest of them should be locked out until the refresh is complete.
    # Then, they can pick up the new bearer token and continue.
    #
    # =========================================================================

    _cached_sessions = {}
    _profile_managers = {}

    # Since _profile_managers is shared by multiple sessions which may be on 
    # multiple threads, we must make sure to lock other threads out whenever
    # operating on a node in _profile_managers
    _profile_lock = threading.RLock()

    def __new__(cls, profile):
        # There's sort of an implied "thread" parameter here, but we can get
        # that from the current thread
        current_thread = threading.current_thread()

        # The session_key uniquely defines the RestApiSession in the cache.
        # Note that we don't need to worry about multiple threads trying to
        # work with the same RestApiSession at the same time, because by
        # definition, each RestApiSession is tied to exactly one thread.
        session_key = (current_thread, profile.profile_name)

        if session_key in cls._cached_sessions:
            return cls._cached_sessions[session_key]
        else:
            new_obj = super().__new__(cls)
            cls._cached_sessions[session_key] = new_obj
            return new_obj

    def __init__(self, profile):

        if getattr(self, '_initialized', False):
            return

        self.current_thread = threading.current_thread()
        self.profile = profile
        self.session_key = (self.current_thread, self.profile.profile_name)

        # Create the requests.Session object
        self._session = requests.Session()

        # Default timeout used by our REST wrapper when caller doesn't provide one.
        # (requests.Session itself doesn't enforce default timeouts)
        self.default_timeout = DEFAULT_HTTP_TIMEOUT
        
        adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
        self._session.mount(f'https://{self.profile.rest_api}', adapter)

        # Handle "certificate" case
        if self.profile.authentication[cfg.KW_AUTH_TYPE] == cfg.KW_AUTH_CERT:
            self._session.cert = self.profile.authentication[cfg.KW_CERTIFICATE]

        # Handle "htgettoken" case
        elif self.profile.authentication[cfg.KW_AUTH_TYPE] == cfg.KW_AUTH_HTGETTOKEN:
            self._last_bearer_token = None

        # No authorization set in configuration!
        else:
            raise cfg.ConfigurationError(f"profile {self.profile.profile_name!r} "
                    "has an invalid or missing authentication type.")

        self._initialized = True

    @property
    def session(self):
        if self.profile.authentication[cfg.KW_AUTH_TYPE] == cfg.KW_CERTIFICATE:
            # Since certificates don't expire frequently like htgettoken tokens
            # do, just return the session object with no worries
            return self._session
        
        if self.bearer_token != self._last_bearer_token:
            # The bearer token has changed, so update session headers!
            self._session.headers.update({
                'Authorization': f"Bearer {self.bearer_token}"
            })
            
            self._last_bearer_token = self.bearer_token
        return self._session
                

    #@property
    #def profile_manager(self):
    #    # Lock all profile data so that if a new profile needs to be created,
    #    # only one thread will do the creating.
    #    with self.__class__._profile_lock:
    #        profile_manager = self.__class__._profile_managers.get(self.profile.profile_name, None)
    #        if profile_manager is None:
    #            # we need to create it
    #            profile_manager = ProfileManager(self.profile)
    #            self.__class__._profile_managers[self.profile.profile_name] = profile_manager
    #        
    #        return profile_manager
    @property
    def profile_manager(self):
        with self.__class__._profile_lock:
            mgr = self.__class__._profile_managers.get(self.profile.profile_name)
            if mgr is None:
                mgr = ProfileManager(self.profile)
                self.__class__._profile_managers[self.profile.profile_name] = mgr
            return mgr

    @property
    def bearer_token(self):
        with self.__class__._profile_lock:
            mgr = self.profile_manager
            return mgr.bearer_token
            

class output_so_far:
    #{{{
    def __init__(self, fp):
        self.fp = fp

        self.buffer = bytes()
        self.closed = False
        self.lock = threading.Lock()
        self.read_thread = threading.Thread(target=self._worker_task, daemon=True)
        self.read_thread.start()

    def _worker_task(self):
        while True:
            ch = self.fp.readline()
            if ch == b'':
                break
            with self.lock:
                self.buffer += ch
        self.closed = True

    def read(self):
        with self.lock:
            return copy(self.buffer)

    def read_all(self):
        self.read_thread.join()
        return copy(self.buffer)
        failed = False
        try:
            outs, errs = proc.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            outs, errs = proc.communicate()
    #}}}

    
# A helper to run the frozen version:
def _tool_exe(name: str) -> str:
    """
    Return the absolute path to a sibling hwdb-* tool when frozen.
    In non-frozen mode, return just the name and let PATH resolve it.
    """
    if getattr(sys, "frozen", False):
        # In onedir, sys.executable is .../HWDBTools/hwdb-configure
        return str(Path(sys.executable).resolve().parent / name)
    return name

# Helpers for the WSL (2) case:
def _is_wsl() -> bool:
    # Fast path: env vars that are usually present
    if os.environ.get("WSL_INTEROP") or os.environ.get("WSL_DISTRO_NAME"):
        return True

    # Fallback: /proc/version contains Microsoft
    try:
        with open("/proc/version", "r") as fp:
            return "microsoft" in fp.read().lower()
    except Exception:
        return False

def _pick_web_open_command() -> str | None:
    """
    Return a command string suitable for htgettoken --web-open-command=...

    Policy:
      - WSL: do auto-launch via Windows (wslview/explorer/cmd start), because user is local.
      - macOS: do auto-launch via 'open'.
      - Linux (non-WSL): DO NOT auto-launch by default (often remote/headless).
    """
    if _is_wsl():
        if shutil.which("wslview"):
            return "wslview"
        if shutil.which("explorer.exe"):
            return "explorer.exe"
        if shutil.which("cmd.exe"):
            return 'cmd.exe /c start ""'
        # last resort inside WSL (sometimes present)
        if shutil.which("xdg-open"):
            return "xdg-open"
        return None

    if sys.platform == "darwin":
        return "open"

    # Linux (non-WSL): assume remote/headless -> don't try to open a browser!
    # Well.. actually let's do this by ourselves. This is needed when we run Dashboard...
    if sys.platform.startswith("linux"):
        if (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) and shutil.which("xdg-open"):
            return "xdg-open"
        return None

    # other unix-like: fallback
    if shutil.which("xdg-open"):
        return "xdg-open"
    return None

import time
import shlex

_URL_RE = re.compile(r"(https?://\S+)")

def _extract_first_url(text: str) -> str | None:
    m = _URL_RE.search(text or "")
    if not m:
        return None
    # trim trailing punctuation that sometimes sticks to URLs
    return m.group(1).rstrip(").,;")

def _open_url_best_effort(url: str) -> bool:
    """
    Best-effort open a URL on the *user's* machine!!!! or at least trying to...
    - WSL: prefer cmd.exe start (most reliable), then wslview, then explorer.exe
    - macOS: open
    - Linux: xdg-open
    Returns True if we successfully launched a command (not if browser actually rendered).
    """
    try:
        if _is_wsl():
            # Most reliable in WSL is cmd.exe /c start "" "<url>"
            if shutil.which("cmd.exe"):
                try:
                    subprocess.Popen(["cmd.exe", "/c", "start", "", url],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                    return True
                except Exception:
                    pass

            # Next: wslview (if present)
            if shutil.which("wslview"):
                try:
                    subprocess.Popen(["wslview", url],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                    return True
                except Exception:
                    pass

            # Fallback: explorer.exe
            if shutil.which("explorer.exe"):
                try:
                    subprocess.Popen(["explorer.exe", url],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                    return True
                except Exception:
                    pass

            return False

        if sys.platform == "darwin":
            subprocess.Popen(["open", url],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            return True


        if sys.platform.startswith("linux"):
            # Only try auto-open if a GUI session exists
            has_gui = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
            if not has_gui:
                return False

            if shutil.which("xdg-open"):
                try:
                    subprocess.Popen(
                        ["xdg-open", url],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
                except Exception:
                    return False
            return False

        # Other platforms
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", url],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            return True
        return False

    except Exception:
        return False

def _print_auth_url_once(url: str):
    """
    Always print the auth URL to terminal (stdout) once per process.
    This is important for remote/headless users who can't see auto-opened tabs.
    """
    global _LAST_AUTH_OPEN_URL, _LAST_AUTH_OPEN_TS
    now = time.time()
    with _AUTH_OPEN_LOCK:
        if _LAST_AUTH_OPEN_URL == url:
            return
        _LAST_AUTH_OPEN_URL = url
        _LAST_AUTH_OPEN_TS = now

    # Plain print so it shows even if logger isn't configured to console
    print(f"\n[htgettoken] Authentication URL (copy/paste in a browser): {url}\n", flush=True)

    
#-------------
import base64
import json
import time

def _jwt_is_expired(token: str | None, *, leeway_s: int = 30) -> bool:
    """
    Check JWT exp claim without verifying signature.
    Returns True if missing/invalid/expired/near-expired.
    """
    if not token:
        return True
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return True
        payload_b64 = parts[1]
        # base64url padding
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")))
        exp = int(payload.get("exp", 0))
        return time.time() >= (exp - leeway_s)
    except Exception:
        # if not possible to parse it, treat it as unusable
        return True

def _open_auth_url_throttled(url: str, *, cooldown_s: float = 60.0) -> bool:
    global _LAST_AUTH_OPEN_TS, _LAST_AUTH_OPEN_URL
    now = time.time()
    with _AUTH_OPEN_LOCK:
        # same URL already opened recently
        if _LAST_AUTH_OPEN_URL == url and (now - _LAST_AUTH_OPEN_TS) < cooldown_s:
            return False
        # any URL opened recently (prevents tab storms with new device codes)
        if (now - _LAST_AUTH_OPEN_TS) < cooldown_s:
            return False

        ok = _open_url_best_effort(url)
        _LAST_AUTH_OPEN_TS = now
        _LAST_AUTH_OPEN_URL = url
        return ok

def _auth_pending_get():
    with _AUTH_PENDING_LOCK:
        return _AUTH_PENDING_UNTIL, _AUTH_PENDING_URL

def _auth_pending_set(url: str | None, *, ttl_s: float):
    with _AUTH_PENDING_LOCK:
        global _AUTH_PENDING_UNTIL, _AUTH_PENDING_URL
        _AUTH_PENDING_UNTIL = time.time() + ttl_s
        _AUTH_PENDING_URL = url

def _auth_pending_clear():
    """
    Clear the 'interactive auth pending' latch.
    Call this once a valid (non-expired) bearer token is observed.
    """
    with _AUTH_PENDING_LOCK:
        global _AUTH_PENDING_UNTIL, _AUTH_PENDING_URL
        _AUTH_PENDING_UNTIL = 0.0
        _AUTH_PENDING_URL = None
        
def refresh_token(profile) -> str | None:
    """
    Run hwdb-htgettoken to refresh bearer token.

    Returns:
        opened_url_value (str|None): the first device-auth URL observed in htgettoken output,
        or None if no URL was observed (e.g. vault token was valid and refresh was non-interactive).
    """

    def create_proc(verbose: bool = False):
        config_dir = profile.profile_dir
        vault_token_file = profile.vault_token_file
        bearer_token_file = profile.bearer_token_file

        tokens = [
            _tool_exe("hwdb-htgettoken"),
            ("-v" if verbose else "-q"),
            f"--configdir={config_dir}",
            f"--vaulttokenfile={vault_token_file}",
            f"--outfile={bearer_token_file}",
            "--vaultserver=htvaultprod.fnal.gov",
            "--issuer=fermilab",
        ]


        # optional web-open-command:
        # If we're handling browser opening ourselves, DO NOT tell htgettoken to open
        # (prevents double-tabs on macOS and other platforms).
        if not USE_INTERNAL_BROWSER_OPEN:
            web_open_cmd = _pick_web_open_command()
            if web_open_cmd:
                tokens.append(f"--web-open-command={web_open_cmd}")

        tokens.extend(profile.authentication.get("flags", []))

        logger.info(f"[htgettoken] running: {' '.join(tokens)}")

        # Make sure frozen/non-frozen runs both pass an explicit CA bundle
        # down to htgettoken / requests / OpenSSL.
        env = os.environ.copy()
        ca_bundle = certifi.where()
        env.setdefault("SSL_CERT_FILE", ca_bundle)
        env.setdefault("REQUESTS_CA_BUNDLE", ca_bundle)

        logger.info(f"[htgettoken] SSL_CERT_FILE={env.get('SSL_CERT_FILE')}")
        logger.info(f"[htgettoken] REQUESTS_CA_BUNDLE={env.get('REQUESTS_CA_BUNDLE')}")
        logger.info(f"[htgettoken] ca_bundle={ca_bundle} exists={os.path.exists(ca_bundle)}")

        try:
            return subprocess.Popen(
                tokens,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError:
            msg = ("htgettoken not found. Have you installed it? "
                   "(try 'pip install htgettoken')")
            logger.error(msg)
            Style.error.print(msg)
            raise

    logger.warning("Refreshing tokens")

    proc = create_proc(verbose=False)
    osf_stdout = output_so_far(proc.stdout)
    osf_stderr = output_so_far(proc.stderr)

    interval = 2          # poll faster so we catch the URL quickly
    total_time = 0
    max_time = 120        # normal max
    max_time_auth = 1800  # if auth URL appears, allow longer for user to complete

    last_stdout = ""
    last_stderr = ""

    opened_url_value: str | None = None
    opened_auth_url = False

    timed_out = False
    while True:
        try:
            proc.wait(interval)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True

        if not timed_out:
            break

        total_time += interval
        if total_time >= max_time:
            break

        current_stdout = osf_stdout.read().decode("utf-8", errors="replace")
        current_stderr = osf_stderr.read().decode("utf-8", errors="replace")

        # detect URL once and optionally open once (throttled)
        if not opened_auth_url:
            url = _extract_first_url(current_stdout) or _extract_first_url(current_stderr)
            if url:
                opened_url_value = url
                opened_auth_url = True

                logger.info(f"[htgettoken] authentication URL: {url}")
                _print_auth_url_once(url)  # always show in terminal

                # If we are responsible for opening the browser, do it ONCE (throttled)
                if USE_INTERNAL_BROWSER_OPEN:
                    ok = _open_auth_url_throttled(url, cooldown_s=1800.0)
                    if ok:
                        logger.info(f"[htgettoken] opened authentication URL via OS hook: {url}")
                    else:
                        logger.info(f"[htgettoken] authentication URL (not auto-opened): {url}")
                        print(
                            "\n[htgettoken] NOTE: Auto-open failed on this system.\n"
                            "Please copy/paste the URL above into a browser to authenticate.\n",
                            flush=True,
                        )

                # Latch pending auth immediately to prevent other threads spawning htgettoken
                _auth_pending_set(url, ttl_s=1800.0)

                # Give user time to complete interactive flow
                max_time = max_time_auth
            
        # optional: your display_message logic can go here if you want
        if current_stdout != last_stdout:
            # display_message(current_stdout, total_time)  # if you kept it
            last_stdout = current_stdout
        if current_stderr != last_stderr:
            # display_message(current_stderr, total_time)  # if you kept it
            last_stderr = current_stderr

    if timed_out:
        proc.kill()

    current_stdout = osf_stdout.read_all().decode("utf-8", errors="replace")
    current_stderr = osf_stderr.read_all().decode("utf-8", errors="replace")

    if proc.returncode is None:
        logger.error(f"htgettoken timed out. stdout:\n{current_stdout}\nstderr:\n{current_stderr}")
        raise AuthenticationError("The call to htgettoken timed out.")

    if proc.returncode != 0:
        logger.error("htgettoken failed in quiet mode; re-running once with -v to capture diagnostics.")
        proc2 = create_proc(verbose=True)
        outs2, errs2 = proc2.communicate()
        outs2 = (outs2 or b"").decode("utf-8", errors="replace")
        errs2 = (errs2 or b"").decode("utf-8", errors="replace")

        logger.error(
            "The call to htgettoken failed.\n"
            f"[quiet] rc={proc.returncode}\n"
            f"[quiet] stdout:\n{current_stdout}\n"
            f"[quiet] stderr:\n{current_stderr}\n"
            f"[verbose] rc={proc2.returncode}\n"
            f"[verbose] stdout:\n{outs2}\n"
            f"[verbose] stderr:\n{errs2}\n"
        )
        raise AuthenticationError("The call to htgettoken failed.")

    logger.info("The call to htgettoken succeeded.")
    return opened_url_value

   
if __name__ == "__main__":
    print("DEVELOPMENT")
    dev_session = SessionManager(config.get_profile("development"))
    print(f"{dev_session.session.headers}")


    print('\n\n')


    print("PRODUCTION")
    prod_session = SessionManager(config.get_profile("production"))
    print(f"{prod_session.session.headers}")


    print('\n\n')
