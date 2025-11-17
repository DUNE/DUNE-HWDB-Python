from dash import Input, Output, State, ctx, no_update, html, dash_table
import dash
import pandas as pd
from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.RestApiV1 import get_projects, get_systems, get_subsystems, get_component_types

import copy, time
from datetime import datetime
from copy import deepcopy


def _safe_id_key(entry):
    """Return a lowercase string version of the 'id' for sorting, safely handling int/None."""
    v = entry.get("id")
    if v is None:
        return (1e9, "")  # push None to the end
    s = str(v).strip()
    # Try to convert to a number
    if s.replace(".", "", 1).isdigit():
        return (0, float(s))
    return (1, s.lower())

def _fetch_projects():
    """Return list of dicts: [{id: "...", name: "..."}]"""

    try:
        resp = get_projects()
        resp = resp["data"]
        if not isinstance(resp, list):
            logger.warning(f"[TypeGetter] get_projects() returned unexpected type: {type(resp)}")
            return []
        # Keep only 'id' and 'name' keys
        projects = [
            {"id": r.get("id"), "name": r.get("name")}
            for r in resp if isinstance(r, dict)
        ]
        # Sort alphabetically by ID (case-insensitive)
        projects = sorted(projects, key=_safe_id_key)
        
        logger.info(f"[TypeGetter] _fetch_projects got {len(projects)} projects from HWDB")
        return projects

    except Exception as e:
        logger.error(f"[TypeGetter] _fetch_projects failed: {e}")
        return []

def _fetch_systems(project_id: str):
    """Return [{id, name}] for a given project"""
    try:
        resp = get_systems(project_id)
        resp = resp["data"]
        if not isinstance(resp, list):
            logger.warning(f"[TypeGetter] get_systems() returned unexpected type: {type(resp)}")
            return []
        # Keep only 'id' and 'name' keys
        systems = [
            {"id": r.get("id"), "name": r.get("name")}
            for r in resp if isinstance(r, dict)
        ]
        # Sort alphabetically by ID (case-insensitive)
        systems = sorted(systems, key=_safe_id_key)

        logger.info(f"[TypeGetter] _fetch_systems got {len(systems)} systems from HWDB")
        return systems

    except Exception as e:
        logger.error(f"[TypeGetter] _fetch_systems failed: {e}")
        return []


def _fetch_subsystems(project_id: str, system_id: int):
    """Return [{id, name}] for a given project and system."""
    try:
        resp = get_subsystems(project_id, system_id)
        logger.info(f"[TypeGetter] get_subsystems({project_id}, {system_id}) returned type={type(resp)}")

        # Handle both dict and list formats
        if isinstance(resp, dict):
            data = resp.get("data", [])
        elif isinstance(resp, list):
            data = resp
        else:
            logger.warning(f"[TypeGetter] Unexpected response type from get_subsystems: {type(resp)}")
            return []

        # Defensive log for debugging
        logger.info(f"[TypeGetter] _fetch_subsystems raw count = {len(data)}")

        # Ensure all items are dicts and extract relevant fields
        subsystems = [
            {"id": r.get("subsystem_id"), "name": r.get("subsystem_name")}
            for r in data if isinstance(r, dict)
        ]

        # --- sort naturally by ID (numeric-aware) ---
        subsystems = sorted(subsystems, key=_safe_id_key)

        logger.info(f"[TypeGetter] _fetch_subsystems got {len(subsystems)} subsystems for system {system_id}")
        
        return subsystems

    except Exception as e:
        logger.error(f"[TypeGetter] _fetch_subsystems failed: {e}")
        return []

def _fetch_types(project_id: str, system_id: int, subsystem_id: int):
    """Return [{id, name}] for a given subsystem"""
    try:
        resp = get_component_types(project_id, system_id, subsystem_id, size=99999)
        logger.info(f"[TypeGetter] get_component_types({project_id}, {system_id}, {subsystem_id}, size=99999) returned type={type(resp)}")

        # Handle both dict and list formats
        if isinstance(resp, dict):
            data = resp.get("data", [])
        elif isinstance(resp, list):
            data = resp
        else:
            logger.warning(f"[TypeGetter] Unexpected response type from get_component_types: {type(resp)}")
            return []

        # Defensive log for debugging
        logger.info(f"[TypeGetter] _fetch_types raw count = {len(data)}")

        # Ensure all items are dicts and extract relevant fields
        types = [
            {"id": r.get("part_type_id"), "name": r.get("full_name")}
            for r in data if isinstance(r, dict)
        ]

        # --- sort naturally by ID (numeric-aware) ---
        types = sorted(types, key=_safe_id_key)

        logger.info(f"[TypeGetter] _fetch_types got {len(types)} types for subsystem {subsystem_id}")
        
        return types

    except Exception as e:
        logger.error(f"[TypeGetter] _fetch_types failed: {e}")
        return []



