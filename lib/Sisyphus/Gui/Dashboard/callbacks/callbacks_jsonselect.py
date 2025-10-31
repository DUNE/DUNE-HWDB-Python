from dash import Input, Output, State, ctx, no_update
import dash
import os, json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# Import your Sisyphus config to locate preferences file
from Sisyphus.Configuration import config
from ..utils.data_utils import load_data, GETTestLog

logger = config.getLogger(__name__)

def register_jsonselect_callbacks(app):

    PREF_FILE = Path(config.active_profile.profile_dir) / "dash_user_preferences.txt"

    # --- Select and load local JSON file ---
    @app.callback(
        [
            Output("data-store", "data", allow_duplicate=True),
            Output("downloaded-output", "children", allow_duplicate=True),
        ],
        Input("select-json", "n_clicks"),
        prevent_initial_call=True,
    )
    def select_local_json(n_clicks):
        if not n_clicks:
            return no_update, no_update

        # 1️Determine working directory
        if PREF_FILE.exists():
            working_dir = PREF_FILE.read_text().strip()
            if not os.path.isdir(working_dir):
                working_dir = os.getcwd()
        else:
            working_dir = os.getcwd()

        logger.info(f"[Select JSON] Starting in: {working_dir}")

        # 2️Open file picker at that directory
        root = tk.Tk()
        root.withdraw()  # hide Tkinter root window
        file_path = filedialog.askopenfilename(
            title="Select JSON file",
            initialdir=working_dir,
            filetypes=[("JSON files", "*.json")],
        )
        root.destroy()

        if not file_path:
            logger.info("[Select JSON] User canceled.")
            return no_update, "❌ No file selected."

        logger.info(f"[Select JSON] Selected: {file_path}")

        # 3️Load and parse JSON
        try:
            with open(file_path, "r") as f:
                json_data = json.load(f)
        except Exception as e:
            msg = f"⚠️ Failed to read JSON: {e}"
            logger.error(msg)
            return no_update, msg

        # 4️Feed into your loader
        try:
            df = load_data(json_data)
            logger.info(f"[Select JSON] Loaded {len(df)} entries.")
        except Exception as e:
            msg = f"⚠️ Failed to parse JSON: {e}"
            logger.error(msg)
            return no_update, msg

        # 5️Update UI and data-store
        file_name = os.path.basename(file_path)
        msg = f"✅ Loaded local JSON file: {file_name} from {working_dir}"
        return df.to_dict("records"), msg
