APP_VERSION = "v0.9.2"

# Sisyphus
from Sisyphus.Configuration import config
from Sisyphus.Configuration import config, RESTAPI_PROD, RESTAPI_DEV

logger = config.getLogger(__name__)

import os
import sys
import warnings
import time
import threading
import multiprocessing.resource_tracker as rt

# Suppress resource tracker and deprecation warnings globally
warnings.filterwarnings("ignore", category=DeprecationWarning)
rt._resource_tracker._warn = lambda *a, **kw: None

# ============================================
# HWDB profile switcher (replaces restart)
# ============================================
def switch_profile(profile_name: str, persist: bool = True):
    """
    Switch HWDB profile both in memory and optionally persist it to disk.

    Parameters
    ----------
    profile_name : str
        Either "production" or "development".
    persist : bool
        If True, also update ~/.sisyphus/config.json permanently.
    """
    if profile_name not in ("production", "development"):
        raise ValueError("profile_name must be 'production' or 'development'")

    # Update the active profile name
    config.config_data["active profile"] = profile_name

    # Adjust its REST API endpoint
    if profile_name == "production":
        config.active_profile.profile_data["rest api"] = RESTAPI_PROD
    else:
        config.active_profile.profile_data["rest api"] = RESTAPI_DEV

    # Save to disk if requested
    if persist:
        config.save()
        logger.info(f"✅ Switched to {profile_name} and updated ~/.sisyphus/config.json")
    else:
        logger.info(f"⚡ Temporarily switched to {profile_name} (no file saved)")
        
def restart(silent: bool = True, delay: float = 0.5):
    """
    Safely restart the current Dashboard module.

    Parameters
    ----------
    silent : bool
        If True, suppresses terminal output (default True)
    delay : float
        Delay in seconds before restarting to let UI callbacks settle
    """

    now = time.time()
    if now - _last_restart_time[0] < 3:
        # Prevent accidental double restart (e.g. double-click)
        return
    _last_restart_time[0] = now

    if not silent:
        logger.info(f"[Dashboard] Restarting in {delay:.1f} sec...")
        logger.info(sys.executable, "-m", "Sisyphus.Gui.Dashboard")

    # Use a background thread so Dash callback can finish returning before quit
    def _delayed_restart():
        time.sleep(delay)
        #os.execv(sys.executable, [sys.executable, "-m", "Sisyphus.Gui.Dashboard"])
        import subprocess
        subprocess.Popen(
            [sys.executable, "-m", "Sisyphus.Gui.Dashboard"],
            close_fds=True,
            stdout=None if silent else sys.stdout,
            stderr=None if silent else sys.stderr,
        )
        os._exit(0)  # ensure current process quits immediately

    threading.Thread(target=_delayed_restart, daemon=True).start()

