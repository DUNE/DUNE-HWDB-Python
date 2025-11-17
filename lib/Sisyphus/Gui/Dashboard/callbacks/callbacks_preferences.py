# callbacks/callbacks_preferences.py
from dash import Input, Output, State, ctx, html
import dash
import os
from pathlib import Path
from datetime import datetime
from Sisyphus.Gui.Dashboard.utils.config import switch_profile
from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

def register_preferences_callbacks(app):

    # Preference file lives under the active profile directory
    PREF_FILE = Path(config.active_profile.profile_dir) / "dash_user_preferences.txt"

    # 1) Initialize store once at startup (default = launch dir; else from PREF_FILE)
    @app.callback(
        Output("preferences-store", "data"),
        Output("db-version-toggle", "value"),
        Input("init-trigger", "n_intervals"),
        prevent_initial_call=False
    )
    def initialize_preferences(_):
        default_dir = os.getcwd()
        active_version = config.active_profile.profile_name  # ← read from config.json

        if PREF_FILE.exists():
            saved = PREF_FILE.read_text().strip()
            if saved and os.path.isdir(saved):
                return {"working_dir": saved}, active_version
        # ensure file exists the first time
        try:
            PREF_FILE.parent.mkdir(parents=True, exist_ok=True)
            PREF_FILE.write_text(default_dir)
        except Exception:
            pass
        return {"working_dir": default_dir}, active_version

    # 2) Render / navigate the directory browser (clickable folders)
    @app.callback(
        [
            Output("directory-browser", "children"),
            Output("preferences-store", "data", allow_duplicate=True),  # update selected dir on click
            Output("dir-display", "children"),
        ],
        [
            Input("open-preferences", "n_clicks"),
            Input({"type": "dir-link", "index": dash.ALL}, "n_clicks"),
        ],
        State("preferences-store", "data"),
        prevent_initial_call=True
    )
    def browse_directories(open_click, dir_clicks, store_data):
        # current selection from store
        current = (store_data or {}).get("working_dir") or os.getcwd()

        # if a folder link was clicked, ctx.triggered_id will be a dict
        trig = ctx.triggered_id
        if isinstance(trig, dict) and trig.get("type") == "dir-link":
            selected = trig.get("index")
            if isinstance(selected, str) and os.path.isdir(selected):
                current = selected  # navigate into that folder

        # Build folder list
        try:
            base_path = Path(current)
            subdirs = sorted([p for p in base_path.iterdir() if p.is_dir() and not p.name.startswith(".")])
        except Exception as e:
            children = html.Div(f"⚠️ Cannot open {current}: {e}")
            return children, dash.no_update, f"Current: {current}"

        entries = []
        # Parent link (if not root)
        if base_path.parent != base_path:
            entries.append(
                html.A("⬆️ (Parent)",
                       id={"type": "dir-link", "index": str(base_path.parent)},
                       n_clicks=0,
                       style={"display": "block", "marginBottom": "6px"})
            )

        for sub in subdirs:
            entries.append(
                html.A(f"📁 {sub.name}",
                       id={"type": "dir-link", "index": str(sub)},
                       n_clicks=0,
                       className="dir-link" + (" selected" if str(sub) == str(base_path) else ""),
                       style={"display": "block", "marginLeft": "12px", "padding": "2px 4px"})
            )

        browser_ui = html.Div([html.Div(entries)])
        # Also update the store with the *current* path (so Save uses it)
        new_store = {"working_dir": str(base_path)}

        return browser_ui, new_store, f"Current: {base_path}"

    # 3) Toggle the slide-in pane
    @app.callback(
        Output("preferences-pane", "is_open"),
        [Input("open-preferences", "n_clicks"), Input("save-preferences", "n_clicks")],
        State("preferences-pane", "is_open"),
        prevent_initial_call=True
    )
    def toggle_pane(open_click, save_click, is_open):
        if ctx.triggered_id in ("open-preferences", "save-preferences"):
            return not is_open
        return is_open

    # 4) Save the selected directory (string!) into the profile’s PREF_FILE
    @app.callback(
        [
            Output("working-dir-display", "children"),
            Output("preferences-store", "data", allow_duplicate=True),
        ],
        Input("save-preferences", "n_clicks"),
        State("preferences-store", "data"),
        prevent_initial_call=True
    )
    def save_working_directory(n_clicks, store_data):
        # ALWAYS extract the string path from the store dict
        directory = (store_data or {}).get("working_dir")
        if not isinstance(directory, str):
            return "❌ No directory selected.", dash.no_update
        if not os.path.isdir(directory):
            return f"❌ Directory not found: {directory}", dash.no_update
        if not os.access(directory, os.W_OK):
            return f"❌ Directory not writable: {directory}", dash.no_update

        try:
            PREF_FILE.parent.mkdir(parents=True, exist_ok=True)
            PREF_FILE.write_text(directory)
            #msg = f"✅ Working directory saved: {directory}  (prefs: {PREF_FILE})"
            msg = f"✅ Working directory saved: {directory}"
            return msg, {"working_dir": directory}
        except Exception as e:
            return f"❌ Failed to save preferences: {e}", dash.no_update

    # 5) Handle Database Version toggle
    @app.callback(
        [
            Output("db-version-toggle", "value", allow_duplicate=True),
            Output("db-version-display", "children", allow_duplicate=True),
            Output("version-change-signal", "data", allow_duplicate=True),
        ],
        Input("db-version-toggle", "value"),
        prevent_initial_call=True
    )
    def update_db_version(selected_version):
        """
        Called when user switches DB version radio buttons.
        """
        if selected_version not in ("production", "development"):
            raise dash.exceptions.PreventUpdate

        switch_profile(selected_version, persist=True)

        message = f"You are currently using the {selected_version} version"
        
        logger.info(f"[Switch] Active profile set to {selected_version}")
        logger.info(f"[Config] REST API = {config.active_profile.rest_api}")

        # send a signal with a unique timestamp
        return selected_version, message, {"timestamp": datetime.now().isoformat()}
