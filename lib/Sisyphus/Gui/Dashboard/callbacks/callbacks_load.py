from dash import Input, Output, State, html, dcc, ctx
import dash
from dash.exceptions import PreventUpdate
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import base64, io, json, pickle
from datetime import datetime
from Sisyphus.Gui.Dashboard.utils.data_utils import load_data, GETTestLog
from Sisyphus.RestApiV1 import get_hwitem, get_hwitems, get_hwitem_test
from Sisyphus.Configuration import config
from pathlib import Path
import os
import time
import threading

logger = config.getLogger(__name__)

_plot_jobs = {}

def _plot_sync_worker(job_id):
    from Sisyphus.RestApiV1 import Utilities as ra_util
    executor = ra_util._executor

    job = _plot_jobs[job_id]
    args = job["args"]
    typeid = job["typeid"]
    testtype = job["testtype"]

    try:
        resp = get_hwitems(**args)
        items = resp["data"]
        total = len(items)
        job["total"] = total

        results = []

        # --- Fetch TestLog per item (PROGRESS LOOP) ---
        futures = [executor.submit(GETTestLog, it, testtype) for it in items]
        for idx, f in enumerate(futures):
            try:
                results.append(f.result())
            except Exception as e:
                logger.error(f"[Plots] GETTestLog failed: {e}")
                results.append({})
            job["processed"] = idx + 1

        # --- Convert raw results to DataFrame ---
        data = load_data(results)

        # --- Drop unwanted keys ---
        unwanted_keys = [
            "category","link","link_href","link_rel","status","component_id",
            "ITEM: category","ITEM: batch_id","ITEM: batch_received","ITEM: component_id",
            "ITEM: component_type_name","ITEM: component_type_part_type_id","ITEM: specs_version",
            "TEST: id","TEST: images","TEST: link_href","TEST: link_rel","TEST: methods_0_rel",
            "TEST: methods_0_href","TEST: test_spec_version","TEST: test_type_id","TEST: test_type_name",
        ]
        data = data.drop(columns=[c for c in data.columns if c in unwanted_keys], errors="ignore")

        # --- Sort columns exactly like before ---
        priority_item = [...]
        priority_test = [...]

        item_cols = sorted([c for c in data.columns if c.startswith("ITEM: ")])
        test_cols = sorted([c for c in data.columns if c.startswith("TEST: ")])
        other_cols = [c for c in data.columns if c not in item_cols + test_cols]

        item_cols = [c for c in priority_item if c in item_cols] + sorted([c for c in item_cols if c not in priority_item])
        test_cols = [c for c in priority_test if c in test_cols] + sorted([c for c in test_cols if c not in priority_test])
        other_cols = [c for c in priority_item if c in other_cols] + sorted([c for c in other_cols if c not in priority_item])

        sorted_cols = list(dict.fromkeys(item_cols + test_cols + other_cols))
        data = data[sorted_cols]

        # --- Save pickle locally (unchanged logic) ---
        from pathlib import Path
        pref_file = Path(config.active_profile.profile_dir) / "dash_user_preferences.txt"
        if pref_file.exists():
            working_dir = pref_file.read_text().strip()
            if not os.path.isdir(working_dir):
                working_dir = os.getcwd()
        else:
            working_dir = os.getcwd()

        save_dir = Path(working_dir) / typeid
        save_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pickle_filename = f"HWDB_downloaded_{typeid}_{ts}.pkl"
        if testtype:
            pickle_filename = f"HWDB_downloaded_{typeid}_{testtype}_{ts}.pkl"

        pickle_path = save_dir / pickle_filename
        import pickle
        with open(pickle_path, "wb") as f:
            pickle.dump(data, f)

        # --- Store result & mark done ---
        job["data"] = data.to_dict("records")
        job["done"] = True

    except Exception as e:
        job["error"] = str(e)
        job["done"] = True



