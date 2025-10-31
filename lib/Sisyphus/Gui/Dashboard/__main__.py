from .utils import silence_warnings

import threading, webbrowser
from threading import Timer
from dash import Dash
import dash_bootstrap_components as dbc


import os, sys, io, contextlib
import logging
os.environ["FLASK_RUN_FROM_CLI"] = "false"
logging.getLogger("werkzeug").disabled = True


from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from .layout.layout_main import layout, register_layout_callbacks
from .callbacks.callbacks_preferences import register_preferences_callbacks
from .callbacks.callbacks_jsonselect import register_jsonselect_callbacks

from .callbacks import (
    register_conditions_callbacks,
    register_filter_callbacks,
    register_valuefilter_callbacks,
    register_hidecharts_callbacks,
    register_load_callbacks,
    register_plot_callbacks,
    register_sync_callbacks,
    register_updatemenu_callbacks,
)

#------------- create the website and interface -------
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
    )
app.title = "HWDB Dashboard"
# Pass IsPro into layout generator
app.layout = layout
register_layout_callbacks(app)

# Register all callback modules
register_preferences_callbacks(app)
register_conditions_callbacks(app)
register_filter_callbacks(app)
register_valuefilter_callbacks(app)
register_hidecharts_callbacks(app)
register_load_callbacks(app)
register_plot_callbacks(app)
register_sync_callbacks(app)
register_updatemenu_callbacks(app)
register_jsonselect_callbacks(app)

logger.info("Dashboard is starting up...")
# Run the app
host = "127.0.0.1"
port = 8050
def open_browser():
    webbrowser.open_new(f"http://{host}:{port}")

if __name__ == "__main__":    
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        # Launch browser after short delay so server starts first
        threading.Timer(1.0, open_browser).start()
        app.run(debug=False, use_reloader=False)

