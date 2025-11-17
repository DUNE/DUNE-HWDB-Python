import base64
import io
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, no_update, html
from dash.exceptions import PreventUpdate
from Sisyphus.Configuration import config
import numpy as np
import plotly.express as px

logger = config.getLogger(__name__)

def register_callbacks(app):

    @app.callback(
        [
            Output("overlay-store", "data", allow_duplicate=True),
            #Output("downloaded-output2", "children"),
            Output("downloaded-output", "children", allow_duplicate=True), # The downloaded message
            Output("distribution-plot", "figure", allow_duplicate=True),
        ],
        Input("upload-overlay", "contents"),
        [
            State("upload-overlay", "filename"),
            State("data-store", "data"),
            State("distribution-plot", "figure"),
        ],
        prevent_initial_call=True,
    )
    def upload_overlay(contents, filename, main_data, current_fig):
        print("Callback executed")

        if contents is None:
            return no_update, html.Span("No file uploaded", style={"color": "red"}), no_update

        # --- SAFE GUARD: If no main plot yet, don't try to overlay ---
        if current_fig is None or not isinstance(current_fig, dict) or "data" not in current_fig:
            msg = html.Span(
                "Please generate a main distribution before adding an overlay.",
                style={"color": "orange", "fontSize": "18px"}
            )
            return no_update, msg, no_update

        # --- Read CSV ---
        #try:
        #    content_type, content_string = contents.split(",")
        #    decoded = base64.b64decode(content_string)
        #    overlay_df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        #    print(f"[Overlay] CSV read OK: {overlay_df.shape}")
        #except Exception as e:
        #    msg = html.Span(f"Error reading CSV: {e}", style={"color": "red"})
        #    return no_update, msg, no_update

        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            csv_data = io.StringIO(decoded.decode('utf-8-sig'))  # handle BOM automatically

            # Try to detect delimiter (comma vs semicolon vs tab)
            sample = csv_data.read(2048)
            csv_data.seek(0)
            delimiter = ',' if sample.count(',') > sample.count(';') else ';'

            overlay_df = pd.read_csv(csv_data, sep=delimiter, engine="python")
            logger.info(f"[Overlay] CSV read OK: {overlay_df.shape}")
            logger.info(f"[Overlay] Columns: {overlay_df.columns.tolist()}")
        except Exception as e:
            msg = html.Span(f"Error reading CSV: {e}", style={"color": "red"})
            return no_update, msg, no_update

        
        if not main_data:
            msg = html.Span("Please load main data before overlay.", style={"color": "orange"})
            return no_update, msg, no_update

        main_df = pd.DataFrame(main_data)

        # --- Normalize columns ---
        main_df.columns = [str(c).strip().lower() for c in main_df.columns]
        overlay_df.columns = [str(c).strip().lower() for c in overlay_df.columns]

        # --- Find common columns ---
        #common_cols = set(main_df.columns) & set(overlay_df.columns)
        #if not common_cols:
        #    msg = html.Span("No common columns between main and overlay data.", style={"color": "red"})
        #    return no_update, msg, no_update
        #_________________________________________________________________________
        
        # Detectar columna del histograma principal
        title = current_fig.get("layout", {}).get("title", {}).get("text", "")
        overlay_col = None
        if "Histogram of" in title:
            possible_name = title.replace("Histogram of", "").strip().lower()
            if possible_name in overlay_df.columns:
                overlay_col = possible_name
        if not overlay_col:
            common_cols = set(main_df.columns) & set(overlay_df.columns)
            if not common_cols:
                msg = html.Span("No common columns found.", style={"color": "red"})
                return no_update, msg, no_update
            overlay_col = list(common_cols)[0]

        # === type detection ===
        def detect_dtype(main_series, overlay_series):
            def is_datetime_like(series):
                """Heuristic: if more than 60% of the rows contain date-like symbols (T, -, /, :)."""
                s = series.dropna().astype(str).head(20)
                return s.str.contains(r"[-/T:]", regex=True).mean() > 0.6

            # Attempt to detect datetime
            if is_datetime_like(main_series) or is_datetime_like(overlay_series):
                try:
                    main_dt = pd.to_datetime(main_series, errors="coerce", utc=True).dt.tz_localize(None)
                    over_dt = pd.to_datetime(overlay_series, errors="coerce", utc=True).dt.tz_localize(None)

                    # Validate that at least 60% of the values are valid dates
                    valid_ratio_main = main_dt.notna().mean()
                    valid_ratio_over = over_dt.notna().mean()

                    if max(valid_ratio_main, valid_ratio_over) > 0.6:
                        return main_dt, over_dt, "datetime"
                except Exception:
                    pass

            # Attempt to detect whether the data is numeric
            try:
                main_num = pd.to_numeric(main_series, errors="coerce")
                over_num = pd.to_numeric(overlay_series, errors="coerce")
                if main_num.notna().sum() > 0:
                    return main_num, over_num, "numeric"
            except Exception:
                pass

            # If it’s not datetime or numeric, then classify it as categorical.
            return main_series.astype(str), overlay_series.astype(str), "categorical"

        # === Apply type detection ===
        main_df[overlay_col], overlay_df[overlay_col], dtype_kind = detect_dtype(
            main_df[overlay_col], overlay_df[overlay_col]
        )

        logger.info(f"[Overlay] Column '{overlay_col}' detected as {dtype_kind}")

        # === Combine datasets ===
        main_df["_source_"] = "Main"
        overlay_df["_source_"] = "Overlay"
        combined_df = pd.concat([main_df, overlay_df], ignore_index=True)

        # === Consistent binning ===
        nbins = 50
        main_hist = next((t for t in current_fig["data"] if t["type"] == "histogram"), None)
        if main_hist and "nbinsx" in main_hist:
            nbins = main_hist.get("nbinsx", 50)

        # === Create combined histogram ===
        fig = px.histogram(
            combined_df,
            x=overlay_col,
            color="_source_",
            nbins=nbins,
            barmode="overlay",
            opacity=0.65,
            color_discrete_map={
                "Main": "rgba(0,0,255,0.55)",   # "rgba(0,0,255,0.6)",
                "Overlay": "rgba(255, 80, 80, 0.22)", # "rgba(100,100,100,0.5)"
            },
            title=f"Histogram of {overlay_col}",
        )

        # === Visual adjustments ===
        fig.update_layout(
            bargap=0.05,
            legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title=overlay_col,
            yaxis_title="Count",
        )

        # Preserve the original X-axis range
        if "xaxis" in current_fig.get("layout", {}) and "range" in current_fig["layout"]["xaxis"]:
            fig.update_xaxes(range=current_fig["layout"]["xaxis"]["range"])

        msg = html.Span(
            f"Overlay loaded successfully: {filename} (matched column '{overlay_col}', type: {dtype_kind})",
            style={"fontSize": "18px", "color": "red", "font-family": "Arial"},
        )

        logger.info(f"[Overlay] Overlay added using column: {overlay_col}")
        return overlay_df.to_dict("records"), msg, fig

