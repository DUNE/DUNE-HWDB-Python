from dash import Input, Output, State, html, dcc, ctx, no_update
from dash.dependencies import Input, Output, State, MATCH
import dash
from dash.exceptions import PreventUpdate
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import base64, io, json, pickle
from datetime import datetime
from Sisyphus.Gui.Dashboard.utils.data_utils import load_data, GETTestLog
from Sisyphus.RestApiV1 import get_hwitem, get_hwitems, get_hwitem_locations, get_hwitem_image_list, get_image
from Sisyphus.Configuration import config
from pathlib import Path
import os
import re
import time
import threading
#import qrcode

logger = config.getLogger(__name__)

# ============================================================
#   GLOBAL SHIPMENT JOB REGISTRY (like Downloader)
# ============================================================
_shipment_jobs = {}   # jobid → {"processed", "total", "done", "error"}


# ============================================================
#   HELPERS
# ============================================================
def _combinedItemsLocs(itemDATA):
    """Fetch merged item + location info for a PID"""
    
    eachPID = itemDATA["part_id"]
    
    # Get item and location info
    resp_loca = get_hwitem_locations(eachPID)

    # Keep only certain keys keys
    each_item = {
        "pid": eachPID,
        #"institution"  : itemDATA["institution"],
        #"country"      : itemDATA["country_code"],
        #"manufacturer" : itemDATA["manufacturer"],
        "serial"       : itemDATA["serial_number"],
        "itemcomments" : itemDATA["comments"],
        "specs"        : itemDATA["specifications"],
        "compstatus"   : itemDATA["status"],
        "certified"    : itemDATA["certified_qaqc"],
        "uploaded"     : itemDATA["qaqc_uploaded"],
        "installed"    : itemDATA["is_installed"],
        "locations"    : resp_loca,
    }
    
    return each_item

def _run_shipment_worker(jobid, items):
    """Runs in background thread. Uses shared REST executor pool."""
    job = _shipment_jobs[jobid]
    try:
        #resp = get_hwitems(typeid, size=99999)
        #items = resp.get("data", [])
        
        job["total"] = len(items)

        from Sisyphus.RestApiV1 import Utilities as ra_util
        executor = ra_util._executor

        processed = 0
        for _ in executor.map(lambda d: _combinedItemsLocs(d), items):
            processed += 1
            job["processed"] = processed

        job["done"] = True

    except Exception as e:
        job["error"] = str(e)
        logger.error(f"[Shipment Worker] {e}")
        
def _fetch_shipments(typeid: str):
    """Used only in the sync completion stage"""
    
    # No Component Type ID was provided...
    if not typeid:
        return []
        
    try:
        resp = get_hwitems(typeid,size=99999)
        
        resp = resp["data"]

        if not isinstance(resp, list):
            logger.warning(f"[Shipment] get_hwitems() returned unexpected type: {type(resp)}")
            return []

        if not len(resp)>0:
            return []
        
        # Let's use the global, persistent HWDB session pool used by all other Sisyphus REST utilities:
        from Sisyphus.RestApiV1 import Utilities as ra_util
        executor = ra_util._executor
        results = list(executor.map(lambda d: _combinedItemsLocs(d), resp))

        return results

    except Exception as e:
        logger.error(f"[Shipment] _fetch_shipments failed: {e}")
        return []
    
