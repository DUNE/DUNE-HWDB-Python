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

logger = config.getLogger(__name__)

# --- Load the JSON and reset button text after finish ---
def register_callbacks(app):
    @app.callback(
        [Output("data-store", "data", allow_duplicate=True),
         Output("load-json", "children"),
         Output("downloaded-output", "children", allow_duplicate=True), # The downloaded message
         Output("load-json", "style"),
         Output("load-json", "disabled")],
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
            return dash.no_update, "Sync to the HWDB", "", style, False
        
        #------------------------------------------
        # Case A: user clicked “Sync to the HWDB”
        #------------------------------------------
        if trig == "load-json":
            logger.info("[Sync] ⏳ Fetching data from HWDB…")
            
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




                
                #------------------------------------------------

                #resp = get_hwitems(user_string, size=99999)
                resp = get_hwitems(**args)
            
                totalentry = len(resp["data"])

                if len(resp["data"])>0:
                
                    # for Test Log
                    if testtype_string:

                        #with ThreadPoolExecutor(max_workers=50) as executor:
                        #    results = list(executor.map(lambda d: GETTestLog(d, testtype_string), resp["data"]))
                        #    data = load_data(results)

                        # Let's use the global, persistent HWDB session pool used by all other Sisyphus REST utilities:
                        from Sisyphus.RestApiV1 import Utilities as ra_util
                        executor = ra_util._executor
                        results = list(executor.map(lambda d: GETTestLog(d, testtype_string), resp["data"]))
                        data = load_data(results)
                        
                    else:
                        data = load_data(resp["data"])
                #------------------------------------------------
                # Filter unwanted columns
                unwanted_keys = [
                    "category", "link", "link_href", "link_rel", "status", "component_id",                            # for Item list
                    "ITEM: category", "ITEM: batch_id", "ITEM: batch_received", "ITEM: component_id",                 # for each Items
                    "ITEM: component_type_name", "ITEM: component_type_part_type_id", "ITEM: specs_version",          # for each Items
                    "TEST: id", "TEST: images", "TEST: link_href", "TEST: link_rel", "TEST: methods_0_rel",           # for each Tests
                    "TEST: methods_0_href", "TEST: test_spec_version", "TEST: test_type_id", "TEST: test_type_name"]  # for each Tests
                data = data.drop(columns=[c for c in data.columns if c in unwanted_keys], errors="ignore")
            
                # Sort the columns
                priority_item = ["part_id"             , "parent_part_id"      , "country_code"      , "institution_id"        , "institution_name"      ,
                                 "ITEM: part_id"       , "ITEM: parent_part_id", "ITEM: country_code", "ITEM: institution_id"  , "ITEM: institution_name", 
                                 "created"             , "creator_id"          , "creator_name"      , "creator_username"      , "manufacturer_id"       , "manufacturer_name",
                                 "ITEM: created"       , "ITEM: creator_id"    , "ITEM: creator_name", "ITEM: creator_username", "ITEM: manufacturer_id" , "ITEM: manufacturer_name",
                                 "serial_number"       , "location"            , "status_id"         , "status_name"           ,
                                 "ITEM: serial_number" , "ITEM: location"      , "ITEM: status_id"   , "ITEM: status_name"     ,
                                 "certified_qaqc"      , "qaqc_uploaded"       , "is_installed"      , "comments"              ,
                                 "ITEM: certified_qaqc", "ITEM: qaqc_uploaded" , "ITEM: is_installed", "ITEM: comments"
                ]
                priority_test = ["TEST: created"       , "TEST: creator_id"    , "TEST: creator_name", "TEST: creator_username", "TEST: comments"]
                # Group columns by prefix
                item_cols = sorted([c for c in data.columns if c.startswith("ITEM: ")])
                test_cols = sorted([c for c in data.columns if c.startswith("TEST: ")])
                other_cols = [c for c in data.columns if c not in item_cols + test_cols] # this is actually when a Test Type Name is not given
            
                # Combine in the following order:
                # Apply priority order within each group
                item_cols = (
                    [c for c in priority_item if c in item_cols] +
                    sorted([c for c in item_cols if c not in priority_item])
                )
                test_cols = (
                    [c for c in priority_test if c in test_cols] +
                    sorted([c for c in test_cols if c not in priority_test])
                )
                other_cols = (
                    [c for c in priority_item if c in other_cols] +
                    sorted([c for c in other_cols if c not in priority_item])
                )

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

                # Create subdirectory based on typeid
                if user_string:
                    sub_dir = os.path.join(working_dir, str(user_string))
                    os.makedirs(sub_dir, exist_ok=True)  # Create folder if it doesn't exist
                    save_dir = sub_dir  # redirect save target

                # Generate timestamped file name
                ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                pickle_filename = f"HWDB_downloaded_{user_string}_{ts}.pkl"
                if testtype_string:
                     pickle_filename = f"HWDB_downloaded_{user_string}_{testtype_string}_{ts}.pkl"
                pickle_path = Path(save_dir) / pickle_filename

                # Save the Pickle data
                try:
                    with open(pickle_path, "wb") as f:
                        #pickle.dump(resp, f)
                        pickle.dump(data, f)
                except Exception as e:
                    logger.error(f"[Sync] ⚠️ Failed to save JSON: {e}")


                return data.to_dict("records"),"Sync to the HWDB",html.Div(f"Loaded {totalentry} Items from the HWDB",style={"fontSize": "20px", "color": "red","font-family": "Arial, sans-serif"}), style, False
                    
            except Exception as e:
                return dash.no_update, "Sync to the HWDB", html.Div(f"Error: {e}",style={"fontSize": "20px", "color": "red","font-family": "Arial, sans-serif"}), style, False

        
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
                return data.to_dict("records"),"Sync to the HWDB",html.Div(f"Loaded {totalentry} Items from {upload_name}",style={"fontSize": "20px", "color": "red","font-family": "Arial, sans-serif"}), style, False

            except Exception as e:
                return dash.no_update, "Sync to the HWDB", html.Div(f"Error: {e}",style={"fontSize": "20px", "color": "red","font-family": "Arial, sans-serif"}), style, False


