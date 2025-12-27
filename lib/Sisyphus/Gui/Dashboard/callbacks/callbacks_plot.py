from dash import Input, Output, State, html, callback
import dash
from dash.exceptions import PreventUpdate
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import ast
import pickle

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

def register_callbacks(app):

    #--------------------------------
    # to deal with lists:

    #Expand list to columns
    def explode_list_column(df, col):
        if df is None or df.empty or col not in df.columns:
            return df.copy() if df is not None else pd.DataFrame()
        
        #If the column does not have any list type values
        if not df[col].apply(lambda v: isinstance(v, list)).any():
            return df.copy()
        
        rows = []
        for _, row in df.iterrows():
            val = row[col]
            if isinstance(val, list):
                for item in val:
                    #nr = row.copy()
                    nr = row.to_dict()
                    nr[col] = item
                    rows.append(nr)
                
            else: 
                
                rows.append(row.to_dict())

        return pd.DataFrame(rows)
        
    def explode_two_lists(df, col_x, col_y):

        if df is None or df.empty or col_x not in df.columns or col_y not in df.columns:
            return df.copy() if df is not None else pd.DataFrame()
                    
        rows = []
        for _, row in df.iterrows():
            vx = row[col_x] if isinstance(row[col_x], list) else [row[col_x]]
            vy = row[col_y] if isinstance(row[col_y], list) else [row[col_y]]

            L = max(len(vx), len(vy))
        
            vx = list(vx) + [np.nan] * (L - len(vx))
            vy = list(vy) + [np.nan] * (L - len(vy))

            base = row.drop([col_x, col_y]).to_dict()
            
            
            for i in range(L):
                nr = dict(base)
                nr[col_x] = vx[i]
                nr[col_y] = vy[i]
                rows.append(nr)   
            
        return pd.DataFrame(rows)

    def build_hist2d(df, x, y, numbins):
        try:
            return px.density_heatmap(
                df,
                x=x,
                y=y,
                nbinsx=numbins or 50,
                nbinsy=numbins or 50,
                color_continuous_scale="Viridis"
            )
        except Exception as e:
            logger.error(f"Error creating 2D histogram: {e}")
            return go.Figure()
    
    #########################################
    def safe_list(v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = ast.literal_eval(s)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    # fallthrough: return original string if parsing fails
                    pass
        return v
    #--------------------------------


    
    # Update the plot
    @app.callback(
        Output("distribution-plot", "figure"),
        Output("conditions-display", "children"),
        Output("filtered-store", "data"),
        Output("plot-config-store", "data"),
        [
            Input("plot-column", "value"),
            Input("chart-type", "value"),
            Input("scatter-x", "value"),
            Input("scatter-y", "value"),
            Input("value-filter", "value"),
            Input("invert-selection-toggle", "value"), 
            Input({"type": "apply-condition", "index": dash.ALL}, "n_clicks"),
            Input("numbins-input", "value"), # triggers auto-refresh
            Input("data-store", "data"),
       ],
       [
            State({"type": "field", "index": dash.ALL}, "value"),
            State({"type": "operator", "index": dash.ALL}, "value"),
            State({"type": "threshold", "index": dash.ALL}, "value"),
            State({"type": "color", "index": dash.ALL}, "value"),
            State("logic-operator", "value"),
       ],
       prevent_initial_call=True ##
    )
    def update_plot(plot_column, chart_type,
                    scatter_x, scatter_y,
                    value_filter,
                    invert_toggle,
                    apply_clicks,
                    numbins,
                    data,
                    fields, operators, thresholds, colors, logic_operator):

         
        # Early exit: skip plotting when data not loaded yet
        if not data or data == {}:
            return dash.no_update, [], [], [] # Nov 12

        # --- Resolve dataframe from data-store ---
        if isinstance(data, dict) and "path" in data:
            try:
                with open(data["path"], "rb") as f:
                    DF = pickle.load(f)
            except Exception as e:
                logger.error(f"Failed to load pickle data for plotting: {e}")
                raise PreventUpdate
        else:
            DF = pd.DataFrame(data)

        invert = "exclude" in (invert_toggle or [])

        if DF.empty or (plot_column and plot_column not in DF.columns):
            return dash.no_update, [], [], []
        #DF = pd.DataFrame(data)
        #invert = "exclude" in (invert_toggle or [])
        #if DF.empty or plot_column not in DF.columns:
        #    return dash.no_update, [], [], [] # Nov 12

        #--------------------------------
        # Stop if no variable selected
        #if (chart_type != "scatter") and not plot_column:
        #    # Return an empty figure and no chips
        #    return go.Figure(), [], [], [] # Nov 12

        # to deal with lists:
        # Stop if required variables are missing 
        ##NEW
        if chart_type == "scatter":
            if not scatter_x or not scatter_y:
                return go.Figure(), [], [], []

        elif chart_type == "hist2d":
            if not scatter_x or not scatter_y:
                return go.Figure(), [], [], []

        else:
            if not plot_column:
                return go.Figure(), [], [], []
        #--------------------------------
        

        # If column has mixed types → cast to string
        for c in DF.columns:
            if DF[c].map(type).nunique() > 1:
                DF[c] = DF[c].astype(str)
        
        # --- Basic validation ---
        if DF is None or DF.empty:
            return go.Figure(), [], [], []

        df_filtered = DF.copy()

        
        # Filter by selected value
        if value_filter and plot_column in df_filtered.columns:
            if invert:
                df_filtered = df_filtered[~df_filtered[plot_column].isin(value_filter)]
            else:
                df_filtered = df_filtered[df_filtered[plot_column].isin(value_filter)]

        # keep a “base” dataframe for per-condition plotting
        df_base = df_filtered.copy()

                
        # --- Apply all conditions to build final filtered subset ---
       
        df_filtered = df_base.copy()

        if apply_clicks and any(apply_clicks):
            condition_masks = []
            for (f, op, t, user_color, clicks) in zip(fields, operators, thresholds, colors, apply_clicks):
                if not clicks or not f or not op or t in (None, ""):
                    continue
                if f not in df_filtered.columns:
                    continue

                try:
                    if op == "contains":
                        mask = df_filtered[f].astype(str).str.contains(str(t), case=False, na=False)
                    else:
                        t_cast = pd.to_numeric(t, errors="coerce") if df_filtered[f].dtype.kind in "if" else t
                        mask = df_filtered.eval(f"`{f}` {op} @t_cast")
                    condition_masks.append(mask)
                except Exception as e:
                    logger.error(f"Condition error ({f} {op} {t}): {e}")

            if condition_masks:
                combined_mask = condition_masks[0]
                for m in condition_masks[1:]:
                    combined_mask = (combined_mask & m) if logic_operator == "and" else (combined_mask | m)
                df_filtered = df_filtered[combined_mask]


        # --- Freeze ITEM-level dataframe (never expand this) ---
        df_for_store = df_filtered.copy()

        # Determine selected chart type
        primary = chart_type or "histogram"

        # Normalize chart type to remove "_log" suffix for internal plotting
        primary_base = primary.replace("_log", "")


        # Is there at least one “real” condition?
        def _has_real_conditions():
            if not (apply_clicks and any(apply_clicks)):
                return False
            for (f, op, t, clicks) in zip(fields, operators, thresholds, apply_clicks):
                if clicks and f and op and t not in (None, ""):
                    return True
            return False

        has_conditions = _has_real_conditions()
        

        
        # (Choose which dataframe to use for plotting)
        df_plot = df_filtered.copy()
        
        #--------------------------------
        # to deal with lists:

        try:
            # Only attempt normalization on relevant columns to limit work:
            cols_to_check = set()
            if plot_column:
                cols_to_check.add(plot_column)
            if scatter_x:
                cols_to_check.add(scatter_x)
            if scatter_y:
                cols_to_check.add(scatter_y)

            # Apply safe_list to those columns (if they exist in df_plot)
            for c in list(cols_to_check):
                if c and c in df_plot.columns:
                    df_plot[c] = df_plot[c].apply(safe_list)
        except Exception as e:
            logger.error(f"Error normalizing list-like columns: {e}")


        try:
            #if primary_base in ("scatter", "hist2d"):
            if primary_base == "scatter" or primary_base == "hist2d":
                # For scatter expand both scatter_x and scatter_y if they are list-like
                if scatter_x and scatter_y and scatter_x in df_plot.columns and scatter_y in df_plot.columns:
                    # Only expand two lists (handles non-lists gracefully)
                    df_plot = explode_two_lists(df_plot, scatter_x, scatter_y)
                else:
                    # Not enough information to plot scatter
                    df_plot = df_plot.copy()
            else:
                # For histogram, cumhist, box, line -> expand only the plot_column if it contains lists
                if plot_column and plot_column in df_plot.columns:
                    df_plot = explode_list_column(df_plot, plot_column)
        except Exception as e:
            logger.error(f"Error expanding list columns for plotting: {e}")
            # fallback to unexpanded df
            df_plot = df_filtered.copy()

        #--------------------------------

        # Convert any list remnants in df_plot to scalars if they somehow remain
        for c in df_plot.columns:
            if df_plot[c].apply(lambda v: isinstance(v, list)).any():
                # If lists remain (unexpected), convert to string to keep things safe for plotting
                df_plot[c] = df_plot[c].apply(lambda v: v if not isinstance(v, list) else (v[0] if len(v) > 0 else np.nan))
                
        # Helper for building px figures
        def build_px(chart, df, x=None, y=None):
            try:
                
                if chart == "histogram":
                    if (x or plot_column) not in df.columns:
                        # pick the first numeric column if plot_column invalid
                        num_cols = df.select_dtypes(include="number").columns
                        if len(num_cols) > 0:
                            x = num_cols[0]
                        else:
                            # fallback: first column as string
                            x = df.columns[0]
                    if not numbins:
                        return px.histogram(df, x=x or plot_column)
                    else:
                        if type(numbins) is int:
                            return px.histogram(df, x=x or plot_column, nbins=numbins)
                        else:
                            return px.histogram(df, x=x or plot_column)
                elif chart == "cumhist":
                    if (x or plot_column) not in df.columns:
                        num_cols = df.select_dtypes(include="number").columns
                        x = num_cols[0] if len(num_cols) > 0 else df.columns[0]
                    if not numbins:
                        return px.histogram(df, x=x or plot_column, cumulative=True)
                    else:
                        if type(numbins) is int:
                            return px.histogram(df, x=x or plot_column, nbins=numbins, cumulative=True)
                        else:
                            return px.histogram(df, x=x or plot_column, cumulative=True)
                elif chart == "box":
                    return px.box(df, y=y or plot_column)
                elif chart == "scatter":
                    if x in df.columns and y in df.columns:
                        return px.scatter(df, x=x, y=y)
                    else:
                        return go.Figure()
                elif chart == "line":
                    if (x or plot_column) not in df.columns:
                        num_cols = df.select_dtypes(include="number").columns
                        x = num_cols[0] if len(num_cols) > 0 else df.columns[0]
                    return px.line(df, x=x or plot_column)
                elif chart == "hist2d":
                    if x not in df.columns or y not in df.columns:
                        return go.Figure()
                    
                    df = df.copy()
                    df[x] = pd.to_numeric(df[x], errors="coerce")
                    df[y] = pd.to_numeric(df[y], errors="coerce")
                    df = df.dropna(subset=[x, y])
                    
                    if df.empty:
                        return go.Figure()
                    
                    return build_hist2d(df, x, y, numbins)
                return go.Figure()
            except Exception as e:
                logger.error(f"Error in build_px: {e}")
                logger.error(f"x: , {x}, plot_column: {plot_column}")
                logger.error(f"df.dtypes:\n {df.dtypes}")
                return go.Figure()

        # Base figure
        #primary = chart_type or "histogram"
        fig = build_px(
            primary_base,
            df_plot,
            #x=(scatter_x if primary_base == "scatter" else (plot_column if primary_base == "line" else None)),
            #y=(scatter_y if primary_base == "scatter" else None),
            x=(scatter_x if primary_base in ("scatter", "hist2d") else (plot_column if primary_base == "line" else None)),
            y=(scatter_y if primary_base in ("scatter", "hist2d") else None),
        )
        base_trace_count = len(fig.data)
        
        # --- Determine display title ---
        title_suffix = " (log scale)" if primary.endswith("_log") else ""
        #plot_label = plot_column or (f"{scatter_y} vs {scatter_x}" if primary_base == "scatter" else "")
        if primary_base in ("scatter", "hist2d"):
            plot_label = f"{scatter_y} vs {scatter_x}"
        else:
            plot_label = plot_column
        title_text = f"{primary_base.capitalize()} of {plot_label}{title_suffix}"

        # Apply conditions (Add button)
        # --- Apply visual condition traces (we must expand the cond subset similarly before plotting) ---
        chips = []

        if has_conditions:
            fig = go.Figure()

            # --- Restore axis titles (px normally does this, go.Figure does not) ---
            if primary_base in ("scatter", "hist2d"):
                fig.update_xaxes(title_text=scatter_x)
                fig.update_yaxes(title_text=scatter_y)
            else:
                fig.update_xaxes(title_text=plot_column)
                fig.update_yaxes(title_text="count")

            # Build one trace per condition (from df_base, NOT df_filtered)
            for (f, op, t, user_color, clicks) in zip(fields, operators, thresholds, colors, apply_clicks):
                if not clicks or not f or not op or t in (None, ""):
                    continue
                if f not in df_base.columns:
                    continue

                cond = df_base.copy()
                try:
                    if op == "contains":
                        cond = cond[cond[f].astype(str).str.contains(str(t), case=False, na=False)]
                    else:
                        t_cast = pd.to_numeric(t, errors="coerce") if cond[f].dtype.kind in "if" else t
                        cond = cond.query(f"`{f}` {op} @t_cast")
                except Exception as e:
                    logger.error(f"Error applying condition {f} {op} {t}: {e}")
                    continue

                if cond.empty:
                    continue

                # Expand lists consistently for plotting
                cond_plot = cond.copy()
                if primary_base in ("scatter", "hist2d") and scatter_x and scatter_y:
                    cond_plot[scatter_x] = cond_plot[scatter_x].apply(safe_list) if scatter_x in cond_plot.columns else cond_plot.get(scatter_x)
                    cond_plot[scatter_y] = cond_plot[scatter_y].apply(safe_list) if scatter_y in cond_plot.columns else cond_plot.get(scatter_y)
                    cond_plot = explode_two_lists(cond_plot, scatter_x, scatter_y)
                else:
                    if plot_column in cond_plot.columns:
                        cond_plot[plot_column] = cond_plot[plot_column].apply(safe_list)
                        cond_plot = explode_list_column(cond_plot, plot_column)

                label = f"{f} {op} {t}"

                if primary_base == "scatter":
                    if scatter_x not in cond_plot.columns or scatter_y not in cond_plot.columns:
                        continue
                    fig.add_trace(
                        go.Scattergl(
                            x=cond_plot[scatter_x],
                            y=cond_plot[scatter_y],
                            mode="markers",
                            name=label,
                            marker=dict(
                                color=user_color or "gray",
                                size=10,
                                opacity=0.7,
                                line=dict(width=1, color="black"),
                            ),
                        )
                    )

                elif primary_base in ("histogram", "cumhist"):
                    if plot_column not in cond_plot.columns:
                        continue
                    fig.add_trace(
                        go.Histogram(
                            x=cond_plot[plot_column],
                            name=label,
                            opacity=0.6,
                            marker=dict(color=user_color or "gray"),
                            nbinsx=int(numbins) if isinstance(numbins, int) else None,
                            cumulative=dict(enabled=(primary_base == "cumhist")),
                        )
                    )

                else:
                    # For box/line/etc you can add similar go.* traces later
                    pass

                chips.append(
                    html.Div(
                        label,
                        style={
                            "display": "inline-block",
                            "backgroundColor": user_color or "#666",
                            "color": "white",
                            "padding": "6px 12px",
                            "margin": "6px",
                            "borderRadius": "16px",
                            "fontWeight": "bold",
                            "font-family": "Arial, sans-serif",
                        },
                    )
                )

        else:
            # No conditions → use existing px-based base plot
            fig = build_px(
                primary_base,
                df_plot,
                x=(scatter_x if primary_base in ("scatter", "hist2d") else (plot_column if primary_base == "line" else None)),
                y=(scatter_y if primary_base in ("scatter", "hist2d") else None),
            )

   

                
        # --- Final layout ---
        #fig.update_layout(title="", template="plotly_white")
        fig.update_layout(
            title=title_text,
            title_x=0.5,
            title_font=dict(size=22, family="Arial, sans-serif", color="#333"),
            template="plotly_white",
        )
        
        if primary_base in ("histogram", "cumhist"):
            fig.update_layout(barmode="overlay")
            fig.update_traces(opacity=0.6)

        # Apply log scale if selected variant
        if primary.endswith("_log"):
            fig.update_yaxes(type="log")
        else:
            fig.update_yaxes(type="linear")
    
        
        # === Adjust layout for long X labels ===
        if primary_base in ("histogram", "cumhist", "line"):
            # Compute the longest X label (string length)
            if plot_column in df_plot.columns:
                max_label_len = max(
                    (len(str(x)) for x in df_plot[plot_column].unique()),
                    default=0,
                )
                # Heuristic: scale bottom margin with label length, cap it
                bottom_margin = min(300, 60 + max_label_len * 4)

                # Expand figure height to preserve vertical data area
                fig.update_layout(
                    margin=dict(t=60, b=bottom_margin, l=60, r=40),
                    height=600 + (bottom_margin - 100)
                )

                # Optional: tilt long labels for readability
                fig.update_xaxes(tickangle=-25)

        

                
        # --- Save current state ---
        state_data = {
            "chart_type": chart_type,
            "plot_column": plot_column,
            "scatter_x": scatter_x,
            "scatter_y": scatter_y,
            "numbins": numbins,
            "value_filter": value_filter,
        }

        conditions_data = {
            "fields": fields,
            "operators": operators,
            "thresholds": thresholds,
            "colors": colors,
            "logic_operator": logic_operator,
        }


       
        # === Compute and store binning info for overlay use ===
        config_data = None
        if primary_base in ("histogram", "cumhist") and plot_column in df_plot.columns:
            series = df_plot[plot_column]

            # Try to interpret as datetime first
            try_datetime = pd.to_datetime(series, errors="coerce", utc=True)
            if try_datetime.notna().sum() > 0:
                numeric = try_datetime.view("int64") / 1e9  # convert ns → seconds
                is_datetime = True
            else:
                numeric = pd.to_numeric(series, errors="coerce").dropna()
                is_datetime = False

            # Compute bins safely
            if numeric.empty or numeric.nunique() == 1:
                bins = np.linspace(0, 1, 2)
            else:
                bins = np.linspace(numeric.min(), numeric.max(), int(numbins or 50) + 1)

            config_data = {
                "column": plot_column,
                "chart_type": primary_base,
                "is_datetime": is_datetime,
                "bins": bins.tolist(),
                "histnorm": "count",  # you can extend later
            }

        else:
            config_data = dash.no_update

        # Convert figure to JSON (serializable)
        fig_json = fig.to_plotly_json() # not used below but can be helpful for debugging


        # Return:
        # - fig (plot)
        # - chips (conditions)
        # - df_for_store (ITEM-level filtered records) -> to store in filtered-store
        # - config_data (binning etc)
        try:
            #store_records = df_filtered.to_dict("records")
            filtered_indices = df_filtered.index.tolist()
            filtered_store_payload = {
                "path": data["path"],          # reuse original pickle
                "row_indices": filtered_indices,
            }

        except Exception:
            filtered_store_payload = []

            
        return fig, chips, filtered_store_payload, config_data

