import pandas as pd, ast
from dash import Input, Output, State, html, dcc
import dash

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)


# Filter variables
def register_callbacks(app):
    @app.callback(
        Output("value-filter", "options"),
        Input("plot-column", "value"),
        Input("data-store", "data"),
        Input("chart-type", "value"),
    )
    def update_value_filter_options(selected_column, data, chart_type):

        if chart_type in ("scatter", "hist2d"):
            return []
        
        DF = pd.DataFrame(data)
        
        if DF is None or DF.empty or not selected_column or selected_column not in DF.columns:
            return []
        
        ## unique values without nulls
        #unique_vals = DF[selected_column].dropna().unique().tolist()
        series = DF[selected_column].dropna()

        # Flatten list-valued cells
        flat_vals = []
        for v in series:
            if isinstance(v, list):
                flat_vals.extend(v)
            else:
                flat_vals.append(v)

        unique_vals = list(dict.fromkeys(flat_vals))

        
    
        try:
            unique_vals_sorted = sorted(unique_vals, key=lambda v: str(v))
        except Exception:
            unique_vals_sorted = unique_vals
        options = [{"label": str(v), "value": v} for v in unique_vals_sorted]
        return options

    @app.callback(
        Output("filter-container", "style"),
        Input("plot-column", "value"),
        Input("chart-type", "value")
    )
    def show_filter(selected_col, chart_type):
        if chart_type in ("scatter", "hist2d"):
            return {"display": "none"}
        
        if selected_col is None:
            #Hide filters
            return {"display": "none"}
        
        #Show filters
        return {"display": "block", "marginTop": "10px"}