# ============================================================
#   CALLBACKS
# ============================================================
def register_callbacks(app):

    # ---------------------------
    # Sync button - fetch + cache
    # ---------------------------

    @app.callback(
        [
            Output("fetch-shipments", "children"),
            Output("fetch-shipments", "style"),
            Output("fetch-shipments", "disabled"),
            Output("fetch-shipments-trigger", "data"),
            Output("shipment-total", "data"),
            Output("shipment-interval", "disabled"),
            Output("shipment-items-cache", "data"),
            Output("shipment-job-id", "data"),
            Output("shipment-memory-store", "data", allow_duplicate=True),
        ],
        Input("fetch-shipments", "n_clicks"),
        State("shipment-typeid", "value"),
        prevent_initial_call=True,
    )
    def show_syncing_shipments_feedback(n_clicks, typeid):
        """Immediately update the button to orange and disable it."""
        if not n_clicks:
            raise PreventUpdate

        # orange "syncing" style
        syncing_style = {
            "fontSize": "20px",
            "padding": "14px 32px",
            "backgroundColor": "#f39c12",  # orange
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "not-allowed",
            "transition": "all 0.2s ease-in-out",
            "marginRight": "50px",
            "gap": "15px",
        }

        # fetch list of items to know the total
        try:
            resp = get_hwitems(typeid, size=99999)
            items = resp.get("data", [])
            total = len(items)
            logger.info(f"[Shipment Sync] Total items = {total}")
        except Exception as e:
            logger.error(f"[Shipment Sync] Fetch failed: {e}")
            return "Error fetching shipments", syncing_style, False, None, None, True, None, None, None

        if not total:
            return "No Shipments found", syncing_style, False, None, 0, True, None, None, None

        # create a job id
        jobid = f"SHIP-{int(time.time()*1000)}"
        _shipment_jobs[jobid] = {
            "processed": 0,
            "total": total,
            "done": False,
            "error": None,
        }

        # background thread
        thread = threading.Thread(
            target=_run_shipment_worker,
            args=(jobid, items),
            daemon=True,
        )
        thread.start()

        logger.info("[Shipment] Shipment button clicked — showing 'Syncing...' feedback")
        
        return "Syncing to the HWDB...", syncing_style, True, jobid, total, False, items, jobid, {"last_typeid": typeid}

    # Pre-populate the input on startup
    @app.callback(
        Output("shipment-typeid", "value"),
        Input("shipment-memory-store", "data"),
        prevent_initial_call=False,
    )
    def preload_typeid(data):
        if not data:
            raise PreventUpdate
        return data.get("last_typeid")

    
    # --------------------------------------------------------
    # Poll background job status
    # --------------------------------------------------------
    @app.callback(
        Output("fetch-shipments", "children", allow_duplicate=True),
        Output("fetch-shipments", "style", allow_duplicate=True),
        Output("fetch-shipments", "disabled", allow_duplicate=True),
        Output("shipment-interval", "disabled", allow_duplicate=True),
        Input("shipment-interval", "n_intervals"),
        State("shipment-job-id", "data"),
        State("shipment-total", "data"),
        prevent_initial_call=True,
    )
    def update_shipment_button(_, jobid, total):
        if not jobid:
            raise PreventUpdate

        job = _shipment_jobs.get(jobid)
        if not job:
            return "Error: Job missing", None, False, True

        processed = job.get("processed", 0)
        done = job.get("done", False)
        err = job.get("error")

        if err:
            return f"Error: {err}", {"backgroundColor":"#e74c3c"}, False, True

        if not done:
            pct = int(processed * 100 / total) if total else 0
            style = {
                "fontSize": "20px",
                "padding": "14px 32px",
                "backgroundColor": "#f39c12",
                "color": "white",
                "border": "none",
                "borderRadius": "8px",
                "cursor": "not-allowed",
                "transition": "all 0.2s",
                "marginRight": "50px",
            }
            return f"{pct}% completed...", style, True, False

        # finished → restore original look
        style = {
            "fontSize": "20px",
            "padding": "14px 32px",
            "backgroundColor": "#4CAF50",
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "pointer",
            "marginRight": "50px",
        }

        # remove this job so no more ticks can reuse stale data
        _shipment_jobs.pop(jobid, None)

        return "Sync to the HWDB", style, False, True





    

    @app.callback(
        [
            Output("fetch-shipments-store", "data", allow_duplicate=True), 
            Output("shipment-table", "data", allow_duplicate=True),
            #Output("tg-cache", "data", allow_duplicate=True),
            Output("fetch-shipments", "children",allow_duplicate=True),
            Output("fetch-shipments", "style",allow_duplicate=True),
            Output("fetch-shipments", "disabled",allow_duplicate=True),
        ],    
        Input("fetch-shipments-trigger", "data"),
        State("shipment-typeid", "value"),
        #State("shipments-selected-pid", "data"),
        #State("tg-cache", "data"),
        prevent_initial_call=True,
    )

    def _sync_shipments(trigger_data,typeid):
        if not trigger_data:
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
            
        logger.info("[Shipment] fetch-shipments syncing...")


        data = _fetch_shipments(typeid)
        if not len(data)>0:
            return [], [], "Sync to the HWDB", style, False

        data = sorted(data, key=lambda d: d.get("pid", ""), reverse=True)

        shipment_table_data = []

        
        for eachpid in data:

            if len(eachpid["specs"])>0:
                try:
                    myorigin = eachpid["specs"][0]["DATA"]["Pre-Shipping Checklist"][8].get("Origin of this shipment")
                except:
                    myorigin = ""
            
            mylocation = ""
            myStatus   = ""
            if len(eachpid["locations"]["data"]):
                if eachpid["locations"]["data"][0]["location"]["id"] != 0:
                    mylocation = eachpid["locations"]["data"][0]["location"]["name"] # get the latest location
                    myStatus = "Delivered"
                else:
                    myStatus = eachpid["locations"]["data"][0]["location"]["name"]
                    mylocation = myorigin
                   
            # Loop over locations in each PID
            myShipped   = ""
            myShipper   = ""
            myReceived  = ""
            myReceiver  = ""
            
            for eachloc in eachpid["locations"]["data"]:
                # get the latest Shipped in case if there are multuiple
                # and the status id must be 0 (In-Transit)
                if myShipped == "" and eachloc.get("location", {}).get("id","") == 0:
                    ts = eachloc.get("arrived", "")
                    myShipped = ts.split("T")[0] # just grab the YYYY-MM-DD
                    myShipper = eachloc.get("creator", "")

                # get the latest Shipped in case if there are multuiple
                # and the status id must NOT be 0 (In-Transit)
                if myReceived == "" and eachloc.get("location", {}).get("id","") != 0:
                    ts = eachloc.get("arrived", "")
                    myReceived = ts.split("T")[0] # just grab the YYYY-MM-DD
                    myReceiver = eachloc.get("creator", "")

            if myReceived < myShipped:
                myReceived = ""
                myReceiver = ""

            # fill the two flags
            myCertified = ""
            myUploaded  = ""
            if eachpid["certified"] == True:
                myCertified = "✅"
            else:
                myCertified = "❌"
            if eachpid["uploaded"] == True:
                myUploaded = "✅"
            else:
                myUploaded = "❌"
                
            
            shipment_table_data.append({
                "box_pid"      : eachpid["pid"],
                "certified"    : myCertified,
                "docuploaded"  : myUploaded,
                "location"     : mylocation,
                "shipped_date" : myShipped,
                "received_date": myReceived,
                "shipper"      : myShipper,
                "receiver"     : myReceiver,
                "status"       : myStatus,
            })

            
        return data,shipment_table_data, "Sync to the HWDB", style, False


    
    # ──────────────────────────────────────────────
    # The 3 summary cards
    # ──────────────────────────────────────────────

    @app.callback(
        [
            Output("summary-total", "children"),
            Output("summary-transit", "children"),
            Output("summary-delivered", "children"),
        ],
        Input("shipment-table", "data"),  # reacts when table updates
        prevent_initial_call=True,
    )
    def update_shipment_summary(data):
        if not data or len(data) == 0:
            raise PreventUpdate

        total = len(data)
        in_transit = sum(1 for d in data if d.get("status", "").lower() == "in-transit")
        delivered = sum(1 for d in data if d.get("status", "").lower() == "delivered")

        logger.info(f"[Shipment Summary] Total={total}, In Transit={in_transit}, Delivered={delivered}")

        return (
            f"📦 Total Boxes: {total}",
            f"🚚 In Transit: {in_transit}",
            f"📍 Delivered: {delivered}",
        )


    # ──────────────────────────────────────────────
    # The deail info on the individual shipping boxes
    # ──────────────────────────────────────────────

    @app.callback(
        [
            Output("shipment-details-section", "style"),
            Output("shipment-history-table", "data"),
            Output("shipment-history-title", "children"),
            Output("subcomp-info-table", "data"),
            Output("info-box-qarep", "children"),
            Output("info-box-poc", "children"),
            Output("info-box-ori", "children"),
            Output("info-box-des", "children"),
            Output("info-box-dim", "children"),
            Output("info-box-wei", "children"),
            Output("info-box-ffn", "children"),
            Output("info-box-mod", "children"),
            Output("info-box-exd", "children"),
            Output("info-box-acn", "children"),
            Output("info-box-act", "children"),
            Output("info-box-vis", "children"),
            
            #Output("info-box-shippinglabel", "children"),
            #Output("info-box-shippinglabel", "style"),

            Output({"type": "download-button", "index": "shippinglabel"}, "children"),
            Output({"type": "download-button", "index": "shippinglabel"}, "style"),
            Output({"type": "image-id-store" , "index": "shippinglabel"}, "data"),

            Output({"type": "download-button", "index": "bol"}, "children"),
            Output({"type": "download-button", "index": "bol"}, "style"),
            Output({"type": "image-id-store" , "index": "bol"}, "data"),

            Output({"type": "download-button", "index": "proforma"}, "children"),
            Output({"type": "download-button", "index": "proforma"}, "style"),
            Output({"type": "image-id-store" , "index": "proforma"}, "data"),

            Output({"type": "download-button", "index": "approval"}, "children"),
            Output({"type": "download-button", "index": "approval"}, "style"),
            Output({"type": "image-id-store" , "index": "approval"}, "data"),

            Output("info-box-appwho", "children"),
            Output("info-box-apptime", "children"),
            Output("info-box-attached", "children"),
            Output("info-box-insured", "children"),

            Output("info-wh-sku", "children"),
            Output("info-wh-pal", "children"),
            Output("info-wh-tim", "children"),
            Output("info-wh-per", "children"),
            Output("info-wh-vis", "children"),

        ],
        Input("fetch-shipments-store", "data"),
        Input("shipment-table", "derived_viewport_selected_rows"),
        prevent_initial_call=True,
    )
    def show_details(table_data,selected_rows):
        if not selected_rows or not table_data:
            raise PreventUpdate

        idx = selected_rows[0]

        # Fill the title with the selected PID
        box_pid = table_data[idx]["pid"]

        # Fill the Shipment history table
        history = []
        for eachloc in table_data[idx]["locations"]["data"]:

            timestr = eachloc.get("arrived", "")
            try:
                dt = datetime.fromisoformat(timestr)
                shortertime = dt.strftime("%Y-%m-%d %H:%M")  # "2025-11-06 14:43"
            except Exception:
                shortertime = timestr  # fallback if malformed
            
            history.append({
                "date"    : shortertime,
                "person"  : eachloc.get("creator", ""),
                "location": eachloc.get("location", {}).get("name",""),
                "comments": eachloc.get("comments", ""),
            })
        # Sort descending by arrival date
        history = sorted(history, key=lambda d: d.get("arrived", ""), reverse=True)

        # GET Specifications
        subcomp_table_data = []
        specs_list = table_data[idx].get("specs", [])
        # Pre-shipping checklist
        qa_name     = ""
        qa_emails   = []
        poc_name    = ""
        poc_emails  = []
        qa_string   = "Consortium QA Rep: —"
        poc_string  = "POC: —"
        origin      = "Origin: —" 
        destination = "Destination: —"
        dimension   = "Dimension: —"
        weight      = "Weight: —"
        ffname      = "FF name: —"
        ffmode      = "Mode of Trans.: —"
        exdate      = "Expected Arrival Date: —"
        ack_name    = "Acknowledged by who?: —"
        ack_time    = "When acknowledged?: —"
        visinspec   = "Visual Inspection: —"
        labelID     = ""
        color       = "#b0b0b0"  # default gray button
        if specs_list and isinstance(specs_list[0], dict):
            data_block = specs_list[0].get("DATA", {})
            if isinstance(data_block, dict):

                # Fill the sub-component table
                subpids = data_block.get("SubPIDs", [])
                for eachsub in subpids:
                    if not isinstance(eachsub, dict) or not eachsub:
                        continue  # skip anything unexpected

                    # Extract the single key/value pair
                    key, subpid = list(eachsub.items())[0]
                    subtext = key  # e.g., "Test Type 003 (My Sub Comp 1)"

                    # Parse the text using regex
                    match = re.match(r"^(.*?)\s*\((.*?)\)$", subtext)
                    if match:
                        comptype, subfunc = match.groups()
                        subcomp_table_data.append({
                            "subtype": comptype.strip(),
                            "subfunc": subfunc.strip(),
                            "subpid": subpid.strip(),
                            })
                        #logger.info(f"Parsed: {comptype}, {subfunc}, {subpid}")
                    else:
                        # fallback if parentheses missing
                        subcomp_table_data.append({
                            "subtype": subtext.strip(),
                            "subfunc": "",
                            "subpid": subpid.strip(),
                        })
                        logger.warning(f"⚠ Unmatched SubPID format: {subtext}")

                # Pre-shipping checklist
                preshipping = data_block.get("Pre-Shipping Checklist", [])
                for eachpre in preshipping:
                    if not isinstance(eachpre, dict) or not eachpre:
                        continue  # skip anything unexpected
                    # QA Rep
                    if "Consortium QA Rep name" in eachpre:
                        qa_name = eachpre["Consortium QA Rep name"]
                    elif "Consortium QA Rep Email" in eachpre:
                        emails = eachpre["Consortium QA Rep Email"]
                        if isinstance(emails, list):
                            qa_emails.extend(emails)
                        elif isinstance(emails, str):
                            qa_emails.append(emails)
                    # PoC
                    if "POC name" in eachpre:
                        poc_name = eachpre["POC name"]
                    elif "POC Email" in eachpre:
                        pemails = eachpre["POC Email"]
                        if isinstance(pemails, list):
                            poc_emails.extend(pemails)
                        elif isinstance(emails, str):
                            poc_emails.append(pemails)
                    # Origin
                    if "Origin of this shipment" in eachpre:
                        origin = f"Origin: {eachpre["Origin of this shipment"]}"
                    # Destination
                    if "Destination of this shipment" in eachpre:
                        destination = f"Destination: {eachpre["Destination of this shipment"]}"
                    # Dimension
                    if "Dimension of this shipment" in eachpre:
                        dimension = f"Dimension: {eachpre["Dimension of this shipment"]}"
                    # Weight
                    if "Weight of this shipment" in eachpre:
                        weight = f"Weight: {eachpre["Weight of this shipment"]}"
                    # FF name
                    if "Freight Forwarder name" in eachpre:
                        ffname = f"FF name: {eachpre["Freight Forwarder name"]}"
                    # FF mode
                    if "Mode of Transportation" in eachpre:
                        ffmode = f"Mode of Trans.: {eachpre["Mode of Transportation"]}"
                    # Expected Arrival Date
                    if "Expected Arrival Date (CST)" in eachpre:
                        timestr = eachpre["Expected Arrival Date (CST)"]
                        try:
                            dt = datetime.fromisoformat(timestr)
                            shortertime = dt.strftime("%Y-%m-%d %H:%M")  # "2025-11-06 14:43"
                        except Exception:
                            shortertime = timestr  # fallback if malformed
                        exdate = f"Expected Arrival Date: {shortertime}"
                    # Acknowledged by who?
                    if "FD Logistics team acknowledgment (name)" in eachpre:
                        ack_name = f"Acknowledged by who?: {eachpre["FD Logistics team acknowledgment (name)"]}"
                    # Acknowledged when?
                    if "FD Logistics team acknowledgment (date in CST)" in eachpre:
                        timestr = eachpre["FD Logistics team acknowledgment (date in CST)"]
                        try:
                            dt = datetime.fromisoformat(timestr)
                            shortertime = dt.strftime("%Y-%m-%d %H:%M")  # "2025-11-06 14:43"
                        except Exception:
                            shortertime = timestr  # fallback if malformed
                        ack_time = f"When acknowledged?: {shortertime}"
                    # Visual Inspection
                    if "Visual Inspection (YES = no damage)" in eachpre:
                        if eachpre["Visual Inspection (YES = no damage)"] == "YES":
                            visinspec = f"Acknowledged by who?: Looks fine"
                        else:
                            visinspec = f"Acknowledged by who?: {eachpre["Visual Inspection Damage"]}"
                    # Shipping Label ID
                    if "Image ID for this Shipping Sheet" in eachpre:
                        labelID = eachpre["Image ID for this Shipping Sheet"] or ""
                        if len(labelID)>0:
                            color = "#4CAF50"  # green
                        else:
                            color = "#b0b0b0"  # default gray
           
                # Combine into final formatted string
                # Ensure qa_name is a non-empty string
                if not isinstance(qa_name, str) or not qa_name.strip():
                    qa_name = ""
                # Ensure qa_emails is a proper list of non-empty strings
                if not isinstance(qa_emails, list):
                    qa_emails = []
                else:
                    qa_emails = [str(e).strip() for e in qa_emails if isinstance(e, str) and e.strip()]
                # Build final formatted string
                if qa_name or qa_emails:
                    if qa_name and qa_emails:
                        qa_string = f"Consortium QA Rep: {qa_name} ({', '.join(qa_emails)})"
                    elif qa_name:
                        qa_string = f"Consortium QA Rep: {qa_name}"
                    elif qa_emails:
                        qa_string = f"Consortium QA Rep: ({', '.join(qa_emails)})"
                    else:
                        qa_string = "Consortium QA Rep: —"

                # Ensure qa_name is a non-empty string
                if not isinstance(poc_name, str) or not poc_name.strip():
                    qa_name = ""
                # Ensure qa_emails is a proper list of non-empty strings
                if not isinstance(poc_emails, list):
                    poc_emails = []
                else:
                    poc_emails = [str(e).strip() for e in poc_emails if isinstance(e, str) and e.strip()]
                # Build final formatted string
                if poc_name or poc_emails:
                    if poc_name and poc_emails:
                        poc_string = f"POC: {poc_name} ({', '.join(poc_emails)})"
                    elif poc_name:
                        poc_string = f"POC: {poc_name}"
                    elif poc_emails:
                        poc_string = f"POC: ({', '.join(poc_emails)})"
                    else:
                        poc_string = "POC: —"





                        

        # Shipping checklist
        bolID    = ""
        bolcolor = "#b0b0b0"  # default gray button
        proID    = ""
        procolor = "#b0b0b0"  # default gray button
        appID    = ""
        appcolor = "#b0b0b0"  # default gray button
        finappn  = "Final approved by who?: —"
        finappt  = "Final approved when?: —"
        attached = "Shipping label attached?: —"
        insured  = "Shipment insured?: —"
        if specs_list and isinstance(specs_list[0], dict):
            data_block = specs_list[0].get("DATA", {})
            if isinstance(data_block, dict):
                
                shipping = data_block.get("Shipping Checklist", [])
                for eachshi in shipping:
                    if not isinstance(eachshi, dict) or not eachshi:
                        continue  # skip anything unexpected
                        
                    # BoL
                    if "Image ID for BoL" in eachshi:
                        bolID = eachshi["Image ID for BoL"] or ""
                        if len(bolID)>0:
                            bolcolor = "#4CAF50"  # green
                        else:
                            bolcolor = "#b0b0b0"  # default gray
                    # Proforma Invoice
                    if "Image ID for Proforma Invoice" in eachshi:
                        proID = eachshi["Image ID for Proforma Invoice"] or ""
                        if len(proID)>0:
                            procolor = "#4CAF50"  # green
                        else:
                            procolor = "#b0b0b0"  # default gray
                    # Final approval message
                    if "Image ID for the final approval message" in eachshi:
                        appID = eachshi["Image ID for the final approval message"] or ""
                        if len(appID)>0:
                            appcolor = "#4CAF50"  # green
                        else:
                            appcolor = "#b0b0b0"  # default gray
                    # Final approved by who?
                    if "FD Logistics team final approval (name)" in eachshi:
                        finappn = f"Final approved by who?: {eachshi["FD Logistics team final approval (name)"]}"
                    # Final approved when?
                    if "FD Logistics team final approval (date in CST)" in eachshi:
                        timestr = eachshi["FD Logistics team final approval (date in CST)"]
                        try:
                            dt = datetime.fromisoformat(timestr)
                            shortertime = dt.strftime("%Y-%m-%d %H:%M")  # "2025-11-06 14:43"
                        except Exception:
                            shortertime = timestr  # fallback if malformed
                        finappt  = f"Final approved when?: {shortertime}"
                    # Label attached?
                    if "DUNE Shipping Sheet has been attached" in eachshi:
                        if eachshi["DUNE Shipping Sheet has been attached"]:
                            attached = "Shipping label attached?: ✅ Yes!"
                        else:
                            attached = "Shipping label attached?: ❌ No!"
                    # Insured?
                    if "This shipment has been adequately insured for transit" in eachshi:
                        if eachshi["This shipment has been adequately insured for transit"]:
                            insured = "Shipment insured?: ✅ Yes!"
                        else:
                            insured = "Shipment insured?: ❌ No!"


        # Warehouse
        sku      = "SKU: —"
        pallet   = "PalletID: —"
        scanned  = "Scanned date/time: —"
        whreceiv = "Person received: —"
        whvisual = "Visual inspection: —"
        if specs_list and isinstance(specs_list[0], dict):
            data_block = specs_list[0].get("DATA", {})
            if isinstance(data_block, dict):
                
                warehouse = data_block.get("Warehouse", [])
                for eachwh in warehouse:
                    if not isinstance(eachwh, dict) or not eachwh:
                        continue  # skip anything unexpected
                        
                    # SKU
                    if "SKU" in eachwh:
                        sku = f"SKU: {eachwh["SKU"]}"
                    # PalletID
                    if "PalletID" in eachwh:
                        pallet = f"PalletID: {eachwh["PalletID"]}"
                    # Scanned date/time
                    if "Scanned date/time" in eachwh:
                        timestr = eachwh["Scanned date/time"]
                        try:
                            dt = datetime.fromisoformat(timestr)
                            shortertime = dt.strftime("%Y-%m-%d %H:%M")  # "2025-11-06 14:43"
                        except Exception:
                            shortertime = timestr  # fallback if malformed
                        scanned = f"Scanned date/time: {shortertime}"
                    # Person received
                    if "Person received" in eachwh:
                        whreceiv = f"Person received: {eachwh["Person received"]}"
                    # Visual inspection
                    if "Visual inspection" in eachwh:
                        whvisual = f"Visual inspection: {eachwh["Visual inspection"]}"

                            
                        
        #logger.info(f"[show_details] labelID={labelID!r}, bolID={bolID!r}")

        return (
            {"display": "flex", "gap": "20px", "justifyContent": "space-between"},  # make section visible
            history,
            f"Shipment History for {box_pid}",
            subcomp_table_data,
            qa_string,
            poc_string,
            origin,
            destination,
            dimension,
            weight,
            ffname,
            ffmode,
            exdate,
            ack_name,
            ack_time,
            visinspec,
            "⬇️ Download Shipping Label",  # keep button text
            {"backgroundColor": color},
            labelID,
            "⬇️ Download Bill of Lading",  # keep button text
            {"backgroundColor": bolcolor},
            bolID,
            "⬇️ Download Proforma Invoice",  # keep button text
            {"backgroundColor": procolor},
            proID,
            "⬇️ Download final approval message",  # keep button text
            {"backgroundColor": appcolor},
            appID,
            finappn,
            finappt,
            attached,
            insured,
            sku,
            pallet,
            scanned,
            whreceiv,
            whvisual,
        )



    # Download Images
    @app.callback(
        Output({"type": "image-status-store", "index": MATCH}, "data"),  # dummy output
        Input({"type": "download-button", "index": MATCH}, "n_clicks"),
        State({"type": "image-id-store", "index": MATCH}, "data"),
        
        State("shipment-typeid", "value"),
        Input("fetch-shipments-store", "data"),
        Input("shipment-table", "derived_viewport_selected_rows"),
        prevent_initial_call=True,
    )
    def download_image(n_clicks, label_id, typeid, table_data,selected_rows):
        """Triggered when the 'Download' button is clicked."""
        if not n_clicks:
            raise PreventUpdate

        if not selected_rows or not table_data:
            raise PreventUpdate

        if not label_id or not isinstance(label_id, str) or not label_id.strip():
            logger.warning("[Download an Image] No valid ID found — nothing to download.")
            #return {"backgroundColor": "#b0b0b0"}  # keep gray
            return dash.no_update  # keep dash happy

        try:

            idx = selected_rows[0]
            box_pid = table_data[idx]["pid"]

            logger.info(f"[Download an Image] Downloading image for PID={box_pid}, ID={label_id}")

            # Get list of images
            resp=get_hwitem_image_list(box_pid)
            filename = None
            for image in resp["data"]:
                if image.get("image_id") == label_id:
                    filename = image.get("image_name")
                    break
            
            if not filename:
                raise RuntimeError("Image name not found in list response")
               
            # Determine save directory
            pref_file = Path(config.active_profile.profile_dir) / "dash_user_preferences.txt"
            working_dir = Path(pref_file.read_text().strip()) if pref_file.exists() else Path.cwd()
            if not working_dir.is_dir():
                working_dir = Path.cwd()

            # Create subdirectory based on typeid
            sub_dir = working_dir / str(typeid)
            sub_dir.mkdir(parents=True, exist_ok=True)
            image_path = sub_dir / filename

            # Perform the download
            get_image(label_id, write_to_file=image_path)

            logger.info(f"[Download an Image] Saved to {image_path}")

            return dash.no_update  # keep dash happy

        except Exception as e:
            logger.error(f"[Download an Image] Failed: {e}")
            #return {"backgroundColor": "#e74c3c"}
            return {"status": "error", "error": str(e)}




    # 1) click-anywhere maps active cell -> selected_rows
    # Click Anywhere in a row to Select
    @app.callback(
        Output("shipment-table", "selected_rows"),
        Input("shipment-table", "active_cell"),
        prevent_initial_call=True,
    )
    def sync_active_to_selected(active_cell):
        """When user clicks any cell, select that entire row."""
        if active_cell:
            
            return [active_cell["row"]]
        return []

    # 2) style_data_conditional driven by selected_rows to color the whole row
    @app.callback(
        Output("shipment-table", "style_data_conditional"),
        Input("shipment-table", "selected_rows"),
        State("shipment-table", "data"),
    )
    def highlight_entire_row(selected_rows, table_data):
        base_styles = [
            {"if": {"filter_query": "{Status} eq 'Delivered'"}, "backgroundColor": "#C8E6C9"},
            {"if": {"filter_query": "{Status} eq 'In Transit'"}, "backgroundColor": "#FFF9C4"},
        ]

        if not selected_rows:
            return base_styles

        # highlight entire selected row(s)
        for i in selected_rows:
            base_styles.append({
                "if": {"row_index": i},
                "backgroundColor": "#D1E9FF",
                "border": "1px solid #4A90E2",
            })
        return base_styles
    
 
