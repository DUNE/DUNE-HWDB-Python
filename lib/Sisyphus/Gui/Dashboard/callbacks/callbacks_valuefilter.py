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
        Input("data-store", "data")
    )
    def update_value_filter_options(selected_column, data):
        DF = pd.DataFrame(data)
        if DF is None or DF.empty or not selected_column or selected_column not in DF.columns:
            return []
        ## unique values without nulls
        unique_vals = DF[selected_column].dropna().unique().tolist()
    
        try:
            unique_vals_sorted = sorted(unique_vals, key=lambda v: str(v))
        except Exception:
            unique_vals_sorted = unique_vals
        options = [{"label": str(v), "value": v} for v in unique_vals_sorted]
        return options

    @app.callback(
        Output("filter-container", "style"),
        Input("plot-column", "value")
    )
    def show_filter(selected_col):
        if selected_col is None:
            #Hide filters
            return {"display": "none"}
        else:
            #Show filters
            return {"display": "block", "marginTop": "10px"}
