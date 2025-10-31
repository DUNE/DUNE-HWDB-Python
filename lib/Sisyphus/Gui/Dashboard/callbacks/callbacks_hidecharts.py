import pandas as pd, ast
from dash import Input, Output, State, html, dcc
import dash

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

# Show/hide chart controls
def register_callbacks(app):
    @app.callback(
        Output("scatter-controls","style"),  # Only show if type = scatter
        Output("numbins-input","style"),     # Only show if type = histogram or cumhist
        Output("plot-column","style"),       # Not  show if type = scatter
        Output("plot-column-label","style"), # Not  show if type = scatter
        #Output("box-controls","style"),
        Input("chart-type","value")
    )
    def toggle_controls(chart_type):
        return (
            {"display":"block"} if chart_type=="scatter" else {"display":"none"},
            {
                "width": "160px",         # make it wider
                "height": "20px",         # make it taller
                "fontSize": "18px",       # larger text
                "fontWeight": "bold",
                "padding": "10px 15px",
                "borderRadius": "12px",   # rounded corners
                "border": "2px solid #007BFF",
                #"boxShadow": "2px 2px 8px rgba(0, 0, 0, 0.2)",  # 3D effect
                #"marginTop": "5px", # spacing between the input and the button
                "marginLeft": "5px",
                "textAlign": "center",
                "marginLeft": "10px",
            } if (chart_type=="histogram" or chart_type=="cumhist") else {"display":"none"},
            {"display":"none"} if chart_type=="scatter" else {"display":"block"},
            {"display":"none"} if chart_type=="scatter"
                               else {
                                   "fontSize": "20px",            # Larger text
                                   "padding": "4px 32px",        # Larger button size
                                   "backgroundColor": "#BEBDB8",  # Gray color
                                   "color": "white",
                                   "border": "none",
                                   "borderRadius": "8px",
                                   "font-family": "Arial, sans-serif",
                                   "cursor": "pointer",
                                   "marginLeft": "10px",
                                },
        )


