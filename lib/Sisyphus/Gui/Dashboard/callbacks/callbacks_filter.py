from dash import Input, Output, State
import dash
import pandas as pd
import numpy as np
import re
from dash import dcc
from dash.exceptions import PreventUpdate
import os
from datetime import datetime
from Sisyphus.Configuration import config
logger = config.getLogger(__name__)
import json

#---
import sys
import argparse
import Sisyphus
import Sisyphus.Configuration as Config
from Sisyphus.Configuration import config
logger = config.getLogger(__name__)
from Sisyphus.Utils.Terminal import Image
from Sisyphus.Utils.Terminal.Style import Style

# Store the filtered Items in a csv file
def register_callbacks(app):
    @app.callback(
        Output("download-dataframe-csv","data"),
        Output("save-status", "children"),
        Output("save-status-timer", "disabled"),
        Input("btn-download","n_clicks"),
        State({"type":"field","index":dash.ALL},"value"),
        State({"type":"threshold","index":dash.ALL},"value"),
        State({"type":"operator","index":dash.ALL},"value"),
        State("logic-operator","value"),
        State("filtered-store", "data"),
        #Input("data-store", "data"),
        State("csv-filename", "value"),
        State("preferences-store", "data"),
        State("typeid-input", "value"),
        State("testtype-input", "value"),
        State("condition-container","children"), # <--- testing
        prevent_initial_call=True
    )
    def download_filtered(n_clicks, fields, thresholds, operators, logic_operator, filtered_data, filename, preferences, typeid, testtype,conds):

        if not n_clicks or not filtered_data:
            raise PreventUpdate

        
        # Default name if user didn’t type one
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = "HWDB_filtered.csv"
        if not filename or filename.strip() == default_name:

            if testtype:
                filename = f"HWDB_filtered_{typeid}_{testtype}_{ts}.csv"
            else:
                filename = f"HWDB_filtered_{typeid}_{ts}.csv"
        


        
        if not filename.lower().endswith(".csv"):
            filename += ".csv"

        if n_clicks and filtered_data:
            df = pd.DataFrame(filtered_data)

            # --- Local save ---
            save_dir = preferences.get("working_dir", os.getcwd())
            
            # Create subdirectory based on typeid
            if typeid:
                sub_dir = os.path.join(save_dir, str(typeid))
                os.makedirs(sub_dir, exist_ok=True)  # Create folder if it doesn't exist
                save_dir = sub_dir  # redirect save target
            
            save_path = os.path.join(save_dir, filename)

            try:
                df.to_csv(save_path, index=False)
                msg = f"✅ Saved to: {save_path}"
                logger.info(f"[CSV Save] Saved locally to: {save_path}")
            except Exception as e:
                msg = f"⚠️ Failed to save: {e}"
                logger.error(f"[CSV Save] ⚠️ Failed to save locally: {e}")



            # --- Save filter conditions as JSON ---
            if fields and thresholds and operators and logic_operator:
                logger.info(f"Saving a JSON file...")
                if typeid:
                    if testtype:
                        cond_filename = f"HWDB_conditions_{typeid}_{testtype}_{ts}.json"
                    else:
                        cond_filename = f"HWDB_conditions_{typeid}_{ts}.json"
                else:
                    cond_filename = f"HWDB_conditions_{ts}.json"
                cond_path = os.path.join(save_dir, cond_filename)
                
                conditions = {
                    "typeid": typeid,
                    "testtype": testtype,
                    "fields": fields,
                    "thresholds": thresholds,
                    "operators": operators,
                    "logic_operator": logic_operator,
                    "timestamp": ts,
                }
                
                try:
                    with open(cond_path, "w") as f:
                        json.dump(conditions, f, indent=2)
                        logger.info(f"[COND Save] Saved filter conditions to: {cond_path}")
                except Exception as e:
                    logger.error(f"[COND Save] ⚠️ Failed to save conditions: {e}")
                
            return dash.no_update,msg, False
            
        raise dash.exceptions.PreventUpdate


    # Clearing the message when timer fires
    @app.callback(
        Output("save-status", "children", allow_duplicate=True),
        Output("save-status-timer", "disabled", allow_duplicate=True),
        Input("save-status-timer", "n_intervals"),
        prevent_initial_call="initial_duplicate"
    )
    def clear_save_status(_):
        # Clear the message and stop the timer
        return "", True
       
    # Display a suggested file name at startup
    @app.callback(
        Output("csv-filename", "value"),
        Input("typeid-input", "value"),
        Input("testtype-input", "value"),
        prevent_initial_call=False  # ensures it runs at startup
    )
    def suggest_filename(typeid,testtype):
        # Generate timestamp
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # If no typeid yet, just show a simple placeholder
        if not typeid:
            return f"HWDB_filtered_{ts}.csv"

        # Otherwise, build a suggested name
        if testtype:
            filename = f"HWDB_filtered_{typeid}_{testtype}_{ts}.csv"
        else:
            filename = f"HWDB_filtered_{typeid}_{ts}.csv"
        return filename