# --- Load the JSON and reset button text after finish ---
def register_callbacks(app):

    # --------------------------------------------------------
    # Poll background job status
    # --------------------------------------------------------
    @app.callback(
        Output("load-json", "children", allow_duplicate=True),
        Output("load-json", "style", allow_duplicate=True),
        Output("load-json", "disabled", allow_duplicate=True),
        Output("data-store", "data", allow_duplicate=True),
        Output("downloaded-output", "children", allow_duplicate=True),
        Output("plots-interval", "disabled", allow_duplicate=True),
        Input("plots-interval", "n_intervals"),
        State("plots-job-id", "data"),
        prevent_initial_call=True,
    )
    def poll_plots_job(n, job_id):
        job = _plot_jobs.get(job_id)
        if not job:
            raise PreventUpdate

        if job.get("error"):
            red = {"backgroundColor": "#e74c3c", "color": "white"}
            return f"Error: {job['error']}", red, False, None, "", True

        processed = job["processed"]
        total = job["total"]
        pct = int(processed * 100 / total)

        if not job["done"]:
            orange = {
                "fontSize": "20px",
                "padding": "14px 32px",
                "backgroundColor": "#f39c12",
                "color": "white",
                "border": "none",
                "borderRadius": "8px",
                "cursor": "not-allowed",
                "animation": "pulse 1.5s infinite",
                "gap": "15px",
                "marginRight": "50px",
            }
            return f"{pct}% completed...", orange, True, None, "", False

        # DONE — restore button
        green = {
            "fontSize": "20px",
            "padding": "14px 32px",
            "backgroundColor": "#4CAF50",
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "pointer",
            "gap": "15px",
            "marginRight": "50px",
        }
        msg = f"Loaded {total} Items from the HWDB"
        data = job["data"]
        _plot_jobs.pop(job_id, None)
        return "Sync to the HWDB", green, False, data, msg, True

    # --------------------------------------------------------
    # Display the progress
    # --------------------------------------------------------
    @app.callback(
        [
            Output("load-json", "children", allow_duplicate=True),
            Output("load-json", "style", allow_duplicate=True),
            Output("load-json", "disabled", allow_duplicate=True),
            Output("data-store", "data", allow_duplicate=True),
            Output("downloaded-output", "children", allow_duplicate=True),
            Output("plot-sync-interval", "disabled", allow_duplicate=True),
        ],
        Input("plot-sync-interval", "n_intervals"),
        State("plot-sync-job-id", "data"),
        prevent_initial_call=True,
    )
    def update_sync_progress(n, job_id):
        if not job_id or job_id not in _plot_jobs:
            raise PreventUpdate

        job = _plot_jobs[job_id]
        processed = job["processed"]
        total = job["total"]
        pct = int(100 * processed / total) if total else 0

        # update % text while job is running
        if not job["done"]:
            return (
                f"{pct}% completed...",
                {
                    "fontSize": "20px",
                    "padding": "14px 32px",
                    "backgroundColor": "#f39c12",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "8px",
                    "cursor": "not-allowed",
                    "transition": "all 0.2s ease-in-out",
                    "gap": "15px",
                    "marginRight": "50px",
                },
                True,
                dash.no_update,
                "",
                False,  # keep interval alive
            )

        # job finished → restore button + save data
        data = job.get("data", [])
        msg = html.Div(f"Loaded {total} Items from the HWDB",
                    style={"fontSize": "20px", "color": "red"})

        green = {
            "fontSize": "20px",
            "padding": "14px 32px",
            "backgroundColor": "#4CAF50",
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "pointer",
            "gap": "15px",
            "marginRight": "50px",
        }

        return "Sync to the HWDB", green, False, data, msg, True,

    # --------------------------------------------------------
    # Download DATA
    # --------------------------------------------------------
    @app.callback(
        [Output("data-store", "data", allow_duplicate=True),
         Output("load-json", "children"),
         Output("downloaded-output", "children", allow_duplicate=True), # The downloaded message
         Output("load-json", "style"),
         Output("load-json", "disabled"),
         Output("plot-sync-job-id", "data"),
         Output("plot-sync-interval", "disabled"),
        ],
        Input("load-json", "n_clicks"), # The Sync to the HWDB button
        Input("upload-json", "contents"), # for loading a local file
        State("upload-json", "filename"), # for loading a local file
        State("typeid-input", "value"),
        State("testtype-input", "value"),
        
        Input("prefilter-pid", "value"),
        Input("prefilter-serialnum", "value"),
        Input("prefilter-manu", "value"),
        Input("prefilter-creator", "value"),
        Input("prefilter-comments", "value"),
        Input("prefilter-location", "value"),
        Input("prefilter-country", "value"),
        Input("prefilter-institution", "value"),
        Input("prefilter-status", "value"),
        Input("prefilter-isinstalled", "value"),
        Input("prefilter-consortiumcert", "value"),
        Input("prefilter-qaqcuploaded", "value"),
        
        prevent_initial_call=True
    )
    #def load_json_file(n_clicks, upload_contents, upload_name, user_string, testtype_string, switch_value):
    def load_json_file(n_clicks, upload_contents, upload_name, user_string, testtype_string,
                           pre_pid, pre_serial, pre_manu, pre_creator, pre_comments, pre_location,
                           pre_country, pre_institution, pre_status, pre_installed, pre_cert, pre_uploaded):

        trig = ctx.triggered_id
        df = None
    
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

        # only block if neither sync button nor upload fired
        #if not n_clicks:
        #    raise dash.exceptions.PreventUpdate
        if trig not in ("load-json", "upload-json"):
            raise dash.exceptions.PreventUpdate
        
        # No Component Type ID was provided...
        if not user_string:
            return dash.no_update, "Sync to the HWDB", "", style, False, None, False

        

        
        #------------------------------------------
        # Case A: user clicked “Sync to the HWDB”
        #------------------------------------------
        if trig == "load-json":
            #logger.info("[Sync] ⏳ Fetching data from HWDB…")

            logger.info("[Sync] Starting background job for HWDB sync...")
            
            # Load the data
            try:

                # --- Setting up the Pre-Filters ---
                args = {
                    "part_type_id"      : None,
                    "size"              : None,
                    "part_id"           : None,
                    "serial_number"     : None,
                    "manufacturer"      : None,
                    "creator"           : None,
                    "comments"          : None,
                    "country_of_origin" : None,
                    "resp_institution"  : None,
                    "status"            : None,
                    "location"          : None,
                    "certified_qaqc"    : None,
                    "qaqc_uploaded"     : None,
                    "is_installed"      : None,
                }
                args["part_type_id"] = user_string
                args["size"]         = 99999
                #+++++++++
                if pre_pid is not None:
                    args["pre_pid"] = pre_pid
                if pre_serial is not None:
                    args["serial_number"] = f"%{pre_serial}%"
                if pre_manu is not None:
                    args["manufacturer"] = f"%{pre_manu}%"
                if pre_creator is not None:
                    args["creator"] = f"%{pre_creator}%"
                if pre_comments is not None:
                    args["comments"] = f"%{pre_comments}%"
                if pre_country is not None:
                    args["country_of_origin"] = f"%{pre_country}%"
                if pre_institution is not None:
                    args["resp_institution"] = f"%{pre_institution}%"
                if pre_status is not None:
                    statusid = -1
                    if    pre_status == "Unknown":
                        statusid = 0
                    elif  pre_status == "In Fabrication":
                        statusid = 100
                    elif  pre_status == "Waiting on QA/QC Tests":
                        statusid = 110
                    elif  pre_status == "QA/QC Tests - Passed All":
                        statusid = 120
                    elif  pre_status == "QA/QC Tests - Non-conforming":
                        statusid = 130
                    elif  pre_status == "QA/QC Tests - Use As Is":
                        statusid = 140
                    elif  pre_status == "In Rework":
                        statusid = 150
                    elif  pre_status == "In Repair":
                        statusid = 160
                    elif  pre_status == "Permanently Unavailable":
                        statusid = 170
                    elif  pre_status == "Broken or Needs Repair":
                        statusid = 180
                    elif  pre_status == "Available (deprecated)":
                        statusid = 1
                    elif  pre_status == "Temporarily Unavailable (deprecated)":
                        statusid = 2
                    elif  pre_status == "Permanently Unavailable (deprecated)":
                        statusid = 3
                    args["status"] = statusid
                if pre_location is not None:
                    args["location"] = pre_location
                if pre_cert is not None:
                    args["certified_qaqc"] = pre_cert
                if pre_uploaded is not None:
                    args["qaqc_uploaded"] = pre_uploaded
                if pre_installed is not None:
                    args["is_installed"] = pre_installed
                #+++++++++




                
                # REST call
                #resp = get_hwitems(user_string, size=99999)
                resp = get_hwitems(**args)
                #totalentry = len(resp["data"])
                all_items = resp["data"]
                total = len(all_items)

                # Register job
                job_id = f"PLOT-{int(time.time()*1000)}"
                global _plot_jobs
                _plot_jobs[job_id] = {
                    "processed": 0,
                    "total": total,
                    "done": False,
                    "error": None,
                    "typeid": user_string,
                    "testtype": testtype_string,
                    "args": args  # store filters
                }

                # Launch background thread
                thread = threading.Thread(
                    target=_plot_sync_worker,
                    args=(job_id,),
                    daemon=True,
                )
                thread.start()
        
                # start polling + disable button + show 0%
                orange = {
                    "fontSize": "20px",
                    "padding": "14px 32px",
                    "backgroundColor": "#f39c12",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "8px",
                    "cursor": "not-allowed",
                    "animation": "pulse 1.5s infinite",
                    "gap": "15px",
                    "marginRight": "50px",
                }

                return dash.no_update, "0% completed...", "", orange, True, job_id, False

            except Exception as e:
                logger.error(f"[Sync] ERROR while preparing sync job: {e}")
                red = style.copy()
                red["backgroundColor"] = "#FF0000"
                return dash.no_update, "Sync to the HWDB", html.Div(
                    f"Error: {e}",
                    style={"fontSize": "20px", "color": "red"}
                    ), red, False, None, False
        
        #------------------------------------------
        # Case B: user uploaded (read) a file
        #------------------------------------------
        #elif trig == "upload-json" and upload_contents:
        elif ("upload-json" in (trig or "")) and upload_contents and upload_name:
            
            content_type, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string)

            ext = os.path.splitext(upload_name)[1].lower()

            try:
                if ext in [".pkl", ".pickle"]:
                    # --- Pickle ---
                    data = pickle.loads(decoded)
                elif ext in [".csv"]:
                    # --- CSV ---
                    data = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
                else:
                    return dash.no_update, f"⚠️ Unsupported file type: {ext}"
                
                totalentry = len(data)

                # Convert to JSON for storage
                return data.to_dict("records"),"Sync to the HWDB",html.Div(f"Loaded {totalentry} Items from {upload_name}",style={"fontSize": "20px", "color": "red","font-family": "Arial, sans-serif"}), style, False, None, False

            except Exception as e:
                return dash.no_update, "Sync to the HWDB", html.Div(f"Error: {e}",style={"fontSize": "20px", "color": "red","font-family": "Arial, sans-serif"}), style, False, None, False


