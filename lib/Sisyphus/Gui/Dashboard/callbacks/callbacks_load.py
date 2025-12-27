from dash import Input, Output, State, html, dcc, ctx
import dash
from dash.exceptions import PreventUpdate
import pandas as pd
from Sisyphus.RestApiV1 import Utilities as ra_util
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

def normalize_scalar_lists(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in df.columns:
        series = df[col]

        if series.apply(lambda v: isinstance(v, list)).any():
            scalar_col = f"{col}__scalar"

            df[scalar_col] = series.apply(
                lambda v: v[0] if isinstance(v, list) and len(v) == 1 else None
            )

            # force numeric dtype!!
            df[scalar_col] = pd.to_numeric(df[scalar_col], errors="coerce")

    return df
    
    #def norm(v):
    #    if isinstance(v, list):
    #        return v[0] if len(v) == 1 else None
    #    return v

    #return df.applymap(norm)

def _plot_sync_worker(job_id):
    
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

        # --- Fetch Test Data (TestLog) per item (PROGRESS LOOP) ---
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
        data = normalize_scalar_lists(data)

        # --- Drop unwanted keys ---
        unwanted_keys = [
            "category","link","link_href","link_rel","status","component_id",
            "ITEM: category","ITEM: batch_id","ITEM: batch_received","ITEM: component_id",
            "ITEM: component_type_name","ITEM: component_type_part_type_id","ITEM: specs_version",
            "TEST: id","TEST: images","TEST: link_href","TEST: link_rel","TEST: methods_0_rel",
            "TEST: methods_0_href","TEST: test_spec_version","TEST: test_type_id","TEST: test_type_name",
        ]
        data = data.drop(columns=[c for c in data.columns if c in unwanted_keys], errors="ignore")

        # --- Sort columns ---
        priority_item = [
            "part_id"             , "parent_part_id"      , "country_code"      , "institution_id"        , "institution_name"      ,
            "ITEM: part_id"       , "ITEM: parent_part_id", "ITEM: country_code", "ITEM: institution_id"  , "ITEM: institution_name", 
            "created"             , "creator_id"          , "creator_name"      , "creator_username"      , "manufacturer_id"       , "manufacturer_name",
            "ITEM: created"       , "ITEM: creator_id"    , "ITEM: creator_name", "ITEM: creator_username", "ITEM: manufacturer_id" , "ITEM: manufacturer_name",
            "serial_number"       , "location"            , "status_id"         , "status_name"           ,
            "ITEM: serial_number" , "ITEM: location"      , "ITEM: status_id"   , "ITEM: status_name"     ,
            "certified_qaqc"      , "qaqc_uploaded"       , "is_installed"      , "comments"              ,
            "ITEM: certified_qaqc", "ITEM: qaqc_uploaded" , "ITEM: is_installed", "ITEM: comments"
        ]
        priority_test = ["TEST: created"       , "TEST: creator_id"    , "TEST: creator_name", "TEST: creator_username", "TEST: comments"]

        item_cols = sorted([c for c in data.columns if c.startswith("ITEM: ")])
        test_cols = sorted([c for c in data.columns if c.startswith("TEST: ")])
        other_cols = [c for c in data.columns if c not in item_cols + test_cols]

        # Combine in the following order:
        # Apply priority order within each group
        item_cols = [c for c in priority_item if c in item_cols] + sorted([c for c in item_cols if c not in priority_item])
        test_cols = [c for c in priority_test if c in test_cols] + sorted([c for c in test_cols if c not in priority_test])
        other_cols = [c for c in priority_item if c in other_cols] + sorted([c for c in other_cols if c not in priority_item])

         # Final column order
        sorted_cols = (
            item_cols +
            test_cols +
            other_cols
        )

        # Remove possible duplicates while keeping order
        sorted_cols = list(dict.fromkeys(sorted_cols))

        # Reorder the DataFrame
        data = data[sorted_cols]

        #--- Also, save the loaded data locally ---
        # Determine working directory
        pref_file = Path(config.active_profile.profile_dir) / "dash_user_preferences.txt"
        if pref_file.exists():
            working_dir = pref_file.read_text().strip()
            if not os.path.isdir(working_dir):
                working_dir = os.getcwd()
        else:
            working_dir = os.getcwd()

        # Create subdirectory based on typeid, create one if it doesn't exist
        save_dir = Path(working_dir) / typeid
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamped file name
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pickle_filename = f"HWDB_downloaded_{typeid}_{ts}.pkl"
        if testtype:
            pickle_filename = f"HWDB_downloaded_{typeid}_{testtype}_{ts}.pkl"
        pickle_path = save_dir / pickle_filename
        
        # Save the Pickle data
        with open(pickle_path, "wb") as f:
            #pickle.dump(data, f)
            pickle.dump(data.copy(), f, protocol=pickle.HIGHEST_PROTOCOL)

        # --- Store result & mark done ---
        payload = data.to_dict("records")

        # payload size & shape (CRITICAL)
        try:
            json_size_mb = len(json.dumps(payload)) / 1e6
        except Exception as e:
            json_size_mb = -1
            logger.error(f"JSON size computation failed: {e}")

        logger.warning(
            f"[DATA-STORE PAYLOAD] rows={len(payload)}, "
            f"cols={len(data.columns)}, "
            f"json_size≈{json_size_mb:.2f} MB"
        )



        # Avoid to push full data into dcc.store.
        #job["data"] = payload
        job["data_path"] = str(pickle_path) # Instead, save only a reference
        job["columns"] = list(data.columns)
        job["done"] = True


        #job["finished_at"] = time.time()
    except Exception as e:
        job["error"] = str(e)
        job["done"] = True



# --- Load the JSON and reset button text after finish ---
def register_callbacks(app):

    # --------------------------------------------------------
    # Poll background job status
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
            Output("sync-status", "data", allow_duplicate=True),
        ],
        Input("plot-sync-interval", "n_intervals"),
        State("plot-sync-job-id", "data"),
        prevent_initial_call=True,
    )
    def update_sync_progress(n, job_id):

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

        # cleanup old jobs (older than 60s) to avoid possible memory leaks without breaking intervals
        now = time.time()
        for jid, j in list(_plot_jobs.items()):
            if j.get("finalized") and now - j.get("finished_at", now) > 60:
                _plot_jobs.pop(jid, None)

        
        if not job_id or job_id not in _plot_jobs:
            raise PreventUpdate

        job = _plot_jobs[job_id]

        if not job:
            raise PreventUpdate

        # if job was already finalized and rendered, stop forever
        if job.get("finalized"):

            meta = {
                "path": job["data_path"],
                "columns": job["columns"],
            }

            logger.info(f"[REAL FINAL UI] meta keys={list(meta.keys())}, cols={len(job['columns'])}")

            msg_final = html.Div(
                f"Loaded {job['total']} Items from the HWDB",
                style={"fontSize": "20px", "color": "red"}
            )

            
            #total_final = job["total"]
            #data_final = list(job.get("data", []))
            #columns_final = job.get("columns", [])
            #logger.info(f"[REAL FINAL UI] rows={len(data_final)}, cols={len(columns_final)}")
            #msg_final = html.Div(
            #    f"Loaded {total_final} Items from the HWDB",
            #    style={"fontSize": "20px", "color": "red"}
            #)

            #raise PreventUpdate
            #return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, True, dash.no_update
            #return "Sync to the HWDB", green, dash.no_update, dash.no_update, dash.no_update, True, dash.no_update # works
            #return "Sync to the HWDB", green, False, dash.no_update, dash.no_update, True, dash.no_update  # works
            #return "Sync to the HWDB", green, False, dash.no_update, msg_final, True, dash.no_update # works

            # Update the button and message now
            return "Sync to the HWDB", green, False, meta, msg_final, True, {"done": True, "ts": time.time()} # works
            #return "Sync to the HWDB", green, False, data_final, msg_final, True, {"done": True, "ts": time.time()}
            #return (
            #    "Sync to the HWDB",
            #    green,
            #    False,
            #    data_final,
            #    msg_final,
            #    True, # disable interval AND render green in same tick
            #    {"done": True, "ts": time.time()},   # sync-status
            #)


        
        processed = job["processed"]
        total = job["total"]
        done = job.get("done", False)
        err = job.get("error")
        pct = int(100 * processed / total) if total else 0



        
        # update % text while job is running
        #if not job["done"]:
        if not done:
        #if not job["done"] or job.get("ui_done") is True:
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
                {"done": False, "ts": time.time()},   # sync-status
            )

        
        # job finished → FINAL render + stop interval
        #data = list(job.get("data", []))
        # Only the metadata
        data = {
            "path": job["data_path"],
            "columns": job["columns"],
        }
        columns = job.get("columns", [])
        logger.info(f"[FINAL UI] rows={len(data)}, cols={len(columns)}")
        msg = html.Div(
            f"Loaded {total} Items from the HWDB",
            style={"fontSize": "20px", "color": "red"}
        )

       


        job["finalized"] = True
        job["finished_at"] = time.time()

        # cleanup job + stop interval
        #_plot_jobs.pop(job_id, None)


        #return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, True, dash.no_update

        # Update the data first. Update the UI (the button and the message later)
        return dash.no_update, dash.no_update, dash.no_update, data, dash.no_update, False, {"done": False, "ts": time.time()},
        #return (
        #    "Sync to the HWDB",
        #    green,
        #    False,
        #    data,
        #    msg,
        #    True, # disable interval AND render green in same tick
        #    {"done": True, "ts": time.time()},   # sync-status
        #)

    # --------------------------------------------------------
    # Download DATA
    # --------------------------------------------------------
    @app.callback(
        [Output("data-store", "data", allow_duplicate=True),
         #Output("load-json", "children", allow_duplicate=True), #
         Output("downloaded-output", "children", allow_duplicate=True), # The downloaded message
         #Output("load-json", "style", allow_duplicate=True), #
         #Output("load-json", "disabled", allow_duplicate=True), #
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

        # Green
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
            raise PreventUpdate
        
        # No Component Type ID was provided...
        if trig in ("load-json", "upload-json") and not user_string:
        #if not user_string:
            return dash.no_update,                     "",               None, dash.no_update, # do NOT touch interval
            #return dash.no_update, "Sync to the HWDB", "", style, False, None, False,
        

        
        #------------------------------------------
        # Case A: user clicked “Sync to the HWDB”
        #------------------------------------------
        if trig == "load-json" and ctx.triggered_id == "load-json":
        #if trig == "load-json":
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
                    args["part_id"] = pre_pid
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


                # Register job
                job_id = f"PLOT-{int(time.time()*1000)}"
                global _plot_jobs
                _plot_jobs[job_id] = {
                    "processed": 0,
                    "total": 0,
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


                    
             
                #return dash.no_update, "0% completed...", "", orange, True, job_id, False,
                return (
                    #[],                 # data-store, initialize explicitly
                    dash.no_update,
                    #dash.no_update,     # button text
                    dash.no_update,     # downloaded-output
                    #dash.no_update,     # style
                    #dash.no_update,     # disabled
                    job_id,             # plot-sync-job-id
                    False,              # enable interval ONLY on true click
                )

            except Exception as e:
                logger.error(f"[Sync] ERROR while preparing sync job: {e}")
                red = style.copy()
                red["backgroundColor"] = "#FF0000"
                #return dash.no_update, "Sync to the HWDB", html.Div(
                #    f"Error: {e}",
                #    style={"fontSize": "20px", "color": "red"}
                #    ), red, False, None, False,
                return dash.no_update, html.Div(
                    f"Error: {e}",
                    style={"fontSize": "20px", "color": "red"}
                    ), None, dash.no_update, # do NOT touch interval
        
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
                    df = pickle.loads(decoded)
                elif ext in [".csv"]:
                    # --- CSV ---
                    df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
                else:
                    return dash.no_update, f"⚠️ Unsupported file type: {ext}", None, dash.no_update

                # Save file to a temp / working location
                pref_file = Path(config.active_profile.profile_dir) / "dash_user_preferences.txt"
                working_dir = pref_file.read_text().strip() if pref_file.exists() else os.getcwd()
                save_path = Path(working_dir) / upload_name

                with open(save_path, "wb") as f:
                    pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)

                meta = {
                    "path": str(save_path),
                    "columns": list(df.columns),
                }

                
                #totalentry = len(data)

                # Convert to JSON for storage
                #return data.to_dict("records"),"Sync to the HWDB",html.Div(f"Loaded {totalentry} Items from {upload_name}",style={"fontSize": "20px", "color": "red","font-family": "Arial, sans-serif"}), style, False, None, False,
                #return data.to_dict("records"),html.Div(f"Loaded {totalentry} Items from {upload_name}",style={"fontSize": "20px", "color": "red","font-family": "Arial, sans-serif"}), None, dash.no_update, # do NOT touch interval

                return (
                    meta,
                    html.Div(
                        f"Loaded {len(df)} Items from {upload_name}",
                        style={"fontSize": "20px", "color": "red", "font-family": "Arial, sans-serif"},
                    ),
                    None,
                    dash.no_update,
                )

            

            except Exception as e:
                #return dash.no_update, "Sync to the HWDB", html.Div(f"Error: {e}",style={"fontSize": "20px", "color": "red","font-family": "Arial, sans-serif"}), style, False, None, False,
                return dash.no_update, html.Div(f"Error: {e}",style={"fontSize": "20px", "color": "red","font-family": "Arial, sans-serif"}), None, dash.no_update, # do NOT touch interval

            
       
