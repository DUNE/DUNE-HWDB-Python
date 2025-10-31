from dash import Input, Output, State, html
import dash
from dash.exceptions import PreventUpdate
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

def register_callbacks(app):

    # Update the plot
    @app.callback(
        Output("distribution-plot", "figure"),
        Output("conditions-display", "children"),
        Output("filtered-store", "data"),
        #Output("status-display", "children"), # OCT
        [
            Input("plot-column", "value"),
            Input("chart-type", "value"),
            Input("scatter-x", "value"),
            Input("scatter-y", "value"),
            Input("value-filter", "value"),  
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
    )
    def update_plot(plot_column, chart_type,
                    scatter_x, scatter_y,
                    value_filter,
                    apply_clicks,
                    numbins,
                    data,
                    fields, operators, thresholds, colors, logic_operator):
        
        # Early exit: skip plotting when data not loaded yet
        if not data or data == {}:
            return dash.no_update, [], []

        DF = pd.DataFrame(data)

        if DF.empty or plot_column not in DF.columns:
            return dash.no_update, [], []

        # Stop if no variable selected
        if (chart_type != "scatter") and not plot_column:
            # Return an empty figure and no chips
            return go.Figure(), [], []

        # If column has mixed types → cast to string
        for c in DF.columns:
            if DF[c].map(type).nunique() > 1:
                DF[c] = DF[c].astype(str)
        
        # --- Basic validation ---
        if DF is None or DF.empty:
            return go.Figure(), [], []

        df_filtered = DF.copy()

        # Filter by selected value
        if value_filter and plot_column in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[plot_column].isin(value_filter)]

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
                return go.Figure()
            except Exception as e:
                logger.error("Error in build_px:", e)
                logger.error("x:", x, "plot_column:", plot_column)
                logger.error("df.dtypes:\n", df.dtypes)
                return go.Figure()

        # Base figure
        primary = chart_type or "histogram"
        fig = build_px(
            primary,
            df_filtered,
            x=(scatter_x if primary == "scatter" else (plot_column if primary == "line" else None)),
            y=(scatter_y if primary == "scatter" else None),
        )

        # Apply conditions (Add button)
        chips = []
        if apply_clicks and any(apply_clicks):
            for idx, (f, op, t, user_color, clicks) in enumerate(zip(fields, operators, thresholds, colors, apply_clicks)):
                if not clicks or not f or not op or not t:
                    continue
                if f not in df_filtered.columns:
                    continue

                cond = df_filtered.copy()
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

                #cond_fig = build_px(primary, cond)
                # To accomodate for the scatter case as well
                cond_fig = build_px(
                    primary,
                    cond,
                    x=(scatter_x if primary == "scatter" else None),
                    y=(scatter_y if primary == "scatter" else None),
                )
            
                for trace in cond_fig.data:
                    trace.name = f"{f} {op} {t}"
                    trace.showlegend = True  # ensure it shows in legend
                    # --- Apply styling enhancements ---
                    if user_color:
                        if hasattr(trace, "marker"):
                            
                            # Scatter or other marker-based traces
                            if trace.type == "scatter":
                                trace.update(
                                    marker=dict( # works for both scatter and histogram traces
                                        color=user_color,
                                        size=14,          # bigger points
                                        opacity=0.6,      # semi-transparent
                                        line=dict(width=1.5, color="black"),  # thin border
                                    )
                                )
                            else:
                                # For bars / histograms, don't set size or line
                                trace.update(marker=dict(color=user_color, opacity=0.7))
                        elif hasattr(trace, "line"):
                            #trace.line.color = user_color
                            #trace.update(line=dict(color=user_color)) # works for both scatter and histogram traces
                            race.update(line=dict(color=user_color, width=3)) # works for both scatter and histogram traces
                    fig.add_trace(trace)

                # Display visual condition chip
                chips.append(
                    html.Div(
                        f"{f} {op} {t}",
                        style={
                            "display": "inline-block",
                            "alignItems": "center",
                            "gap": "8px",
                            "backgroundColor": user_color or "#666",
                            "color": "white",
                            #"padding": "4px 10px",
                            "padding": "6px 12px",
                            #"margin": "4px",
                            "margin": "6px", # TODAY
                            #"borderRadius": "12px",
                            "borderRadius": "16px",
                            "fontWeight": "bold",
                            #"boxShadow": "2px 2px 5px rgba(0,0,0,0.3)",
                            "font-family": "Arial, sans-serif",
                        },
                        title="Condition applied to plot",
                    )
                )

                    

        # --- Final layout ---
        fig.update_layout(title="", template="plotly_white")
        if primary in ("histogram", "cumhist"):
            fig.update_layout(barmode="overlay")
            fig.update_traces(opacity=0.6)


        # --- Apply all conditions to build final filtered subset ---
        if apply_clicks and any(apply_clicks):
            condition_masks = []
            for idx, (f, op, t, user_color, clicks) in enumerate(zip(fields, operators, thresholds, colors, apply_clicks)):
                if not clicks or not f or not op or not t:
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
                    print(f"Condition error ({f} {op} {t}):", e)

            # Combine all masks with selected logic (and/or)
            if condition_masks:
                combined_mask = condition_masks[0]
                for m in condition_masks[1:]:
                    if logic_operator == "and":
                        combined_mask = combined_mask & m
                    else:
                        combined_mask = combined_mask | m
                df_filtered = df_filtered[combined_mask]

        #status_message = html.Span("Ready", style={"color": "green"})
            
        return fig, chips, df_filtered.to_dict("records")
