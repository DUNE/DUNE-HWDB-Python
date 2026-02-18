from Sisyphus.Gui.Dashboard.utils import silence_warnings

import threading, webbrowser
from threading import Timer
from dash import Dash, html
import dash_bootstrap_components as dbc
from pathlib import Path


import os, sys, io, contextlib
import logging
os.environ["FLASK_RUN_FROM_CLI"] = "false"
logging.getLogger("werkzeug").disabled = True


from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Gui.Dashboard.layout.layout_main import layout, register_layout_callbacks
from Sisyphus.Gui.Dashboard.callbacks.callbacks_preferences import register_preferences_callbacks
from Sisyphus.Gui.Dashboard.callbacks.callbacks_jsonselect import register_jsonselect_callbacks
from Sisyphus.Gui.Dashboard.callbacks.callbacks_typegetter import register_typegetter_callbacks
from Sisyphus.Gui.Dashboard.callbacks.callbacks_downloader import register_downloader_callbacks

from Sisyphus.Gui.Dashboard.callbacks import (
    register_conditions_callbacks,
    register_filter_callbacks,
    register_valuefilter_callbacks,
    register_hidecharts_callbacks,
    register_load_callbacks,
    register_plot_callbacks,
    register_sync_callbacks,
    register_updatemenu_callbacks,
    register_shipment_callbacks,
    register_overlay_callbacks,
)

def get_path(rel: str) -> str:
    """
    Resolve a path relative to the runtime root.

    Frozen (PyInstaller onedir):
      <dist>/HWDBTools/_internal/<rel>

    Non-frozen (repo checkout):
      <repo_root>/<rel>
    """
    rel = rel.lstrip("/").replace("\\", "/")

    if getattr(sys, "frozen", False):
        # In onedir, the EXE lives in <dist>/HWDBTools/
        # and _internal is a sibling folder.
        runtime_root = Path(sys.executable).resolve().parent / "_internal"
        return str(runtime_root / rel)

    # Non-frozen: infer repo root from this file location:
    # lib/Sisyphus/Gui/Dashboard/__main__.py -> repo root is 5 parents up
    # (__main__.py -> Dashboard -> Gui -> Sisyphus -> lib -> PROJECT_ROOT)
    runtime_root = Path(__file__).resolve().parents[4]
    return str(runtime_root / rel)

#------------- create the website and interface -------
dash_kwargs = dict(
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

if getattr(sys, "frozen", False):
    # Frozen: our spec places Dashboard assets into _internal/assets/
    dash_kwargs.update(
        assets_folder=get_path("assets"),
        assets_url_path="/assets",   # optional; Dash default is already "/assets"
    )

app = Dash(__name__, **dash_kwargs)

#------------- create the website and interface -------
#app = Dash(
#    __name__,
#    external_stylesheets=[dbc.themes.BOOTSTRAP],
#    suppress_callback_exceptions=True,
#    assets_folder=get_path("assets"),
#    assets_url_path="/assets",
#    )

app.title = "HWDB Dashboard"
app.layout = layout
# Force Dash to validate the layout before callback registration
#app.validation_layout = layout

#app.config.suppress_callback_exceptions = True


# Now register layout-switching callback
register_layout_callbacks(app)

# Register all callback modules
register_downloader_callbacks(app)
register_typegetter_callbacks(app)
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
register_shipment_callbacks(app)
register_overlay_callbacks(app)

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

