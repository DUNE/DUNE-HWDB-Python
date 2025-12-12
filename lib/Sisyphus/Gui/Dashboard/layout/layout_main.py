from dash import dcc, html, Input, Output, State, ctx, dash_table
from Sisyphus.Gui.Dashboard.utils.config import APP_VERSION
import dash_bootstrap_components as dbc

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Gui.Dashboard.layout.layout_typegetter import typegetter_layout
from Sisyphus.Gui.Dashboard.layout.layout_plots      import plots_layout
from Sisyphus.Gui.Dashboard.layout.layout_shipment   import shipment_layout
from Sisyphus.Gui.Dashboard.layout.layout_downloader import downloader_layout

# =========================
# Preferences
# =========================
preferences_section = html.Div(
    [
        dbc.Button(
            "Preferences",
            id="open-preferences",
            color="secondary",
            className="pref-btn",
            style={
                "position": "absolute",
                "top": "15px",
                "left": "15px",
                "zIndex": "999",
                "fontSize": "20px",
                "fontWeight": "500",
                "padding": "10px 18px",
                "borderRadius": "10px",
                "background": "rgba(90, 90, 100, 0.35)",
                "color": "rgba(255,255,255,0.95)",
                "border": "1px solid rgba(255,255,255,0.25)",
                "backdropFilter": "blur(8px)",
                "boxShadow": "none",
                "transition": "all 0.25s ease-in-out",
            },
        ),

        dbc.Offcanvas(
            [
                html.Div(
                    [
                        html.H4("User Preferences", className="pref-title"),
                        html.Hr(style={"opacity": 0.15}),

                        # =============================
                        # Database Version Section
                        # =============================
                        html.H5("Database Version", style={"color": "#fff", "marginTop": "6px"}),
                        html.Div(
                            [
                                dcc.RadioItems(
                                    id="db-version-toggle",
                                    options=[
                                        {"label": "Production", "value": "production"},
                                        {"label": "Development", "value": "development"},
                                    ],
                                    # value is now provided dynamically by callback
                                    #value="development",  # default selection
                                    labelStyle={
                                        "display": "inline-block",
                                        "marginRight": "20px",
                                        "cursor": "pointer",
                                    },
                                    inputStyle={"marginRight": "6px"},
                                    style={"marginTop": "6px", "color": "#ddd"},
                                ),
                            ],
                            style={
                                "background": "rgba(255,255,255,0.05)",
                                "padding": "10px",
                                "borderRadius": "8px",
                                "marginBottom": "15px",
                                "border": "1px solid rgba(255,255,255,0.15)",
                            },
                        ),
                        html.Hr(
                            style={
                                "border": "none",
                                "borderTop": "1px solid rgba(255,255,255,0.2)",
                                "margin": "12px 0 16px 0",
                            }
                        ),
                        # =============================
                        # Working Directory Section
                        # =============================
                        html.H5("Working Directory", style={"color": "#fff"}),
                        html.Div(
                            id="dir-display",
                            style={
                                "fontSize": "14px",
                                "color": "#ccc",
                                "marginBottom": "8px",
                            },
                        ),

                        html.Div(
                            id="directory-browser",
                            className="pref-browser",
                            style={
                                "maxHeight": "60vh",
                                "overflowY": "auto",
                                "padding": "6px",
                                "borderRadius": "8px",
                                "background": "rgba(255,255,255,0.05)",
                                "border": "1px solid rgba(255,255,255,0.15)",
                            },
                        ),
                        html.Div(
                            id="working-dir-display",
                            style={
                                "marginTop": "12px",
                                "fontSize": "13px",
                                "color": "#aaa",
                            },
                        ),
                        #html.Hr(style={"opacity": 0.15}),
                        dbc.Button(
                            "💾 Save the selected working directory",
                            id="save-preferences",
                            color="primary",
                            className="mt-2",
                            style={
                                "width": "100%",
                                "fontWeight": "600",
                                "borderRadius": "8px",
                                "boxShadow": "none",
                                "background": "rgba(0, 136, 255, 0.85)",
                                "border": "none",
                            },
                        ),
                        html.Hr(style={"opacity": 0.15}),
                    ],
                    style={"padding": "10px"},
                )
            ],
            id="preferences-pane",
            placement="start",
            is_open=False,
            style={
                "width": "420px",
                "backdropFilter": "blur(14px)",
                "background": "linear-gradient(160deg, rgba(40,40,50,0.9), rgba(25,25,35,0.9))",
                "color": "white",
                "boxShadow": "4px 0 15px rgba(0,0,0,0.35)",
                "borderRight": "1px solid rgba(255,255,255,0.1)",
            },
        ),
    ]
)


# =========================
# CONTENTS FOR EACH TAB
# =========================


# --------------- LAYOUT --------------------

