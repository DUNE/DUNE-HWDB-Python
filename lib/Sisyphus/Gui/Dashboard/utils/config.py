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
        



# ============================================
# Experimental Hierarchy Chart tab
# ============================================
# Default is OFF so the test tab does not appear in normal releases.
# Enable with either:
#     export HWDB_ENABLE_HIERARCHY_CHART_TAB=1
# or the older/backward-compatible:
#     export HWDB_ENABLE_FDVD_TAB=1
_ENABLE_HIERARCHY_ENV = os.getenv("HWDB_ENABLE_HIERARCHY_CHART_TAB", "").strip().lower()
_ENABLE_FDVD_ENV = os.getenv("HWDB_ENABLE_FDVD_TAB", "").strip().lower()

ENABLE_HIERARCHY_CHART_TAB = (
    _ENABLE_HIERARCHY_ENV in ("1", "true", "yes", "on")
    or _ENABLE_FDVD_ENV in ("1", "true", "yes", "on")
)

# Backward-compatible alias used by older layout_main.py / __main__.py imports.
ENABLE_FDVD_TAB = ENABLE_HIERARCHY_CHART_TAB


def get_active_profile_name(default: str = "development") -> str:
    """Return the current Sisyphus profile name, with a safe fallback."""
    try:
        return str(config.config_data.get("active profile") or default)
    except Exception:
        return default


def normalize_hierarchy_chart_kind(chart_kind: str | None = None) -> str:
    """
    Normalize chart names.

    fdvd / FD-VD / vd -> fdvd
    fdhd / FD-HD / hd -> fdhd
    """
    s = str(chart_kind or "fdvd").strip().lower().replace("_", "-")
    if s in ("fd-hd", "fdhd", "hd"):
        return "fdhd"
    return "fdvd"


def get_hierarchy_json_path(chart_kind: str | None = None) -> str:
    """
    User-editable Hierarchy Chart JSON path for the active profile.

    FD-VD:
        ~/.sisyphus/<profile>/fdvd_layout.json

    FD-HD:
        ~/.sisyphus/<profile>/fdhd_layout.json
    """
    profile = get_active_profile_name()
    kind = normalize_hierarchy_chart_kind(chart_kind)
    filename = "fdhd_layout.json" if kind == "fdhd" else "fdvd_layout.json"
    return str(os.path.expanduser(os.path.join("~", ".sisyphus", profile, filename)))


def get_fdvd_json_path() -> str:
    """Backward-compatible FD-VD diagram JSON path for the active profile."""
    return get_hierarchy_json_path("fdvd")


def get_fdhd_json_path() -> str:
    """FD-HD diagram JSON path for the active profile."""
    return get_hierarchy_json_path("fdhd")
