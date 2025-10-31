from dash import dcc, html, Input, Output, State, ctx
from ..utils.config import APP_VERSION
import dash_bootstrap_components as dbc

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

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
# Pre-Filters
# =========================
prefilter_panel = html.Div(
    [
        html.H4("Pre-Filters", className="prefilter-title"),

        html.Div([
            
            html.Div([
                html.Label("PID"),
                dcc.Input(
                    id="prefilter-pid",
                    placeholder="Enter a PID",
                    type="text",
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),

            html.Div([
                html.Label("Serial Number"),
                dcc.Input(
                    id="prefilter-serialnum",
                    placeholder="Enter a Serial #",
                    type="text",
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),

            html.Div([
                html.Label("Manufacturer"),
                dcc.Input(
                    id="prefilter-manu",
                    placeholder="Enter a Manufacturer",
                    type="text",
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),

            html.Div([
                html.Label("Creator"),
                dcc.Input(
                    id="prefilter-creator",
                    placeholder="Enter a Creator",
                    type="text",
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),

            html.Div([
                html.Label("Comments"),
                dcc.Input(
                    id="prefilter-comments",
                    placeholder="Enter comments",
                    type="text",
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),

            html.Div([
                html.Label("Location"),
                dcc.Input(
                    id="prefilter-location",
                    placeholder="Enter a location ID",
                    type="text",
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),

            html.Div([
                html.Label("Country of Origin"),
                dcc.Input(
                    id="prefilter-country",
                    placeholder="Enter a country name",
                    type="text",
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),

            html.Div([
                html.Label("Institution"),
                dcc.Input(
                    id="prefilter-institution",
                    placeholder="Institution name",
                    type="text",
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),

            html.Div([
                html.Label("Component Status"),
                dcc.Dropdown(
                    id="prefilter-status",
                    options=[{"label": s, "value": s} for s in ["Unknown", "In Fabrication", "Waiting on QA/QC Tests", "QA/QC Tests - Passed All", "QA/QC Tests - Non-conforming", "QA/QC Tests - Use As Is", "In Rework", "In Repair", "Permanently Unavailable", "Broken or Needs Repair", "Available (deprecated)", "Temporarily Unavailable (deprecated)", "Permanently Unavailable (deprecated)"]],
                    placeholder="Select status",
                    clearable=True,
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),

            
            html.Div([
                html.Label("Is Installed?"),
                dcc.Dropdown(
                    id="prefilter-isinstalled",
                    options=[{"label": d, "value": d} for d in ["YES", "NO"]],
                    placeholder="Select detector",
                    clearable=True,
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),

            
            html.Div([
                html.Label("Consoritum QA/QC certified?"),
                dcc.Dropdown(
                    id="prefilter-consortiumcert",
                    options=[{"label": d, "value": d} for d in ["YES", "NO"]],
                    placeholder="Select detector",
                    clearable=True,
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),
            
            html.Div([
                html.Label("QA/QC tests/docs uploaded?"),
                dcc.Dropdown(
                    id="prefilter-qaqcuploaded",
                    options=[{"label": d, "value": d} for d in ["YES", "NO"]],
                    placeholder="Select detector",
                    clearable=True,
                    style={"width": "100%"}
                ),
            ], className="filter-cell"),

          
        ],
        className="filter-grid"),

        #html.Div([
        #    html.Button(
        #        "Apply Pre-Filters",
        #        id="apply-prefilters",
        #        n_clicks=0,
        #        className="prefilter-button",
        #    )
        #], style={"textAlign": "center", "marginTop": "12px"})
    ],
    className="prefilter-panel"
)



# =========================
# CONTENTS FOR EACH TAB
# =========================
# Pre-render both tab layouts
plot_tab_layout = html.Div(
    id="plot-tab-content",
    children=[
        
            html.Div(style={"marginBottom": "40px"}), # some space...

            # Pre-filters
            prefilter_panel,
            html.Div(style={"marginBottom": "50px"}), 
            
            # Boxes for Type ID, Test Type Name, and the Sync button
            html.Div(
                [
                    # Type ID input box
                    dcc.Input(
                        id="typeid-input",
                        persistence=True,
                        type="text",
                        placeholder="Enter a Component Type ID",
                        className="text-center",
                        style={
                            "width": "250px",         # make it wider
                            "height": "45px",         # make it taller
                            "fontSize": "16px",       # larger text
                            "fontWeight": "400",
                            "padding": "10px 15px",
                            "borderRadius": "12px",   # rounded corners
                            "border": "2px solid #007BFF",
                            #"boxShadow": "2px 2px 8px rgba(0, 0, 0, 0.2)",  # 3D effect
                            "marginLeft": "10px",
                            "marginRight": "50px", # spacing between the input and the button
                            "textAlign": "center",
                        },
                    ),
                    # Test Type Name
                    dcc.Input(
                        id="testtype-input",
                        persistence=True,
                        type="text",
                        placeholder="Enter a Test Type Name",
                        className="text-center",
                        style={
                            "width": "350px",         # make it wider
                            "height": "45px",         # make it taller
                            "fontSize": "16px",       # larger text
                            "fontWeight": "400",
                            "padding": "10px 15px",
                            "borderRadius": "12px",   # rounded corners
                            "border": "2px solid #007BFF",
                            #"boxShadow": "2px 2px 8px rgba(0, 0, 0, 0.2)",  # 3D effect
                            "marginRight": "50px", # spacing between the input and the button
                            "textAlign": "center",
                    }),
                    # Sync button
                    html.Button(
                        "Sync to the HWDB",
                        id="load-json",
                        n_clicks=0,
                        style={
                            "fontSize": "20px",            # Larger text
                            "padding": "14px 32px",        # Larger button size
                            "backgroundColor": "#4CAF50",  # 
                            "color": "white",
                            "border": "none",
                            "borderRadius": "8px",
                            "cursor": "pointer",
                            #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
                            "transition": "all 0.2s ease-in-out",
                            "gap": "15px",
                            "marginRight": "50px",
                            #"marginRight": "20px",
                        },
                    ),
                    # Select JSON file
                    dcc.Upload(
                        id="upload-json",
                        children=html.Button(
                            "Select a file (csv/pkl)",
                            style={
                                "fontSize": "20px",
                                "padding": "14px 32px",
                                "backgroundColor": "#2196F3",
                                "justifyContent": "center",
                                "gap": "15px",
                                "color": "white",
                                "border": "none",
                                "borderRadius": "8px",
                                "cursor": "pointer",
                                #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",
                                "transition": "all 0.2s ease-in-out",
                                "marginRight": "50px",
                            },
                        ),
                        multiple=False,
                        #accept=".json,.pkl",
                        accept=".pkl,.pickle,.csv",
                    ),
                    
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": "1px"},
            ),

            # Display information about the downloaded contents
            html.Div(id="downloaded-output"),  # just to show results for now

            # Add spacing here
            html.Div(style={"marginBottom": "40px"}),

            html.Hr(),

            html.Div(style={"marginBottom": "20px"}),
            

            # --- Plot settings ---

            # Chart Type
            html.Label("Select chart type:",
            style={
                "fontSize": "20px",            # Larger text
                "padding": "4px 32px",        # Larger button size
                "backgroundColor": "#BEBDB8",  # Gray color
                "color": "white",
                "border": "none",
                "borderRadius": "8px",
                "cursor": "pointer",
                "font-family": "Arial, sans-serif",
                "marginLeft": "10px",
            }),
            html.Div([
                dcc.Dropdown(
                    id="chart-type",
                    options=[
                        {"label": "Histogram", "value": "histogram"},
                        {"label": "Cumulative Histogram", "value": "cumhist"},
                        {"label": "Scatter", "value": "scatter"},
                        {"label": "Line", "value": "line"},
                        {"label": "Boxplot", "value": "box"},
                    ],
                    value="histogram",
                    placeholder="Select a type",
                    clearable=False,
                    style={
                        "fontSize": "20px",
                        "padding": "0px 0px",
                        "width": "300px", # up to 300px
                        "backgroundColor": "#D9DDDC",
                        "color": "gray",
                        "border": "none",
                        "borderRadius": "8px",
                        "cursor": "pointer",
                        #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
                        "transitio": "all 0.2s ease-in-out",
                        "font-family": "Arial, sans-serif",
                        "marginRight": "50px",
                        "marginLeft": "10px",
                    }
                ),

                # # of bins
                dcc.Input(
                    id="numbins-input",
                    persistence=True,
                    type="number",
                    placeholder="Enter # of bins",
                    className="text-center",
                ),
            ],
            style={"display": "flex", "alignItems": "center", "marginBottom": "1px"},
            ),
            # Add spacing here
            html.Div(style={"marginBottom": "20px"}),
            
            # The variable list for 1D plot
            html.Label(
                "Select a variable for 1D distribution:",
                id="plot-column-label",
                style={
                    "fontSize": "20px",            # Larger text
                    "padding": "4px 32px",        # Larger button size
                    "backgroundColor": "#BEBDB8",  # Gray color
                    "color": "white",
                    "border": "none",
                    "borderRadius": "8px",
                    "font-family": "Arial, sans-serif",
                    "cursor": "pointer",
                    "marginLeft": "10px",
                }
            ),
            html.Div(
                dcc.Dropdown(
                    id="plot-column",
                    options=[],
                    value=None,
                    placeholder="Select a variable",
                    clearable=False,
                    style={
                        "fontSize": "20px",            # Larger text
                        #"padding": "10px 32px",        # Larger button size
                        "padding": "0px 0px",
                        "backgroundColor": "#D9DDDC",  # 
                        "color": "gray",
                        "border": "none",
                        "borderRadius": "8px",
                        "cursor": "pointer",
                        "boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
                        "transition": "all 0.2s ease-in-out",
                        "font-family": "Arial, sans-serif",
                        "marginLeft": "10px",
                }),
                style={
                #    "width": "150px",
                    "marginLeft": "10px",
                    "marginRight": "10px",
                },
            ),

            #Variable filter
            html.Div(
                [
                    html.Label("Select values of the selected variable (only on X-axis):",
                        style={
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
                    ),
                    dcc.Dropdown(
                        id="value-filter",
                        options=[],
                        multi=True,
                        placeholder="Select values to display",
                        style={
                            "fontSize": "20px",            # Larger text
                            "width": "600px",
                            #"padding": "10px 32px",        # Larger button size
                            "padding": "0px 0px",
                            "backgroundColor": "#D9DDDC",  # 
                            "color": "gray",
                            "border": "none",
                            "borderRadius": "8px",
                            "cursor": "pointer",
                            #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
                            "transition": "all 0.2s ease-in-out",
                            "font-family": "Arial, sans-serif",
                            "transition": "all 0.2s ease-in-out",
                            "marginLeft": "10px",
                        },
                    ),
                ], 
                id="filter-container", style={"display": "none", "marginLeft": "10px",}, 
            ),

            # Add spacing here
            html.Div(style={"marginBottom": "20px"}),

    
            # Scatter plot
            html.Div([
                html.Label("Select X-axis:", style={"font-family": "Arial, sans-serif"}),
                dcc.Dropdown(id="scatter-x", options=[], value=None, placeholder="Select X column", style={"font-family": "Arial, sans-serif"}),
                html.Label("Select Y-axis:", style={"font-family": "Arial, sans-serif"}),
                dcc.Dropdown(id="scatter-y", options=[], value=None, placeholder="Select Y column", style={"font-family": "Arial, sans-serif"}),
            ], id="scatter-controls", style={"display":"none"}),

            html.Hr(),

            # Conditions
            html.Div([
                dcc.Dropdown(
                    id="logic-operator",
                    style={
                        "fontSize": "18px",
                        "font-family": "Arial, sans-serif",
                        "width": "150px",
                        "marginRight": "30px",
                        "textAlign": "center",
                        "marginLeft": "5px",
                    },
                    options=[{"label":"AND","value":"and"},{"label":"OR","value":"or"}],
                    value="and",
                    clearable=False
                ),
                html.Button(
                    "Add condition",
                    id="add-condition",
                    n_clicks=0,
                    style={
                        "fontSize": "20px",            # Larger text
                        "padding": "14px 32px",        # Larger button size
                        "backgroundColor": "#4CAF50",  # 
                        "color": "white",
                        "border": "none",
                        "borderRadius": "8px",
                        "cursor": "pointer",
                        #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
                        "transition": "all 0.2s ease-in-out",
                        "font-family": "Arial, sans-serif",
                        "marginRight": "30px",
                    }
                ),
                #html.Button(
                #    "Load conditions",
                #    id="load-conditions",
                #    n_clicks=0,
                #    style={
                #        "fontSize": "20px",
                #        "padding": "14px 32px",
                #        "backgroundColor": "#2196F3",
                #        "color": "white",
                #        "border": "none",
                #        "borderRadius": "8px",
                #        "cursor": "pointer",
                #        #"boxShadow": "0 4px 6px rgba(0,0,0,0.3)"
                #        "transition": "all 0.2s ease-in-out",
                #        "font-family": "Arial, sans-serif",
                #    }
                #),
                dcc.Upload(
                    id="upload-conditions",
                    children=html.Button(
                        "Load conditions",
                        id="load-conditions",
                        n_clicks=0,
                        style={
                            "fontSize": "20px",
                            "padding": "14px 32px",
                            "backgroundColor": "#2196F3",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "8px",
                            "cursor": "pointer",
                            #"boxShadow": "0 4px 6px rgba(0,0,0,0.3)"
                            "transition": "all 0.2s ease-in-out",
                            "font-family": "Arial, sans-serif",
                            "textAlign": "center",
                        },
                    ),
                    multiple=False,
                    accept=".json,application/json", 
                ),
            ],
            style={"display": "flex", "alignItems": "center", "marginBottom": "1px"},
            ),
            html.Div(style={"marginBottom": "20px"}),

            # List of the currently applied conditions
            html.Div(
                id="condition-container",
                style={
                    "fontSize": "18px",
                    "marginRight": "15px",
                    "font-family": "Arial, sans-serif",
                    "textAlign": "center",
                }
            ),

            html.Hr(),
           
            # Graph output
            html.Div([
                html.Div(
                    id="conditions-display",
                    style={
                        #"display": "none" # make this invisible...
                        "textAlign": "center",
                        "marginBottom": "15px",
                        #"fontSize": "20px",
                        "fontWeight": "bold",
                        "font-family": "Arial, sans-serif",
                        "display": "flex",
                        "flexWrap": "wrap",
                        "justifyContent": "center", 
                        "gap": "10px",
                }),

                html.Div(
                    id="status-display",
                    style={
                        "textAlign": "left",
                        "fontFamily": "Arial, sans-serif",
                        "fontSize": "18px",
                        "color": "gray",
                        "marginBottom": "10px",
                        "height": "25px",  # keeps space reserved even when empty
                        "marginLeft": "5px",
                        "marginTop": "0px" 
                    }
                ),
                dcc.Loading(
                    id="loading-plot",
                    type="circle",           # spinner style: "circle", "default", "dot", "graph"
                    color="#007ACC",         # spinner color
                    children=dcc.Graph(id="distribution-plot")
                ),
            ]),

            
            html.Hr(),

            #-----------------------
            html.Div(
                [
                    dcc.Input(
                        id="csv-filename",
                        type="text",
                        placeholder="HWDB_filtered.csv",
                        value="HWDB_filtered.csv",
                        style={
                            "fontSize": "17px",
                            "width": "800px",
                            "marginRight": "12px",
                            "padding": "8px",
                            "borderRadius": "6px",
                            "border": "1px solid #ccc",
                            "fontFamily": "Arial, sans-serif",
                        },
                    ),
                    html.Button(
                        "Save filtered Items in CSV",
                        id="btn-download",
                        style={
                            "fontSize": "20px",            # Larger text
                            "padding": "14px 32px",        # Larger button size
                            "backgroundColor": "#4CAF50",  # Green color
                            "color": "white",
                            "border": "none",
                            "borderRadius": "8px",
                            "cursor": "pointer",
                            #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
                            "transition": "all 0.2s ease-in-out",
                            "fontFamily": "Arial, sans-serif",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "marginTop": "20px",
                },
            ),
            html.Div(
                id="save-status",
                style={
                    "textAlign": "center",
                    "fontSize": "16px",
                    "marginTop": "10px",
                    "fontFamily": "Arial, sans-serif",
                    "color": "red",
                    "fontWeight": "bold",
                },
            ),
            # --- interval timer (initially stopped) ---
            dcc.Interval(id="save-status-timer", interval=3000, n_intervals=0, disabled=True), # stay there for 3 seconds

            dcc.Download(id="download-dataframe-csv"),
            #-----------------------
            

            # --- Hidden data store ---
            #dcc.Store(id="data-store", storage_type="memory"),
            dcc.Store(id="data-store", storage_type="local"),
            dcc.Store(id="filtered-store", storage_type="memory"), # This needs to be right after dcc.Store(id="data-store")!
    ],
    style={"display": "block"}  # visible by default
)

# The 2nd tab
down_tab_layout = html.Div(
    id="down-tab-content",
    children=[
        html.Div(style={"marginBottom": "80px"}),
        html.Label(
            "This is the new tab! Will start to work on this tab shortly...",
            style={
                "font-size": "20px",
                "text-align": "center",
                "font-family": "Arial, sans-serif",
                "display": "block",
                "margin-bottom": "10px"
            },
        ),
    ],
    style={"display": "none"}  # hidden initially
)

# --------------- LAYOUT --------------------

layout = html.Div([

    # --- Preferences ---
    dcc.Store(id="preferences-store", storage_type="local"),
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
                    "fontSize": "6vw",   # responsive font size
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
    
    html.Div(style={"marginBottom": "40px"}), # some space...

    
    # --- Tabs ---
    dcc.Tabs(
        id="tabs",
        value="plot-tab",
        children=[
            dcc.Tab(
                label="Plots",
                value="plot-tab",
                style={ 
                    #"backgroundColor": "#f0f0f0", # Let css handle this
                    #"border": "1px solid #ccc",
                    #"borderRadius": "8px 8px 0 0",
                    #"boxShadow": "0 4px 8px rgba(0,0,0,0.2)",
                    #"padding": "10px",
                    #"marginRight": "5px",
                    "fontWeight": "900",
                    "fontSize": "19px",
                    "font-family": "Arial, sans-serif",
                    #"color": "#222",
                    "textShadow": "none",
                    "cursor": "pointer",
                    "transition": "all 0.5s ease-in-out",
                    "marginLeft": "10px",
                },
                selected_style={ # Let css handle this
                    #"backgroundColor": "#ffffff",
                    #"borderBottom": "3px solid #007acc",
                    #"boxShadow": "inset 0 3px 6px rgba(0,0,0,0.25)",
                    #"color": "#007acc",
                    "fontWeight": "900",
                    "fontSize": "19px",
                    "font-family": "Arial, sans-serif",
                    "textShadow": "none",
                    "transform": "translateY(1px)",
                    "marginLeft": "10px",
                },
                className="custom-tab",
                selected_className="custom-tab--selected",
            ),
            dcc.Tab(
                label="The next project",
                value="down-tab",
                style={
                    #"backgroundColor": "#f0f0f0",
                    #"border": "1px solid #ccc",
                    #"borderRadius": "8px 8px 0 0",
                    #"boxShadow": "0 4px 8px rgba(0,0,0,0.2)",
                    #"padding": "10px",
                    #"marginRight": "5px",
                    "fontWeight": "900",
                    "fontSize": "19px",
                    "font-family": "Arial, sans-serif",
                    #"color": "#222",
                    "textShadow": "none",
                    "cursor": "pointer",
                    "transition": "all 0.5s ease-in-out",
                    "marginRight": "10px",
                },
                selected_style={
                    #"backgroundColor": "#ffffff",
                    #"borderBottom": "3px solid #007acc",
                    #"boxShadow": "inset 0 3px 6px rgba(0,0,0,0.15)",
                    #"color": "#007acc",
                    "fontWeight": "900",
                    "fontSize": "19px",
                    "font-family": "Arial, sans-serif",
                    "textShadow": "none",
                    "transform": "translateY(1px)",
                    "marginRight": "10px",
                },
                className="custom-tab",
                selected_className="custom-tab--selected",
            ),
        ],
    ),

    # this will display the selected tab’s layout
    #html.Div(id="tabs-content"),
    # both tabs are already rendered
    plot_tab_layout,
    down_tab_layout,

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
        [Output("plot-tab-content", "style"),
        Output("down-tab-content", "style")],
        Input("tabs", "value")
    )
    def switch_tabs(tab):
        if tab == "plot-tab":
            return {"display": "block"}, {"display": "none"}
        else:
            return {"display": "none"}, {"display": "block"}
