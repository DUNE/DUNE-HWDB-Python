from dash import Input, Output, State, html, dcc
import dash
from dash.exceptions import PreventUpdate


from Sisyphus.Configuration import config
logger = config.getLogger(__name__)


# --- Update button text immediately on click ---
def register_callbacks(app):
    @app.callback(
        [Output("load-json", "children", allow_duplicate=True),
         Output("load-json", "style"   , allow_duplicate=True),
         Output("load-json", "disabled", allow_duplicate=True)],
        Input("load-json", "n_clicks"),
        prevent_initial_call=True
    )
    def update_button_text(n_clicks):
         # Show syncing status with color change
        syncing_style = {
            "fontSize": "20px",            # Larger text
            "padding": "14px 32px",        # Larger button size
            "backgroundColor": "#f39c12",  # orange
            "color": "white",
            #"fontWeight": "bold",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "pointer",
            #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
            "transition": "all 0.2s ease-in-out",
            "marginRight": "50px",
            "gap": "15px",
        }

        return "Syncing to the HWDB...", syncing_style, True

    # RESET
    @app.callback(
        [
            Output("data-store", "data", allow_duplicate=True),
            Output("condition-container", "children", allow_duplicate=True),
            Output("conditions-display", "children", allow_duplicate=True),
            Output("value-filter", "value", allow_duplicate=True),
            Output("plot-column", "value", allow_duplicate=True),
            Output("scatter-x", "value", allow_duplicate=True),
            Output("scatter-y", "value", allow_duplicate=True),
            Output("numbins-input", "value", allow_duplicate=True),
            Output("logic-operator", "value", allow_duplicate=True),
            Output("chart-type", "value", allow_duplicate=True),
            Output("downloaded-output", "children", allow_duplicate=True),
        ],
        Input("load-json", "n_clicks"),
        #prevent_initial_call=True
        prevent_initial_call="initial_duplicate"
    )
    def reset_dashboard(n_clicks):
    # Clears stored data, conditions, and selected filters
    # when the user clicks 'Sync to the HWDB'.
        if n_clicks:
            return (
                None,  # clear data-store
                [],    # clear condition-container
                [],    # clear chips display
                None,  # clear value-filter
                None,  # clear plot-column
                None,  # clear scatter-x
                None,  # clear scatter-y
                None,  # clear numbins-input
                "and", # reset logic operator to default (AND)
                "histogram",  # reset chart type to Histogram
                html.Div(
                    "Resetting dashboard...",
                    style={"color":"gray","fontSize": "20px","font-family": "Arial, sans-serif"}
                )
            )
        raise dash.exceptions.PreventUpdate
