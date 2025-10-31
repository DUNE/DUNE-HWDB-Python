import pandas as pd, ast
from dash import Input, Output, State, html, dcc
import dash

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)


# Update the dropdown menus based on the downloaded data
def register_callbacks(app):
    @app.callback(
        Output("plot-column", "options"),
        Output("scatter-x", "options"),
        Output("scatter-y", "options"),
        Input("data-store", "data"),
    )
    def update_dropdowns(data):
        if data is None:
            return [], [], []
        df = pd.DataFrame(data)
        options = [{"label": c, "value": c} for c in df.columns]
        return options, options, options
