from dash import Input, Output, State, ALL, no_update, html, dcc, ctx
from dash.exceptions import PreventUpdate

import pandas as pd
import json
from datetime import datetime
import os
import time
import threading
from pathlib import Path

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.RestApiV1 import get_hwitem_test, get_hwitems
from Sisyphus.RestApiV1 import get_hwitem_image_list, get_component_type_image_list, get_image
from Sisyphus.Gui.Dashboard.utils.json_tree import render_json_tree
from concurrent.futures import as_completed
from Sisyphus.RestApiV1 import Utilities as ra_util
pool = ra_util._executor  # shared thread pool

# CSV / JSON helpers
from Sisyphus.Gui.Dashboard.utils.downloader_csv import (
    find_array_paths,
    build_csv_rows_for_entry,
)
from Sisyphus.Gui.Dashboard.utils.downloader_json import (
    build_allowed_tree,
    build_json_for_entry,
)


# NODES WE WANT TO HIDE FROM THE SCHEMA TREE
HIDDEN_SCHEMA_KEYS = {
    "id",
    "images",
    "link",
    "link.href",
    "link.rel",
    "methods",
    "methods[].href",
    "methods[].rel",
    "test_spec_version",
}


# ------------------------------------------------------------
# Background job registry
# ------------------------------------------------------------
_download_jobs = {}  # job_id (dict) with state for Test Data
_binary_jobs = {}  # job_id : {total, processed, done, error}

ORIGINAL_BUTTON_STYLE = {
    "fontSize": "20px",
    "padding": "14px 32px",
    "backgroundColor": "#FF5722",  # original orange
    "color": "white",
    "border": "none",
    "borderRadius": "8px",
    "cursor": "pointer",
    "textAlign": "center",
    "margin": "0 auto",
}

def run_download_job(job_id, pids, fields, testname, fmt, workdir, type_id):
    """
    Runs in a background thread.
    Fetches test entries and builds either CSV rows or nested JSON
    using the helper modules, then saves the final file.
    """
    job = _download_jobs[job_id]
    job["status"] = "running"
    total = len(pids)
    job["total"] = total
    job["processed"] = 0
    job["message"] = "Starting..."
    job["filename"] = None

    pool = ra_util._executor  # USE THE SHARED EXECUTOR
    
    # Precompute helpers depending on format
    if fmt == "csv":
        array_paths = find_array_paths(fields)
        rows = []
        logger.info(f"[DL-JOB {job_id}] ARRAY PATHS = {array_paths}")
    else:
        allowed_tree = build_allowed_tree(fields)
        nested = []
        logger.info(f"[DL-JOB {job_id}] Allowed tree built for JSON export")

    # --- Fetch a single PID test entry ---
    def fetch_entry(pid):
        try:
            resp = get_hwitem_test(pid, testname, history=False)
            entry = resp["data"][0] if resp.get("data") else None
            return pid, entry
        except Exception as e:
            logger.error(f"[DL-JOB {job_id}] Could not fetch {pid}: {e}")
        return pid, None

    try:
        futures = {pool.submit(fetch_entry, pid): pid for pid in pids}
        
        #for idx, pid in enumerate(pids):
        for idx, future in enumerate(as_completed(futures)):
            pid = futures[future]
            job["processed"] = idx + 1
            job["message"] = f"Downloading {pid}..."

            pid, entry = future.result()
            
            if not entry:
                continue

            # --- Accumulate data ---
            if fmt == "csv":
                entry_rows = build_csv_rows_for_entry(entry, pid, fields, array_paths)
                rows.extend(entry_rows)
            else:
                obj = build_json_for_entry(entry, pid, allowed_tree)
                nested.append(obj)

            # Allow other threads some breathing room
            time.sleep(0)

        # ---- Save file ----
        if fmt == "csv" and not rows:
            job["status"] = "error"
            job["message"] = "No valid data found (CSV)."
            return

        if fmt == "json" and not nested:
            job["status"] = "error"
            job["message"] = "No valid data found (JSON)."
            return

        ts = time.strftime("%Y-%m-%d_%H-%M-%S")
        safe = testname.replace(" ", "_")
        filename = f"{type_id}_{safe}_{ts}.{fmt}"
        folder = os.path.join(workdir, type_id)
        os.makedirs(folder, exist_ok=True)
        fullpath = os.path.join(folder, filename)

        if fmt == "csv":
            pd.DataFrame(rows).to_csv(fullpath, index=False)
        else:
            with open(fullpath, "w") as fp:
                json.dump(nested, fp, indent=2)

        job["status"] = "done"
        job["message"] = f"File saved: {type_id}/{filename}"
        job["filename"] = fullpath

        logger.info(f"[DL-JOB {job_id}] Completed. {fullpath}")

    except Exception as e:
        logger.exception(f"[DL-JOB {job_id}] ERROR during download job")
        job["status"] = "error"
        job["message"] = f"ERROR: {e}"


