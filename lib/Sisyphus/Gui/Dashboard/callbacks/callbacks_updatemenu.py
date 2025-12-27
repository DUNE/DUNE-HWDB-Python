import pandas as pd, ast
from dash import Input, Output, State, html, dcc
import dash
from dash.exceptions import PreventUpdate
import base64, io, json, pickle

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)


# Update the dropdown menus based on the downloaded data
def register_callbacks(app):
    @app.callback(
        Output("plot-column", "options"),
        Output("scatter-x", "options"),
        Output("scatter-y", "options"),
        Input("data-store", "data"),
        prevent_initial_call=True,
    )
    #def update_dropdowns(data):
    def update_dropdowns(store):
        #if data is None:
        #    return [], [], []
        
        #if not data:
        #    raise PreventUpdate
    
        #df = pd.DataFrame(data)

        ## make sure DataFrame is fully realized
        #if df.empty or len(df.columns) == 0:
        #    raise PreventUpdate

        if not store or "path" not in store:
            raise PreventUpdate

        with open(store["path"], "rb") as f:
            df = pickle.load(f)
        
        options = [{"label": c, "value": c} for c in df.columns]
        return options, options, options
