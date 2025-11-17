try:
    # Import version from top-level Sisyphus package
    from Sisyphus import version as SISYPHUS_VERSION
    APP_VERSION = SISYPHUS_VERSION
except Exception:
    APP_VERSION = "v?.?.?"  # fallback if not found



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
        