# for Binaries...
def _binary_download_worker(job_id, selected_ids, id_to_meta, images_dir):
    """Runs in a background thread and downloads files one by one."""
    job = _binary_jobs[job_id]
    total = job["total"]
    processed = 0

    for img_id in selected_ids:
        meta = id_to_meta.get(img_id)
        if not meta:
            job["error"] = f"Missing metadata for image_id={img_id}"
            break

        filename = meta.get("image_name") or f"{img_id}.bin"
        target_path = images_dir / filename

        try:
            logger.info(f"[Binaries] Downloading {img_id} → {target_path}")
            get_image(img_id, write_to_file=target_path)
            processed += 1
            job["processed"] = processed
        except Exception as e:
            logger.error(f"[Binaries] Failed to download {img_id}: {e}")
            job["error"] = f"{filename}: {e}"
            break

    job["done"] = True if job.get("error") is None else False

        
def _prune_schema(data, hidden):
    """
    Recursively remove keys listed in `hidden` from JSON schema dict.
    Works on the structure expected by render_json_tree().
    """
    if isinstance(data, dict):
        pruned = {}
        for key, val in data.items():
            if key in hidden:
                continue
            child = _prune_schema(val, hidden)
            if child not in (None, {}, []):
                pruned[key] = child
        return pruned

    if isinstance(data, list):
        cleaned = [_prune_schema(v, hidden) for v in data]
        # filter empty children
        cleaned = [c for c in cleaned if c not in (None, {}, [])]
        return cleaned

    return data


    