layout = html.Div([
    
    # --- Preferences + Header + Tabs pinned together ---
    html.Div(
        id="header-container",
        children=[
            
            # --- Preferences ---
            dcc.Store(id="preferences-store", storage_type="local"),
            dcc.Store(id="version-change-signal", storage_type="session"),
            dcc.Interval(id="init-trigger", n_intervals=0, max_intervals=1),
            preferences_section,


            # --- Title / Header ---
            html.Div(
                [
                    html.Img(
                        src="/assets/IconBig.png",
                        style={
                            "height": "5.5vw",      # scales with viewport width
                            "maxHeight": "800px",   # don’t let it grow too large
                            "minHeight": "35px",    # don’t let it shrink too small
                            "margin-right": "1vw",
                            "marginRight": "12px",
                            "flexShrink": "0",
                            "object-fit": "contain",
                        },
                    ),
                    html.H1(
                        "HWDB Dashboard",
                        style={
                            "fontSize": "4vw",   # responsive font size
                            "font-family": "Arial, sans-serif",
                            "maxFontSize": "40px",
                            "minFontSize": "18px",
                            "color": "#2C3E50",
                            #"textShadow": "2px 2px 6px rgba(0,0,0,0.3)",  # 3D effect
                            "margin": "0",
                            "line-height": "5.5vw", # matches image height
                            "whiteSpace": "nowrap"
                        },
                    ),
                    
                ],
                style={
                    "display": "flex",
                    "justifyContent": "center",
                    "alignItems": "center",
                    "flexWrap": "wrap",   # allow wrapping on small screens
                    "marginBottom": "5px",
                    "textAlign": "center"
                },
            ),
            html.Div( # Display the version of the HWDB in use
                id="db-version-display",
                style={
                    "textAlign": "center",
                    "marginTop": "5px",
                    "fontSize": "18px",
                    "font-family": "Arial, sans-serif",
                    "color": "#0074D9",  # blue
                    "fontWeight": "400",
                }
            ),
    
            html.Div(style={"marginBottom": "20px"}), # some space...

    
            # --- Tabs ---
            dcc.Tabs(
                id="tabs",
                value="plot-tab",  # Initial tab
                children=[
                    dcc.Tab(label="Type Getter", value="tab-typegetter", className="custom-tab"),
                    dcc.Tab(label="Plots", value="plot-tab", className="custom-tab"),
                    dcc.Tab(label="Shipment Tracker", value="shipment-tab", className="custom-tab"),
                    dcc.Tab(label="Binary/Test Downloader", value="down-tab", className="custom-tab"),
                ],
            ),
        ],
        style={
            "position": "fixed",         # 🧷 stays pinned
            "top": "0",
            "left": "0",
            "width": "100%",
            "zIndex": "1000",
            "backgroundColor": "rgba(255, 255, 255, 0.9)",
            "backdropFilter": "blur(10px)",     # 💎 nice frosted-glass effect
            "boxShadow": "0 2px 10px rgba(0,0,0,0.2)",
            "paddingBottom": "8px",
        },
    ),

    # Spacer so page content starts *below* fixed header
    html.Div(style={"height": "230px"}),   # adjust if header height changes


    # --------------- Tabs content ----------------
    
    #html.Div(
    #    id="tab-typegetter-content",
    #    children=[typegetter_layout()],
    #    style={"display": "none"},  # hidden initially; switch_tabs() will show it
    #),
    #plot_tab_layout,
    #shipment_tab_layout,
    #down_tab_layout,

    html.Div(
        id="tab-typegetter-content",
        children=[typegetter_layout()],
        style={"display": "none"},  # hidden initially; switch_tabs() will show it
    ),
    plots_layout(),
    shipment_layout(),
    html.Div(
        id="down-tab-content",
        children=[downloader_layout()],
        style={"display": "none"},  # hidden initially; switch_tabs() will show it
    ),


    #down-tab-content
    
    # Dynamic tab content placeholder
    #html.Div(id="tabs-content", style={"marginTop": "20px"}),

    # Version label in bottom-left corner
    html.Div(style={"marginTop": "80px"}),
    html.Div(
        APP_VERSION,
        id="app-version",
        style={
            "position": "fixed",
            "bottom": "15px",
            "left": "20px",
            "fontSize": "20px",
            "fontWeight": "700",
            "color": "#ffffff",
            # Use a flat solid background with moderate transparency
            "background": "rgba(0, 122, 204, 0.5)",  
            "padding": "8px 16px",
            "borderRadius": "8px",
            # lighter / softer shadow (or none)
            #"boxShadow": "2px 2px 4px rgba(0,0,0,0.2)",
            "boxShadow": "none",
            # either remove text shadow or make it very subtle
            "textShadow": "0 1px 2px rgba(0,0,0,0.2)",
            "letterSpacing": "0.5px",
            "border": "1px solid rgba(255,255,255,0.5)",
            "zIndex": 9999,
            "userSelect": "none",
    })
])



# ---------------------------
# Tabs callback (client-side)
# ---------------------------
def register_layout_callbacks(app):
    @app.callback(
        [
            Output("tab-typegetter-content", "style"),
            Output("plot-tab-content", "style"),
            Output("shipment-tab-content", "style"),
            Output("down-tab-content", "style"),
        ],
        Input("tabs", "value"),
    )
    def switch_tabs(active_tab):
        visible_map = {
            "tab-typegetter": "tab-typegetter-content",
            "plot-tab": "plot-tab-content",
            "shipment-tab": "shipment-tab-content",
            "down-tab": "down-tab-content",
        }
        return tuple(
            {"display": "block"} if tab == active_tab else {"display": "none"}
            for tab in visible_map.keys()
        )
    