def _init_cache(cache):
    """Normalize the cache structure. Always return a dict with the expected keys."""
    """Ensure cache always has the expected keys, preserving existing data."""
    if not isinstance(cache, dict):
        cache = {}
    return {
        "projects": cache.get("projects"),
        "systems": cache.get("systems", {}),
        "subsystems": cache.get("subsystems", {}),
        "types": cache.get("types", {}),
    }

# ---------------------------
# Sync buttons - feedback
# ---------------------------



def register_typegetter_callbacks(app):

    # ---- slide animation (translateX) ----
    @app.callback(
        Output("tg-pages", "style"),
        Input("tg-current-level", "data"),
    )
    def _slide(level_data):
       
        # Accept both plain strings and dicts with {'level': ..., 'count': ...}
        if isinstance(level_data, dict):
            level = level_data.get("level")
        else:
            level = level_data
        
        logger.info(f"[TypeGetter] slide level={level}")

        logger.info(f"[DEBUG] _slide() currently displaying level={level}")
        
        # Default to projects (0%) if missing or invalid
        if level not in ("projects", "systems", "subsystems", "types"):
            level = "projects"

        offsets = {"projects": 0, "systems": -100, "subsystems": -200, "types": -300}
        x = offsets[level]
        
        return {
            "transform": f"translateX({x}%)",
            "display": "flex",
            "transition": "transform 0.35s ease-in-out",
            "width": "400%",
            "overflow": "hidden",
        }

    # ---- breadcrumb-ish text ----
    @app.callback(
        Output("tg-crumbs", "children"),
        Input("tg-selected", "data"),
    )
    def _crumbs(sel):
       
        mystring=""
        if sel.get("project") and sel.get("project_name") and \
            sel.get("system") and sel.get("system_name") and \
            sel.get("subsystem") and sel.get("subsystem_name") and \
            sel.get("type") and sel.get("type_name"):
            mystring=f"Selected: {sel.get("project_name")} ({ sel.get("project")}) → {sel.get("system_name")} ({sel.get("system")}) → {sel.get("subsystem_name")} ({sel.get("subsystem")}) → {sel.get("type_name")} ({sel.get("type")})"
        elif sel.get("project") and sel.get("project_name") and \
            sel.get("system") and sel.get("system_name") and \
            sel.get("subsystem") and sel.get("subsystem_name"):
            mystring=f"Selected: {sel.get("project_name")} ({ sel.get("project")}) → {sel.get("system_name")} ({sel.get("system")}) → {sel.get("subsystem_name")} ({sel.get("subsystem")})"
        elif sel.get("project") and sel.get("project_name") and \
            sel.get("system") and sel.get("system_name"):
            mystring=f"Selected: {sel.get("project_name")} ({ sel.get("project")}) → {sel.get("system_name")} ({sel.get("system")})"
        elif sel.get("project") and sel.get("project_name"):
            mystring=f"Selected: {sel.get("project_name")} ({ sel.get("project")})"
        else:
            mystring="Selected: "

        return mystring
            

    # --- restore projects ---
    @app.callback(
        Output("tg-table-projects", "data", allow_duplicate=True),
        Input("tg-cache", "data"),
        prevent_initial_call="initial_duplicate",   # runs automatically on load
    )
    def _restore_projects_from_cache(cache):
        cache = _init_cache(cache)
        data = cache.get("projects") or []
        if data:
            logger.info(f"[TypeGetter] Restored {len(data)} cached projects from local storage")
        else:
            logger.info("[TypeGetter] No cached projects found on startup")
        return data

    # --- restore systems ---
    @app.callback(
        Output("tg-table-systems", "data", allow_duplicate=True),
        Input("tg-cache", "data"),
        State("tg-selected", "data"),
        State("tg-current-level", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def _restore_systems_from_cache(cache, selected, level):
        if level != "systems":
            raise dash.exceptions.PreventUpdate
        cache = _init_cache(cache)
        project_id = (selected or {}).get("project")
        if not project_id:
            return []
        systems = cache.get("systems", {}).get(project_id, [])
        if systems:
            logger.info(f"[TypeGetter] Restored {len(systems)} systems for project {project_id}")
        return systems


   
    # ---------------------------
    # Sync buttons - fetch + cache
    # ---------------------------

    @app.callback(
        [
            Output("tg-sync-projects", "children"),
            Output("tg-sync-projects", "style"),
            Output("tg-sync-projects", "disabled"),
            Output("tg-sync-projects-trigger", "data"),
        ],
        Input("tg-sync-projects", "n_clicks"),
        prevent_initial_call=True,
    )
    def show_syncing_project_feedback(n_clicks):
        """Immediately update the button to orange and disable it."""
        if not n_clicks:
            raise PreventUpdate

        syncing_style = {
            "fontSize": "20px",
            "padding": "14px 32px",
            "backgroundColor": "#f39c12",  # orange
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "pointer",
            "transition": "all 0.2s ease-in-out",
            "marginRight": "50px",
            "gap": "15px",
        }

        logger.info("[TypeGetter] Porject button clicked — showing 'Syncing...' feedback")
        return "Syncing to the HWDB...", syncing_style, True, {"trigger": True}

    @app.callback(
        [
            Output("tg-table-projects", "data", allow_duplicate=True),
            Output("tg-cache", "data", allow_duplicate=True),
            Output("tg-sync-projects", "children",allow_duplicate=True),
            Output("tg-sync-projects", "style",allow_duplicate=True),
            Output("tg-sync-projects", "disabled",allow_duplicate=True),
        ],    
        #Input("tg-sync-projects", "n_clicks"),
        Input("tg-sync-projects-trigger", "data"),
        State("tg-cache", "data"),
        prevent_initial_call=True,
    )
    def _sync_projects(n_clicks, cache):
        if not n_clicks:
            raise dash.exceptions.PreventUpdate

        logger.info("[TypeGetter] tg-sync-projects syncing...")

        cache = _init_cache(cache)
        data = _fetch_projects()

        cache["projects"] = data
        logger.info(f"[TypeGetter] Projects synced: {len(data)}")

        style = {
            "fontSize": "20px",            # Larger text
            "padding": "14px 32px",        # Larger button size
            "backgroundColor": "#4CAF50",  # 
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "justifyContent": "center",
            "gap": "15px",
            "cursor": "pointer",
            #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
            "transition": "all 0.2s ease-in-out",
            "marginRight": "50px",
        }
            
        return data, cache, "Sync to the HWDB", style, False
        #return projects, projects

    @app.callback(
        [
            Output("tg-sync-systems", "children"),
            Output("tg-sync-systems", "style"),
            Output("tg-sync-systems", "disabled"),
            Output("tg-sync-systems-trigger", "data"),
        ],
        Input("tg-sync-systems", "n_clicks"),
        prevent_initial_call=True,
    )
    def show_syncing_system_feedback(n_clicks):
        """Immediately update the button to orange and disable it."""
        if not n_clicks:
            raise PreventUpdate

        syncing_style = {
            "fontSize": "20px",
            "padding": "14px 32px",
            "backgroundColor": "#f39c12",  # orange
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "pointer",
            "transition": "all 0.2s ease-in-out",
            "marginRight": "50px",
            "gap": "15px",
        }

        logger.info("[TypeGetter] System button clicked — showing 'Syncing...' feedback")
        return "Syncing to the HWDB...", syncing_style, True, {"trigger": True}

    
    @app.callback(
        [
            Output("tg-table-systems", "data", allow_duplicate=True),
            Output("tg-cache", "data", allow_duplicate=True),
            Output("tg-systems-store", "data", allow_duplicate=True),
            Output("tg-sync-systems", "children",allow_duplicate=True),
            Output("tg-sync-systems", "style",allow_duplicate=True),
            Output("tg-sync-systems", "disabled",allow_duplicate=True),
        ],
        #Input("tg-sync-systems", "n_clicks"),
        Input("tg-sync-systems-trigger", "data"),
        State("tg-selected", "data"),
        State("tg-cache", "data"),
        prevent_initial_call=True,
    )
    def _sync_systems(n_clicks, selected, cache):
        if not n_clicks:
            raise dash.exceptions.PreventUpdate

        style = {
            "fontSize": "20px",            # Larger text
            "padding": "14px 32px",        # Larger button size
            "backgroundColor": "#4CAF50",  # 
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "justifyContent": "center",
            "gap": "15px",
            "cursor": "pointer",
            #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
            "transition": "all 0.2s ease-in-out",
            "marginRight": "50px",
        }
            
        cache = _init_cache(cache)
        project_id = selected.get("project")
        if not project_id:
            logger.info("[TypeGetter] Sync Systems ignored: no project selected")
            return no_update, cache, no_update, "Sync to the HWDB", style, False
        data = _fetch_systems(project_id)
        cache["systems"][project_id] = data
        logger.info(f"[TypeGetter] Systems synced for project {project_id}: {len(data)}")
        logger.warning(f"[DEBUG] tg-systems-store will save {len(data)} rows")

        return data, cache, data, "Sync to the HWDB", style, False

    @app.callback(
        [
            Output("tg-sync-subsystems", "children"),
            Output("tg-sync-subsystems", "style"),
            Output("tg-sync-subsystems", "disabled"),
            Output("tg-sync-subsystems-trigger", "data"),
        ],
        Input("tg-sync-subsystems", "n_clicks"),
        prevent_initial_call=True,
    )
    def show_syncing_subsystem_feedback(n_clicks):
        """Immediately update the button to orange and disable it."""
        if not n_clicks:
            raise PreventUpdate

        syncing_style = {
            "fontSize": "20px",
            "padding": "14px 32px",
            "backgroundColor": "#f39c12",  # orange
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "pointer",
            "transition": "all 0.2s ease-in-out",
            "marginRight": "50px",
            "gap": "15px",
        }

        logger.info("[TypeGetter] Subsystem button clicked — showing 'Syncing...' feedback")
        return "Syncing to the HWDB...", syncing_style, True, {"trigger": True}
    
    @app.callback(
        [
            Output("tg-table-subsystems", "data", allow_duplicate=True),
            Output("tg-cache", "data", allow_duplicate=True),
            Output("tg-subsystems-store", "data", allow_duplicate=True),  # 👈 add this
            Output("tg-sync-subsystems", "children",allow_duplicate=True),
            Output("tg-sync-subsystems", "style",allow_duplicate=True),
            Output("tg-sync-subsystems", "disabled",allow_duplicate=True),
        ],
        #Input("tg-sync-subsystems", "n_clicks"),
        Input("tg-sync-subsystems-trigger", "data"),
        State("tg-selected", "data"),
        State("tg-cache", "data"),
        prevent_initial_call=True,
    )
    def _sync_subsystems(nc, selected, cache):
        logger.info(f"[DEBUG] _sync_subsystems() current level before returning: {ctx.states.get('tg-current-level.data')}")

        style = {
            "fontSize": "20px",            # Larger text
            "padding": "14px 32px",        # Larger button size
            "backgroundColor": "#4CAF50",  # 
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "justifyContent": "center",
            "gap": "15px",
            "cursor": "pointer",
            #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
            "transition": "all 0.2s ease-in-out",
            "marginRight": "50px",
        }

        
        cache = _init_cache(cache)
        project_id = selected.get("project")
        system_id = selected.get("system")

        if not system_id:
            logger.info("[TypeGetter] Sync Subsystems ignored: no system selected")
            return no_update, cache, no_update, "Sync to the HWDB", style, False

        # --- fetch + normalize + cache ---
        data = _fetch_subsystems(project_id, system_id)
        cache["subsystems"][str(system_id)] = data
        logger.info(f"[TypeGetter] Subsystems synced for system {system_id}: {len(data)}")

        # --- allow Dash DOM updates to settle before redraw ---
        time.sleep(0.2)   # 200ms delay — just enough to prevent flicker/race

        # --- force a deep copy to guarantee Dash sees new data identity ---
        refreshed = [dict(r) for r in data]  # shallow copy of each dict

        logger.info(f"[TypeGetter] Forcing table redraw with {len(refreshed)} rows")

        # Force Dash to see cache as a new object
        updated_cache = dict(cache)
        #return refreshed, cache
        logger.warning(f"[DEBUG] tg-subsystems-store will save {len(refreshed)} rows")
        return refreshed, updated_cache, refreshed, "Sync to the HWDB", style, False

    
    @app.callback(
        [
            Output("tg-sync-types", "children"),
            Output("tg-sync-types", "style"),
            Output("tg-sync-types", "disabled"),
            Output("tg-sync-types-trigger", "data"),
        ],
        Input("tg-sync-types", "n_clicks"),
        prevent_initial_call=True,
    )
    def show_syncing_type_feedback(n_clicks):
        """Immediately update the button to orange and disable it."""
        if not n_clicks:
            raise PreventUpdate

        syncing_style = {
            "fontSize": "20px",
            "padding": "14px 32px",
            "backgroundColor": "#f39c12",  # orange
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "pointer",
            "transition": "all 0.2s ease-in-out",
            "marginRight": "50px",
            "gap": "15px",
        }

        logger.info("[TypeGetter] Type button clicked — showing 'Syncing...' feedback")
        return "Syncing to the HWDB...", syncing_style, True, {"trigger": True}

    
    @app.callback(
        [
            Output("tg-table-types", "data", allow_duplicate=True),
            Output("tg-cache", "data", allow_duplicate=True),
            Output("tg-types-store", "data", allow_duplicate=True),
            Output("tg-sync-types", "children",allow_duplicate=True),
            Output("tg-sync-types", "style",allow_duplicate=True),
            Output("tg-sync-types", "disabled",allow_duplicate=True),
        ],
        #Input("tg-sync-types", "n_clicks"),
        Input("tg-sync-types-trigger", "data"),
        State("tg-selected", "data"),
        State("tg-cache", "data"),
        prevent_initial_call=True,
    )
    def _sync_types(nc, selected, cache):
        logger.info(f"[DEBUG] _sync_types() current level before returning: {ctx.states.get('tg-current-level.data')}")

        style = {
            "fontSize": "20px",            # Larger text
            "padding": "14px 32px",        # Larger button size
            "backgroundColor": "#4CAF50",  # 
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "justifyContent": "center",
            "gap": "15px",
            "cursor": "pointer",
            #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
            "transition": "all 0.2s ease-in-out",
            "marginRight": "50px",
        }
            
        cache = _init_cache(cache)

        project_id = selected.get("project")
        if not project_id:
            logger.info("[TypeGetter] Sync Types ignored: no project selected")
            return no_update, cache, no_update, "Sync to the HWDB", style, False
        system_id = selected.get("system")
        if not system_id:
            logger.info("[TypeGetter] Sync Types ignored: no system selected")
            return no_update, cache, no_update
        subsystem_id = selected.get("subsystem")
        if not subsystem_id:
            logger.info("[TypeGetter] Sync Types ignored: no subsystem selected")
            return no_update, cache, no_update
        data = _fetch_types(project_id,system_id,subsystem_id)
        cache["types"][subsystem_id] = data
        logger.info(f"[TypeGetter] Types synced for subsystem {subsystem_id}: {len(data)}")

        # --- allow Dash DOM updates to settle before redraw ---
        time.sleep(0.2)   # 200ms delay — just enough to prevent flicker/race

        # --- force a deep copy to guarantee Dash sees new data identity ---
        refreshed = [dict(r) for r in data]  # shallow copy of each dict

        logger.info(f"[TypeGetter] Forcing table redraw with {len(refreshed)} rows")


         # Force Dash to see cache as a new object
        updated_cache = dict(cache)

        logger.warning(f"[DEBUG] tg-types-store will save {len(refreshed)} rows")
        return refreshed, updated_cache, refreshed, "Sync to the HWDB", style, False

    # ---------------------------
    # Lazy load pages from cache (on entry)
    # ---------------------------

    # Show projects data when we enter projects level (if cached)
    @app.callback(
        Output("tg-table-projects", "data", allow_duplicate=True),
        Input("tg-current-level", "data"),
        Input("tabs", "value"), 
        State("tg-cache", "data"),
        prevent_initial_call=True,
    )
    def _populate_projects_on_entry(level, active_tab, cache):
        if active_tab != "type-getter" and level != "projects":
            raise dash.exceptions.PreventUpdate
        if level != "projects":
            raise dash.exceptions.PreventUpdate
        cache = _init_cache(cache)

        projects = cache.get("projects") or []

        if projects:
            logger.info(f"[TypeGetter] Restored {len(projects)} projects from cache on tab re-entry.")
        else:
            logger.info("[TypeGetter] No cached projects found; showing empty table.")
        
        return projects

    @app.callback(
        Output("tg-table-systems", "data", allow_duplicate=True),
        Input("tg-current-level", "data"),
        State("tg-selected", "data"),
        State("tg-cache", "data"),
        prevent_initial_call=True,
    )
    def _populate_systems_on_entry(level, selected, cache):
        if level != "systems":
            raise dash.exceptions.PreventUpdate
        cache = _init_cache(cache)
        pid = selected.get("project")
        return (cache.get("systems", {}).get(pid) or [])

    
    
    @app.callback(
        Output("tg-table-subsystems", "data", allow_duplicate=True),
        Input("tg-current-level", "data"),
        State("tg-selected", "data"),
        State("tg-cache", "data"),
        State("tg-table-subsystems", "data"),
        prevent_initial_call=True,
    )
    def _populate_subsystems_on_entry(level, selected, cache, existing_data):
        logger.info(f"[DEBUG] _populate_subsystems_on_entry fired: level={level}")
        if level != "subsystems":
            raise dash.exceptions.PreventUpdate


        cache = _init_cache(cache)
        current_sid = str((selected or {}).get("system"))
        cached = cache.get("subsystems", {})
        subsystems = cached.get(current_sid, [])

        # Determine if what's shown belongs to the correct system
        # (avoid stale display from a previous system)
        visible_first_id = existing_data[0]["id"] if existing_data else None
        visible_same_as_cached = (
            existing_data == subsystems and bool(subsystems)
        )

        if visible_same_as_cached:
            logger.info(f"[TypeGetter] Subsystems already up-to-date for system {current_sid}")
            raise dash.exceptions.PreventUpdate

        if subsystems:
            logger.info(f"[TypeGetter] Loading {len(subsystems)} subsystems for system {current_sid}")
            return subsystems
        else:
            logger.info(f"[TypeGetter] No subsystems cached for system {current_sid}; showing blank table")
            return []   # clear table if not cached
        
        logger.info(f"[TypeGetter] populate_subsystems_on_entry restored {len(subsystems)} subsystems from cache")

        return subsystems

    @app.callback(
        Output("tg-table-types", "data", allow_duplicate=True),
        Input("tg-current-level", "data"),
        State("tg-selected", "data"),
        State("tg-cache", "data"),
        State("tg-table-types", "data"),
        prevent_initial_call=True,
    )
    def _populate_types_on_entry(level, selected, cache, existing_data):
        logger.info(f"[DEBUG] _populate_types_on_entry fired: level={level}")
        if level != "types":
            raise dash.exceptions.PreventUpdate
        cache = _init_cache(cache)
        #ssid = selected.get("subsystem")
        #return (cache.get("types", {}).get(ssid) or [])
        current_ssid = str((selected or {}).get("subsystem"))
        cached = cache.get("types", {})
        types = cached.get(current_ssid, [])

        # Determine if what's shown belongs to the correct system
        # (avoid stale display from a previous system)
        visible_first_id = existing_data[0]["id"] if existing_data else None
        visible_same_as_cached = (
            existing_data == types and bool(types)
        )

        if visible_same_as_cached:
            logger.info(f"[TypeGetter] Types already up-to-date for subsystem {current_ssid}")
            raise dash.exceptions.PreventUpdate

        if types:
            logger.info(f"[TypeGetter] Loading {len(types)} types for subsystem {current_ssid}")
            return types
        else:
            logger.info(f"[TypeGetter] No types cached for subsystem {current_ssid}; showing blank table")
            return []   # clear table if not cached

        logger.info(f"[TypeGetter] populate_types_on_entry restored {len(types)} types from cache")
        logger.info(f"[DEBUG] _populate_types_on_entry returning {len(cache.get('types', {}).get(str(selected.get('subsystem')), []))} rows")
        return types

    # ---------------------------
    # Row selection → advance / set selection
    # ---------------------------

    @app.callback(
        Output("tg-current-level", "data", allow_duplicate=True),
        Output("tg-selected", "data", allow_duplicate=True),
        Output("tg-table-projects", "active_cell"), 
        Input("tg-table-projects", "active_cell"),
        State("tg-table-projects", "data"),
        State("tg-selected", "data"),
        prevent_initial_call=True,
    )
    def _choose_project(active_cell, table_data, selected):
        # Only react to clicks in the Name column
        if not active_cell or active_cell.get("column_id") != "name":
            raise dash.exceptions.PreventUpdate

        row_index = active_cell.get("row")
        if row_index is None or row_index < 0 or row_index >= len(table_data):
            raise dash.exceptions.PreventUpdate

        row = table_data[row_index]
        project_id = row.get("id")
        if not project_id:
            raise dash.exceptions.PreventUpdate
        project_name = row.get("name")
        if not project_name:
            raise dash.exceptions.PreventUpdate

        # Update selected info
        selected = dict(selected or {})
        selected.update({
            "project": project_id,
            "project_name": project_name,
            "system": None,
            "system_name": None,
            "subsystem": None,
            "subsystem_name": None,
            "type": None,
            "type_name": None
        })
        
        logger.info(f"[TypeGetter] _choose_project fired: active_cell={active_cell}")
        
        return "systems", selected, None


    @app.callback(
        Output("tg-current-level", "data", allow_duplicate=True),
        Output("tg-selected", "data", allow_duplicate=True),
        Output("tg-table-systems", "active_cell"), 
        Input("tg-table-systems", "active_cell"),
        State("tg-table-systems", "data"),
        State("tg-selected", "data"),
        prevent_initial_call=True,
    )
    def _choose_system(active_cell, table_data, selected):
        # Only react to clicks in the Name column
        if not active_cell or active_cell.get("column_id") != "name":
            raise dash.exceptions.PreventUpdate

        row_index = active_cell.get("row")
        if row_index is None or row_index < 0 or row_index >= len(table_data):
            raise dash.exceptions.PreventUpdate

        row = table_data[row_index]
        system_id = row.get("id")
        if not system_id:
            raise dash.exceptions.PreventUpdate
        system_name = row.get("name")
        if not system_name:
            raise dash.exceptions.PreventUpdate
        
        # Update selected info
        selected = dict(selected or {})
        selected.update({
            "system": system_id,
            "system_name": system_name,
            "subsystem": None,
            "subsystem_name": None,
            "type": None,
            "type_name": None
        })

        logger.info(f"[TypeGetter] _choose_system fired: active_cell={active_cell}")
        
        return "subsystems", selected, None
        #return "subsystems", selected, dash.no_update

    @app.callback(
        Output("tg-current-level", "data", allow_duplicate=True),
        Output("tg-selected", "data", allow_duplicate=True),
        Output("tg-table-subsystems", "active_cell"), 
        Input("tg-table-subsystems", "active_cell"),
        State("tg-table-subsystems", "data"),
        State("tg-selected", "data"),
        prevent_initial_call=True,
    )
    def _choose_subsystem(active_cell, table_data, selected):
        # Only react to clicks in the Name column
        if not active_cell or active_cell.get("column_id") != "name":
            raise dash.exceptions.PreventUpdate

        row_index = active_cell.get("row")
        if row_index is None or row_index < 0 or row_index >= len(table_data):
            raise dash.exceptions.PreventUpdate

        row = table_data[row_index]
        subsystem_id = row.get("id")
        if not subsystem_id:
            raise dash.exceptions.PreventUpdate
        subsystem_name = row.get("name")
        if not subsystem_name:
            raise dash.exceptions.PreventUpdate

        # Update selected info
        selected = dict(selected or {})
        selected.update({
            "subsystem": subsystem_id,
            "subsystem_name": subsystem_name,
            "type": None,
            "type_name": None
        })
        
        return "types", selected, None

    # Select Type → copy to clipboard & show status text
    @app.callback(
        Output("tg-copy-buffer", "data"),
        Output("tg-typeid-status", "children"),
        #Output("tg-clipboard", "content"), 
        Output("tg-selected", "data", allow_duplicate=True),
        Output("tg-table-types", "active_cell"), 
        Input("tg-table-types", "active_cell"),
        State("tg-table-types", "data"),
        State("tg-selected", "data"),
        prevent_initial_call=True,
    )
    def _choose_type(active_cell, table_data, selected):
        # Only react to clicks in the Name column
        if not active_cell or active_cell.get("column_id") != "name":
            raise dash.exceptions.PreventUpdate

        row_index = active_cell.get("row")
        if row_index is None or row_index < 0 or row_index >= len(table_data):
            raise dash.exceptions.PreventUpdate

        row = table_data[row_index]
        type_id = row.get("id")
        if not type_id:
            raise dash.exceptions.PreventUpdate
        type_name = row.get("name")
        if not type_name:
            raise dash.exceptions.PreventUpdate

        # Update selected info
        selected = dict(selected or {})
        selected.update({
            "type": type_id,
            "type_name": type_name
        })
        
        # Copy to clipboard via dcc.Clipboard.content
        msg = f"Copied Type ID: {type_id}"
        logger.info(f"[TypeGetter] {msg}")
        #return type_id, msg, selected, None
        #return type_id, html.Span(msg, id="tg-typeid-text"), type_id, selected, None
        return type_id, dash.no_update, selected, None

    # --- 💡 JS-based clientside clipboard ---
    app.clientside_callback(
        """
        function(text) {
            if (!text) return window.dash_clientside.no_update;

            // --- Copy to clipboard ---
            try {
                navigator.clipboard.writeText(text);
                console.log("Copied Type ID:", text);
            } catch (err) {
                console.error("Clipboard copy failed:", err);
            }

            // --- Flash message ---
            const el = document.getElementById("tg-typeid-status");
            if (el) {
                el.textContent = `Copied Type ID: ${text}`;
                el.classList.remove("fade-out");
                void el.offsetWidth;  // restart transition
                setTimeout(() => el.classList.add("fade-out"), 2000);
            }

            // Do NOT cause Dash re-render
            return window.dash_clientside.no_update;
        }
        """,
        Output("tg-typeid-status", "children", allow_duplicate=True),
        Input("tg-copy-buffer", "data"),
        prevent_initial_call=True,
    )
    
    # ---------------------------
    # Back buttons
    # ---------------------------

    @app.callback(
        Output("tg-current-level", "data", allow_duplicate=True),
        Input("tg-back-systems", "n_clicks"),
        prevent_initial_call=True,
    )
    def _back_from_systems(n):
        if not n:
            raise dash.exceptions.PreventUpdate
        return "projects"

    @app.callback(
        Output("tg-current-level", "data", allow_duplicate=True),
        Input("tg-back-subsystems", "n_clicks"),
        prevent_initial_call=True,
    )
    def _back_from_subsystems(n):
        if not n:
            raise dash.exceptions.PreventUpdate
        return "systems"

    @app.callback(
        Output("tg-current-level", "data", allow_duplicate=True),
        Input("tg-back-types", "n_clicks"),
        prevent_initial_call=True,
    )
    def _back_from_types(n):
        if not n:
            raise dash.exceptions.PreventUpdate
        return "subsystems"


    

    @app.callback(
        Output("tg-table-projects", "data", allow_duplicate=True),
        Output("tg-table-systems", "data", allow_duplicate=True),
        Output("tg-table-subsystems", "data", allow_duplicate=True),
        Output("tg-table-types", "data", allow_duplicate=True),
        Input("tabs", "value"),
        State("tg-current-level", "data"),
        State("tg-cache", "data"),   
        State("tg-systems-store", "data"),
        State("tg-subsystems-store", "data"),
        State("tg-types-store", "data"),
        prevent_initial_call=True,
    )
    def _restore_tables_on_tab_switch(active_tab, level, cache, systems_data, subsystems_data, types_data):
        """
        When user returns to Type Getter tab, restore the appropriate table
        from its persistent local store.
        """
        if active_tab != "type-getter":
            raise dash.exceptions.PreventUpdate

        logger.info(f"[TypeGetter] Re-entering tab; current level = {level}")

        cache = _init_cache(cache)
        
        if level == "projects":
            logger.info("[TypeGetter] Restoring projects from local store")
            cache = _init_cache(cache)
            projects = cache.get("projects", [])
            if projects:
                return projects, dash.no_update, dash.no_update, dash.no_update
        
        if level == "systems" and systems_data:
            logger.info(f"[TypeGetter] Restoring {len(systems_data)} systems from local store")
            return dash.no_update, systems_data, dash.no_update, dash.no_update

        elif level == "subsystems" and subsystems_data:
            logger.info(f"[TypeGetter] Restoring {len(subsystems_data)} subsystems from local store")
            return dash.no_update, dash.no_update, subsystems_data, dash.no_update

        elif level == "types" and types_data:
            logger.info(f"[TypeGetter] Restoring {len(types_data)} types from local store")
            return dash.no_update, dash.no_update, dash.no_update, types_data

        logger.info(f"[TypeGetter] No stored data found for {level}")
        raise dash.exceptions.PreventUpdate


    # This listens for that signal and clears the relevant tables, stores, and selections:
    @app.callback(
        [
            Output("tg-table-projects", "data", allow_duplicate=True),
            Output("tg-table-systems", "data", allow_duplicate=True),
            Output("tg-table-subsystems", "data", allow_duplicate=True),
            Output("tg-table-types", "data", allow_duplicate=True),
            Output("tg-cache", "data", allow_duplicate=True),
            Output("tg-selected", "data", allow_duplicate=True),
            Output("tg-systems-store", "data", allow_duplicate=True),
            Output("tg-subsystems-store", "data", allow_duplicate=True),
            Output("tg-types-store", "data", allow_duplicate=True),
        ],
        Input("version-change-signal", "data"),
        prevent_initial_call=True,
    )
    def clear_typegetter_on_version_change(signal):
        if not signal:
            raise dash.exceptions.PreventUpdate

        logger.info("[TypeGetter] HWDB version switched — clearing tables and selections.")

        empty_table = []
        empty_cache = {
            "projects": [],
            "systems": {},
            "subsystems": {},
            "types": {},
        }
        empty_selected = {"project": None, "system": None, "subsystem": None, "type": None}

        return (
            empty_table,  # projects
            empty_table,  # systems
            empty_table,  # subsystems
            empty_table,  # types
            empty_cache,
            empty_selected,
            None,  # tg-systems-store
            None,  # tg-subsystems-store
            None,  # tg-types-store
        )

    # --- Reset to Projects on initial browser load ---
    app.clientside_callback(
        """
        function(tab) {
            if (tab === "tab-typegetter" && !window._tg_init_done) {
                window._tg_init_done = true;
                console.log("[TypeGetter] Forcing initial Projects page");
                return "projects";
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("tg-current-level", "data", allow_duplicate=True),
        Input("tabs", "value"),
        prevent_initial_call=True,
    )

    