# ============================================================
#  Callbacks
# ============================================================
def register_downloader_callbacks(app):

    # --------------------------------------------------------
    # Get a reference schema from a PID+TestType
    # --------------------------------------------------------
    @app.callback(
        Output("downloader-testdata-store", "data", allow_duplicate=True),
        Output("downloader-schema-ui", "style"),  # show schema section
        Output("downloader-memory-store", "data", allow_duplicate=True),
        Output("downloader-sync", "children", allow_duplicate=True),
        Output("downloader-sync", "style", allow_duplicate=True),
        Input("downloader-sync", "n_clicks"),
        State("downloader-refpid", "value"),
        State("downloader-testname", "value"),
        prevent_initial_call=True,
    )
    def sync_to_hwdb(n_clicks, refpid, testname):
        if not n_clicks:
            raise PreventUpdate

        # Immediately show "Syncing..." and orange button
        syncing_style = {
            "fontSize": "20px",
            "padding": "14px 32px",
            "backgroundColor": "#f39c12",  # orange
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "not-allowed",
            "animation": "pulse 1.5s infinite",  # pulse!
        }

        # Validate the provided PID/Type ID
        if not refpid or not isinstance(refpid, str) or len(refpid) < 18:
            logger.warning("Invalid reference PID")
            return no_update, {"display": "none"}, no_update, "Sync to the HWDB", {
                "fontSize": "20px",
                "padding": "14px 32px",
                "backgroundColor": "#4CAF50",  # green
                "color": "white",
                "border": "none",
                "borderRadius": "8px",
                "cursor": "pointer",
            }

        if not testname:
            logger.warning("Test type name missing")
            return no_update, {"display": "none"}, no_update, "Sync to the HWDB", {
                "fontSize": "20px",
                "padding": "14px 32px",
                "backgroundColor": "#4CAF50",  # green
                "color": "white",
                "border": "none",
                "borderRadius": "8px",
                "cursor": "pointer",
            }

        # Make the button stay orange during syncing
        try:
            logger.info(f"Fetching test data for PID={refpid}, Test={testname}")
            resp = get_hwitem_test(refpid, testname, history=False)

            # Always take the latest entry
            testdata = None
            if isinstance(resp, dict) and "data" in resp and len(resp["data"]) > 0:
                testdata = resp["data"][0]
            else:
                logger.warning("No test data found for this PID")
                return no_update, {"display": "none"}, no_update, "Sync to the HWDB", {
                    "fontSize": "20px",
                    "padding": "14px 32px",
                    "backgroundColor": "#4CAF50",  # green
                    "color": "white",
                    "border": "none",
                    "borderRadius": "8px",
                    "cursor": "pointer",
                }

            logger.info("Test data fetched successfully")

            return testdata, {"display": "block"}, {
                "refpid": refpid,
                "testname": testname,
                }, "Sync to the HWDB", {
                    "fontSize": "20px",
                    "padding": "14px 32px",
                    "backgroundColor": "#4CAF50",  # green
                    "color": "white",
                    "border": "none",
                    "borderRadius": "8px",
                    "cursor": "pointer",
                }


        except Exception as e:
            logger.error(f"Error fetching test data: {e}")
            return no_update, {"display": "none"}, no_update, "Sync to the HWDB", {
                "fontSize": "20px",
                "padding": "14px 32px",
                "backgroundColor": "#4CAF50",  # green
                "color": "white",
                "border": "none",
                "borderRadius": "8px",
                "cursor": "pointer",
            }

    # --------------------------------------------------------
    # Pre-populate the inputs on app startup
    # --------------------------------------------------------
    @app.callback(
        Output("downloader-refpid", "value"),
        Output("downloader-testname", "value"),
        Input("downloader-memory-store", "data"),
        prevent_initial_call=False,
    )
    def preload_downloader_inputs(data):
        if not data:
            raise PreventUpdate
        return data.get("refpid"), data.get("testname")

    # --------------------------------------------------------
    # Populate Schema UI on Sync
    # --------------------------------------------------------
    @app.callback(
        Output("downloader-schema-ui", "children"),
        Input("downloader-testdata-store", "data"),
        prevent_initial_call=True,
    )
    def build_schema_ui(testdata):
        if not testdata:
            return no_update

        #tree = render_json_tree(testdata)

        
        # Remove unwanted nodes first
        cleaned = _prune_schema(testdata, HIDDEN_SCHEMA_KEYS)

        # Then render UI tree normally
        tree = render_json_tree(cleaned)

        return html.Div(
            [
                html.H4("Select fields for your schema:", style={"marginTop": "10px"}),
                html.Div(tree),
                html.Hr(),
            ]
        )

    # --------------------------------------------------------
    # Track Selected Schema Fields
    # --------------------------------------------------------
    @app.callback(
        Output("downloader-schema-store", "data"),
        Input({"type": "schema-checkbox", "path": ALL}, "value"),
        prevent_initial_call=True,
    )
    def track_schema_selection(values):
        # values is a list of lists; flatten and filter None
        selected = [v[0] for v in values if v]
        return selected

    # --------------------------------------------------------
    # Toggle the PID range UI visibility
    # --------------------------------------------------------
    @app.callback(
        Output("downloader-pid-range-ui", "style"),
        Input("downloader-schema-ui", "style"),
        prevent_initial_call=True,
    )
    def show_pid_range(schema_style):
        """
        Make PID range selector visible once schema UI is visible.
        """
        if not schema_style or schema_style.get("display") == "none":
            return {"display": "none", "marginTop": "20px"}

        # Schema is visible → enable PID range UI
        return {"display": "block", "marginTop": "20px"}

    # --------------------------------------------------------
    # Toggle download button visibility
    # --------------------------------------------------------
    @app.callback(
        Output("downloader-final-actions", "style"),
        Input("downloader-schema-ui", "style"),
        prevent_initial_call=True,
    )
    def show_download_button(schema_style):
        """
        When the schema UI becomes visible, reveal the download button.
        """
        if not schema_style or schema_style.get("display") == "none":
            return {"display": "none"}

        return {"display": "block"}

    # --------------------------------------------------------
    # Start background download job
    # --------------------------------------------------------
    @app.callback(
        Output("downloader-status", "children"),
        Output("downloader-pid-count", "children"),
        Output("downloader-job-id", "data"),
        Output("downloader-interval", "disabled"),
        Input("downloader-start-download", "n_clicks"),
        State("downloader-refpid", "value"),
        State("downloader-schema-store", "data"),
        State("downloader-testname", "value"),
        State("testdata-format", "value"),
        State("preferences-store", "data"),  # holds working directory
        State("downloader-first-pid", "value"),
        State("downloader-last-pid", "value"),
        prevent_initial_call=True,
    )
    def start_download_job(
        n_clicks,
        refpid,
        fields,
        testname,
        fmt,
        prefs,
        first_pid,
        last_pid,
    ):
        if n_clicks is None or n_clicks == 0:
            raise PreventUpdate

        # ---------------- Basic checks ----------------
        if not refpid or not isinstance(refpid, str) or len(refpid) < 12:
            return "Invalid reference PID.", None, None, True

        if not fields:
            return "No schema fields selected.", None, None, True

        workdir = prefs.get("working_dir") if prefs else None
        if not workdir or not os.path.isdir(workdir):
            return "Working directory is not set. Please configure Preferences.", None, None, True

        # Compute type ID
        type_id = refpid[:12]
        logger.info(f"Fetching PIDs for Type ID: {type_id}")

        # --- Pre-filters to get full PID list ---
        args = {
            "part_type_id": type_id,
            "size": 99999,
            "part_id": None,
            "serial_number": None,
            "manufacturer": None,
            "creator": None,
            "comments": None,
            "country_of_origin": None,
            "resp_institution": None,
            "status": None,
            "location": None,
            "certified_qaqc": None,
            "qaqc_uploaded": None,
            "is_installed": None,
        }

        #args["part_type_id"] = type_id
        #args["size"]         = 99999

        try:
            resp = get_hwitems(**args)
            items = resp["data"]
        except Exception as e:
            logger.error(f"[DL] Error fetching HW items: {e}")
            return "Error fetching HW items.", None, None, True

        pids = sorted([item["part_id"] for item in items])

        if not pids or not fields:
            return "No PIDs found for this Type ID.", None, None, True

        # ---------------- PID Range filtering ----------------
        first = (first_pid or "").strip() if first_pid else None
        last = (last_pid or "").strip() if last_pid else None

        original_pids = pids[:]

        if first and last:
            if first not in pids or last not in pids:
                return f"PID range error: {first}–{last} not found", None, None, True
            start = pids.index(first)
            end = pids.index(last)
            if end < start:
                start, end = end, start
            pids = pids[start : end + 1]

        elif first:
            if first not in pids:
                return f"{first} not found", None, None, True
            pids = [first]

        elif last:
            if last not in pids:
                return f"{last} not found", None, None, True
            pids = [last]

        logger.info(
            f"[DL] Reduced PID list from {len(original_pids)} → {len(pids)} based on range"
        )
        logger.info(f"[DL] Downloading test data for {len(pids)} PIDs")
        logger.info(f"[DL] FIELDS SELECTED = {fields}")

        if not pids:
            return "No PIDs left after applying range filter.", None, None, True

        # ---------------- Create and start job ----------------
        job_id = f"job-{int(time.time() * 1000)}"
        _download_jobs[job_id] = {
            "status": "pending",
            "total": len(pids),
            "processed": 0,
            "message": "Starting...",
            "filename": None,
            "fmt": fmt,
        }

        thread = threading.Thread(
            target=run_download_job,
            args=(job_id, pids, fields, testname, fmt, workdir, type_id),
            daemon=True,
        )
        thread.start()

        status_text = f"Download started for {len(pids)} PIDs..."
        pid_count_text = f"{len(pids)} PIDs selected"
        # Enable interval polling
        return status_text, pid_count_text, job_id, False

    # --------------------------------------------------------
    # Poll background job status
    # --------------------------------------------------------
    @app.callback(
        Output("downloader-status", "children", allow_duplicate=True),
        Output("downloader-pid-count", "children", allow_duplicate=True),
        Output("downloader-interval", "disabled", allow_duplicate=True),
        Output("downloader-start-download", "children", allow_duplicate=True),
        Output("downloader-start-download", "style", allow_duplicate=True),
        Output("downloader-start-download", "disabled", allow_duplicate=True),
        Input("downloader-interval", "n_intervals"),
        State("downloader-job-id", "data"),
        prevent_initial_call=True,
    )
    def poll_download_job(n_intervals, job_id):
        if not job_id:
            raise PreventUpdate

        job = _download_jobs.get(job_id)
        if not job:
            # Stop polling, restore button
            return (
                "Job not found.", None, True,
                "Download Selected Data",
                {"backgroundColor": "#FF5722", "color": "white"},
                False,
            )

        status = job.get("status")
        total = job.get("total", 0)
        processed = job.get("processed", 0)
        message = job.get("message", "")

        # compute % progress (avoid division by zero)
        pct = int((processed / total) * 100) if total > 0 else 0

        # =========================
        # JOB RUNNING
        # =========================
        if status in ("running", "pending"):
            running_style = ORIGINAL_BUTTON_STYLE.copy()
            running_style["backgroundColor"] = "#f39c12"
            running_style["cursor"] = "not-allowed"
            
            button_text = f"{pct}% completed..."
            button_style = running_style
            button_disabled = True

            return (
                message,
                f"{processed} / {total} PIDs processed",
                False,  # keep polling
                button_text,
                button_style,
                button_disabled,
            )

        # =========================
        # JOB DONE
        # =========================
        if status == "done":
            #button_text = "Download Complete"
            button_text = "Download Selected Data" # back to the initial title
            button_style = ORIGINAL_BUTTON_STYLE.copy()
            button_style["backgroundColor"] = "#4CAF50"  # green
            button_disabled = False

            return (
                job.get("message", "Done."),
                f"{total} PIDs have been downloaded",
                True,  # stop polling
                button_text,
                button_style,
                button_disabled,
            )

        # =========================
        # JOB ERROR
        # =========================
        if status == "error":
            button_text = "Download Failed"
            button_style = ORIGINAL_BUTTON_STYLE.copy()
            button_style["backgroundColor"] = "#FF0000"
            button_disabled = False

            return (
                job.get("message", "Error."),
                None,
                True,  # stop polling
                button_text,
                button_style,
                button_disabled,
            )

        # =========================
        # UNKNOWN FALLBACK
        # =========================
        return (
            message or "Unknown status.", None, True,
            "Download Selected Data",
            {"backgroundColor": "#FF5722", "color": "white"},
            False,
        )

    #_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
    # Binaries !!
    #_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/

    # Polling
    @app.callback(
        Output("binary-download-button", "children", allow_duplicate=True),
        Output("binary-download-button", "style", allow_duplicate=True),
        Output("binary-download-button", "disabled", allow_duplicate=True),
        Output("binary-download-interval", "disabled", allow_duplicate=True),
        Input("binary-download-interval", "n_intervals"),
        State("binary-download-job-id", "data"),
        prevent_initial_call=True,
    )
    def update_binary_progress(n, job_id):
        job = _binary_jobs.get(job_id)
        if not job:
            raise PreventUpdate

        if job.get("error"):
            red = {"backgroundColor": "#e74c3c", "color": "white"}
            return f"Error: {job['error']}", red, False, True

        processed = job["processed"]
        total = job["total"]

        if not job["done"]:
            pct = int(processed * 100 / total)
            orange = {
                "fontSize": "18px",
                "padding": "10px 30px",
                "backgroundColor": "#f39c12",
                "color": "white",
                "borderRadius": "8px",
                "cursor": "not-allowed",
                 "border": "none",
            }
            return f"{pct}% completed...", orange, True, False

        # DONE — restore original state
        green = {
            "fontSize": "18px",
            "padding": "10px 30px",
            "backgroundColor": "#4CAF50",
            "color": "white",
            "borderRadius": "8px",
            "cursor": "pointer",
            "border": "none",
        }

        _binary_jobs.pop(job_id, None)
        return "Download", green, False, True

    # Preload the previous typeid or pid
    @app.callback(
        Output("binary-id-input", "value"),
        Input("binary-memory-store", "data"),
        prevent_initial_call=False,
    )
    def preload_binary_identifier(data):
        if not data:
            raise PreventUpdate
        return data.get("identifier")

    
    # -------------------------------------
    # Show/hide Test Data vs Binaries UIs
    # -------------------------------------
    @app.callback(
        Output("downloader-test-section", "style"),
        Output("downloader-binary-section", "style"),
        Input("download-mode", "value"),
    )
    def toggle_downloader_mode(mode):
        test_style = {"marginTop": "20px"}
        binary_style = {"marginTop": "20px"}

        if mode == "binaries":
            # hide test, show binaries
            test_style["display"] = "none"
            binary_style["display"] = "block"
        else:
            # show test, hide binaries
            test_style["display"] = "block"
            binary_style["display"] = "none"

        return test_style, binary_style

    # -------------------------
    # Helpers for binaries
    # -------------------------

    def _parse_binary_identifier(raw: str):
        """
        Decide if the user input is a typeid or a PID.
        Returns (typeid, pid) where one of them can be None.
        """
        if not raw:
            return None, None

        s = raw.strip()

        # PID: typically TYPEID-XXXXX (length 18 in your scheme)
        if "-" in s and len(s) == 18:
            typeid = s.split("-", 1)[0]
            pid = s
            return typeid, pid

        # Component Type ID only (12 chars)
        if len(s) == 12:
            return s, None

        # Fallback: treat as typeid, but log
        logger.warning(f"[Binaries] Unusual identifier length: {s!r}")
        return s, None

    def _get_binary_file_list(identifier: str):
        """
        Given a 12-char Component Type ID or 18-char PID, return
        (file_list, error_msg).

        file_list: list of dicts with keys:
           - label   (for checklist display)
           - value   (image_id, used as checklist value)
           - image_id
           - image_name
           - created (raw timestamp string)
        error_msg: string or None.
        """
        if not identifier:
            return [], "Please provide a Component Type ID (12 chars) or PID (18 chars)."

        ident = identifier.strip()
        try:
            if len(ident) == 12:
                # Treat as Component Type ID
                resp = get_component_type_image_list(ident)
                data = resp.get("data", [])
                context = f"Component Type ID {ident}"
            elif len(ident) == 18:
                # Treat as PID
                resp = get_hwitem_image_list(ident)
                data = resp.get("data", [])
                context = f"PID {ident}"
            else:
                return [], (
                    "Identifier length does not look like a Component Type ID (12 chars) "
                    "or PID (18 chars)."
                )

            if not isinstance(data, list):
                return [], f"Unexpected response format from server for {context}."

            files = []
            for entry in data:
                if not isinstance(entry, dict):
                    continue

                image_name = entry.get("image_name", "")
                image_id   = entry.get("image_id", "")
                raw_created = entry.get("created", "") or ""

                # Try to format the date nicely for the label
                created_display = raw_created
                if raw_created:
                    try:
                        created_display = datetime.fromisoformat(raw_created).strftime(
                            "%Y-%m-%d %H:%M"
                        )
                    except Exception:
                        # If parsing fails, just leave whatever string we got
                        pass

                # Label: DATE | FILENAME
                label = f"{created_display} | {image_name}"

                if image_name and image_id:
                    files.append(
                    {
                        "label": label,
                        "value": image_id,         # used for checklist
                        "image_id": image_id,      # explicit for downloads
                        "image_name": image_name,  # file name on disk
                        "created": raw_created,    # raw sortable timestamp
                    }
                )

            if not files:
                return [], f"No binaries found for {context}."

            # Sort newest first by 'created' if available
            def _sort_key(f):
                c = f.get("created") or ""
                try:
                    return datetime.fromisoformat(c)
                except Exception:
                    return datetime.min

            files = sorted(files, key=_sort_key, reverse=True)

            return files, f"Found {len(files)} binary file(s) for {context}."

        except Exception as e:
            return [], f"Error while contacting HWDB: {e}"

    # Populate the checklist
    @app.callback(
        [
            Output("binary-file-checklist", "options"),
            Output("binary-file-checklist", "value"),
            Output("binary-sync-status", "children"),
            Output("binary-file-meta", "data"),
            Output("binary-sync-button", "children", allow_duplicate=True),
            Output("binary-sync-button", "style", allow_duplicate=True),
        ],
        Input("binary-sync-trigger", "data"),
        State("binary-id-input", "value"),
        prevent_initial_call=True,
    )
    def get_binary_file_list(trigger, identifier):
        if not trigger:
            raise PreventUpdate

        # Base green style to restore when done
        base_style = {
            "fontSize": "18px",
            "padding": "10px 30px",
            "backgroundColor": "#4CAF50",
            "color": "white",
            "borderRadius": "8px",
            "border": "none",
            "cursor": "pointer",
        }

        files, status_msg = _get_binary_file_list(identifier)

        if not files:
            # No files or some error: reset button to green, empty checklist
            return [], [], status_msg, [], "Sync to the HWDB", base_style

        options = [
            {"label": f["label"], "value": f["image_id"]}
            for f in files
        ]
        # default: select all
        values = [f["image_id"] for f in files]

        # Button back to green + original title
        return options, values, status_msg, files, "Sync to the HWDB", base_style
    
    # Select all or de-select all
    @app.callback(
        Output("binary-file-checklist", "value", allow_duplicate=True),
        Input("binary-select-all", "n_clicks"),
        Input("binary-deselect-all", "n_clicks"),
        State("binary-file-checklist", "options"),
        prevent_initial_call=True,
    )
    def toggle_binary_selection(n_select, n_deselect, options):
        triggered = ctx.triggered_id

        if not options:
            raise PreventUpdate

        if triggered == "binary-select-all":
            # select ALL values
            return [o["value"] for o in options]

        if triggered == "binary-deselect-all":
            # deselect all
            return []

        raise PreventUpdate
    # When there is no image available
    @app.callback(
        [
            Output("binary-select-all", "disabled"),
            Output("binary-deselect-all", "disabled"),
        ],
        Input("binary-file-checklist", "options"),
        prevent_initial_call=True,
    )
    def toggle_buttons(options):
        disabled = not bool(options)
        return disabled, disabled
    
    # Individual selections
    @app.callback(
        Output("binary-download-status", "children", allow_duplicate=True),
        Input("binary-file-checklist", "value"),
        prevent_initial_call=True,
    )
    def update_selection_count(selected):
        if not selected:
            return "No binaries selected."
        return f"{len(selected)} binary file(s) selected."


    # Download binaries!
    @app.callback(
        Output("binary-download-button", "children"),
        Output("binary-download-button", "style"),
        Output("binary-download-button", "disabled"),
        Output("binary-download-interval", "disabled"),
        Output("binary-download-job-id", "data"),
        Output("binary-memory-store", "data", allow_duplicate=True),
        Input("binary-download-button", "n_clicks"),
        State("binary-file-checklist", "value"),  # selected image_ids
        State("binary-file-meta", "data"),        # full meta for all files
        State("binary-id-input", "value"),
        State("preferences-store", "data"),
        prevent_initial_call=True,
    )
    def download_selected_binaries(n_clicks, selected_ids, meta_files, identifier, prefs):
        if not n_clicks:
            raise PreventUpdate

        if not selected_ids:
            return PreventUpdate

        # Build image_id → metadata map (we stored both 'value' and 'image_id')
        id_to_meta = {}
        for f in meta_files:
            image_id = f.get("image_id") or f.get("value")
            if image_id:
                id_to_meta[image_id] = f
                
        # Determine typeid
        ident = (identifier or "").strip()
        if len(ident) == 12:
            typeid = ident
        elif len(ident) == 18:
            typeid = ident[:12]
        else:
            return "Download", {}, False, True, None, None
    
        # Determine working directory (same scheme as Shipment Tracker)
        try:
            workdir = prefs.get("working_dir", "")
            if not workdir or not os.path.isdir(workdir):
                workdir = os.getcwd()
        except Exception:
            workdir = os.getcwd()

        # Create <working_dir>/<typeid>/images/
        images_dir = Path(workdir) / typeid / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Register job
        job_id = f"BIN-{int(time.time()*1000)}"
        _binary_jobs[job_id] = {
            "processed": 0,
            "total": len(selected_ids),
            "done": False,
            "error": None,
        }

        # Launch background thread
        thread = threading.Thread(
            target=_binary_download_worker,
            args=(job_id, selected_ids, id_to_meta, images_dir),
            daemon=True,
        )
        thread.start()

        # Immediately update button to syncing-style
        orange = {
            "backgroundColor": "#f39c12",
            "color": "white",
            "borderRadius": "8px",
            "cursor": "not-allowed",
            "fontSize": "18px",
            "padding": "10px 30px",
        }

        return "0% completed...", orange, True, False, job_id, {"identifier": identifier}
        

    # The instant orange “Syncing…” state
    @app.callback(
        [
            Output("binary-sync-button", "children"),
            Output("binary-sync-button", "style"),
            Output("binary-sync-trigger", "data"),
        ],
        Input("binary-sync-button", "n_clicks"),
        State("binary-id-input", "value"),
        prevent_initial_call=True,
    )
    def binary_sync_feedback(n_clicks, identifier):
        if not n_clicks:
            raise PreventUpdate

        # Base green style (for later reset; keep in sync with your layout)
        base_style = {
            "fontSize": "18px",
            "padding": "10px 30px",
            "backgroundColor": "#4CAF50",
            "color": "white",
            "borderRadius": "8px",
            "border": "none",
            "cursor": "pointer",
        }

        if not identifier or not identifier.strip():
            # No identifier → don’t actually trigger sync, and keep button green
            return "Sync to the HWDB", base_style, None

        # Orange + pulsing "syncing" style
        syncing_style = {
            "fontSize": "18px",
            "padding": "10px 30px",
            "backgroundColor": "#f39c12",
            "color": "white",
            "borderRadius": "8px",
            "border": "none",
            "cursor": "not-allowed",
            # If you already have a pulse animation in your CSS, this will use it:
            "animation": "pulse 1.5s infinite",
        }

        # Just some unique token so the next callback can fire
        trigger_payload = {"ts": time.time()}

        return "Syncing to the HWDB...", syncing_style, trigger_payload
