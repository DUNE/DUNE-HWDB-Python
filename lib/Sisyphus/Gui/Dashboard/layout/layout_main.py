from dash import dcc, html, Input, Output, State, ctx, dash_table
from Sisyphus.Gui.Dashboard.utils.config import APP_VERSION
import dash_bootstrap_components as dbc

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Gui.Dashboard.layout.layout_typegetter import typegetter_layout

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
# Pre-render tab layouts

# The Plots tab
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
                    dcc.Upload(
                        id="upload-overlay",
                        children=html.Button(
                            "Select a csv to overlay",
                            style={
                                "fontSize":"20px",
                                "padding":"14px 32px",
                                "backgroundColor":"#9C27B0",
                                "color":"white",
                                "border":"none",
                                "borderRadius":"8px",
                                "cursor":"pointer",
                                "transition":"all 0.2s ease-in-out",
                                "marginRight": "50px",
                            },
                        ),
                        multiple=False,
                        accept=".csv",
                        #style={
                        #    #"border":"2px dashed #9C27B0",
                        #    #"borderRadius":"10px",
                        #    #"padding":"15px",
                        #    "textAlign":"center",
                        #    # "backgroundColor":"#fafafa",
                        #    "width":"300px",
                        #},
                    ),
                    #----------------------------------------------------
                    #Select file to overlay
                    dcc.Store(id="overlay-store"),
                    #----------------------------------------------------
                    
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
                        {"label": "Histogram (log-Y)", "value": "histogram_log"},
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
                    dbc.Checklist(
                        id="invert-selection-toggle",
                        options=[{"label": "Exclude selected bins", "value": "exclude"}],
                        value=[],
                        switch=True,  # makes it a toggle switch instead of a checkbox
                        style={"marginLeft": "15px", "marginTop": "6px"},
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
            dcc.Store(id="plot-config-store", storage_type="memory"), # Nov 12
    ],
    style={"display": "block"}  # visible by default
)




# The Shipment Tracker tab
shipment_tab_layout = html.Div(
    id="shipment-tab-content",
    style={"padding": "15px"},
    children=[

        dcc.Store(id="fetch-shipments-trigger", storage_type="memory"),
        dcc.Store(id="shipments-selected-pid",data={"pid": None},storage_type="local"),   # ✅ persist selection
        dcc.Store(id="fetch-shipments-store", storage_type="memory"),  # persist synced shipment data until refresh
        dcc.Store(id="shippinglabel-id-store"),
        dcc.Store(id="bol-id-store"),
        # Title
        #html.H2(
        #    "Shipment Tracker",
        #    style={
        #        "textAlign": "center",

        #        "fontWeight": "bold",
        #        "marginBottom": "20px",
        #    },
        #),

        html.Div(style={"marginTop": "40px"}), 
        
        # Row 1: Controls and Filters
        html.Div(
            #style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center", "gap": "10px"},
            children=[
                dcc.Input(
                    id="shipment-typeid",
                    type="text",
                    placeholder="Enter Component Type ID",
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
                    #style={
                    #    "width": "280px",
                    #    "height": "40px",
                    #    "padding": "5px 10px",
                    #    "borderRadius": "8px",
                    #    "border": "none",
                    #    "backgroundColor": "#D9DDDC",
                    #    "color": "gray",
                    #    "fontSize": "18px",
                    #},
                ),
                dbc.Button(
                    "Sync to the HWDB",
                    id="fetch-shipments",
                    n_clicks=0,
                    color="primary",
                    #className="tg-sync-btn",
                    style = {
                        "fontSize": "20px",            # Larger text
                        "padding": "14px 32px",        # Larger button size
                        "backgroundColor": "#4CAF50",  # 
                        "color": "white",
                        "border": "none",
                        "borderRadius": "8px",
                        "justifyContent": "center",
                        "gap": "15px",
                        "cursor": "pointer",
                        #"boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",  # 3D effect
                        "transition": "all 0.2s ease-in-out",
                        "marginRight": "50px",
                    }
                ),
                
                #html.Button(
                #    "🖨️ Generate All Labels",
                #    id="generate-all-labels",
                #    n_clicks=0,
                #    style={
                #        "height": "40px",
                #        "borderRadius": "8px",
                #        "border": "none",
                #        "backgroundColor": "#00897B",
                #        "color": "white",
                #        "fontSize": "18px",
                #        "padding": "0px 18px",
                #        "cursor": "pointer",
                #        "transition": "all 0.2s ease-in-out",
                #    },
                #),
            ],
            style={"display": "flex", "alignItems": "center","justifyContent": "center", "marginBottom": "1px"},
        ),

        html.Br(),

        # Row 2: Summary Cards
        html.Div(
            id="shipment-summary-cards",
            style={
                "display": "flex",
                "flexWrap": "wrap",
                "justifyContent": "center",
                "gap": "15px",
                "marginBottom": "25px",
            },
            children=[
                html.Div("📦 Total Boxes: —", id="summary-total", className="summary-card"),
                html.Div("🚚 In-Transit: —", id="summary-transit", className="summary-card"),
                html.Div("📍 Delivered: —", id="summary-delivered", className="summary-card"),
            ],
        ),

        # Row 3: Main Table
        html.Div(
            style={
                "backgroundColor": "#F3F3F3",
                "padding": "10px",
                "borderRadius": "12px",
                "boxShadow": "0 2px 6px rgba(0, 0, 0, 0.15)",
                "marginBottom": "20px",
                "marginRight": "10px",
            },
            children=[
                html.H4("List of shipping boxes", style={"color": "#004C99", "marginLeft": "10px"}),
                dash_table.DataTable(
                    id="shipment-table",
                    columns=[
                        {"name": "Box PID", "id": "box_pid"},
                        {"name": "Certificed", "id": "certified"},          # narrow placeholder column
                        {"name": "Uploaded", "id": "docuploaded"},          # another narrow column
                        {"name": "Latest Location", "id": "location"},
                        {"name": "Shipped Date", "id": "shipped_date"},
                        {"name": "Received Date", "id": "received_date"},
                        {"name": "Shipper", "id": "shipper"},
                        {"name": "Receiver", "id": "receiver"},
                        {"name": "Status", "id": "status"},
                    ],
                    data=[], #<=== the data!!
                    fixed_rows={"headers": True},     # keeps the header row fixed
                    #data=fake_shipments, # for testing purpose only!!
                    css=[
                        # highlight the whole row on hover
                        {"selector": "tr:hover", "rule": "background-color: #E3F2FD !important; cursor: pointer;"},
                        {"selector": "tr:hover td", "rule": "background-color: #E3F2FD !important;"},
                    ],
                    style_table={
                        "height": "30vh",
                        "overflowY": "auto",
                        #"overflowX": "auto",
                        "overflowX": "hidden",     # disables horizontal scrolling
                        "tableLayout": "fixed",    # keeps columns within container width
                        "width": "100%",           # ensures table stays within container
                        "tableLayout": "fixed",   # Force respect of fixed column widths
                    },
                    style_cell={
                        "textAlign": "center",
                        "height": "600px",
                        "fontFamily": "Arial, sans-serif",
                        "fontSize": "16px",
                        "padding": "5px",
                        "height": "auto",       # dynamic cell height (not fixed!)
                        "whiteSpace": "normal", # allows text wrapping if needed
                    },
                    style_header={
                        "backgroundColor": "#4A90E2",
                        "color": "white",
                        "fontWeight": "bold",
                        "fontSize": "17px",
                        "position": "sticky",
                        "top": 0,
                        "zIndex": 1,
                    },
                    # Column-specific widths
                    style_cell_conditional=[
                        {"if": {"column_id": "box_pid"},       "width": "120px", "minWidth": "120px", "maxWidth": "120px"},
                        {"if": {"column_id": "certified"},     "width": "50px", "minWidth": "50px", "maxWidth": "50px"},
                        {"if": {"column_id": "docuploaded"},   "width": "50px", "minWidth": "50px", "maxWidth": "50px"},
                        {"if": {"column_id": "location"},      "width": "200px", "minWidth": "200px", "maxWidth": "200px"},
                        {"if": {"column_id": "shipped_date"},  "width": "90px", "minWidth": "90px", "maxWidth": "90px"},
                        {"if": {"column_id": "received_date"}, "width": "90px", "minWidth": "90px", "maxWidth": "90px"},
                        {"if": {"column_id": "shipper"},       "width": "180px"},
                        {"if": {"column_id": "receiver"},      "width": "180px"},
                        {"if": {"column_id": "status"},        "width": "70px", "minWidth": "70px", "maxWidth": "70px"},
                    ],
                    style_data_conditional=[
                        
                        # highlight delivered and in-transit colors
                        {"if": {"column_id": "Status", "filter_query": "{Status} eq 'Delivered'"},
                         "backgroundColor": "#C8E6C9"},
                        {"if": {"column_id": "Status", "filter_query": "{Status} eq 'In-Transit'"},
                         "backgroundColor": "#FFF9C4"},

               
                        # --- Selected (persisting) row highlight ---
                        {
                            "if": {"state": "selected"},
                            "backgroundColor": "#D1E9FF",
                            "border": "1px solid #4A90E2",
                        },

                        # --- Fix for the single clicked (active) cell ---
                        {
                            "if": {"state": "active"},
                            "backgroundColor": "#D1E9FF",
                            "border": "1px solid #4A90E2",
                        },
                        
                    ],
                    #row_selectable="single",  # enable entire-row interaction
                ),
            ],
        ),

        html.Div(style={"marginBottom": "40px"}), # some space
        
        # Row 4: Timeline
        html.Div(
            id="shipment-details-section",
            style={
                "display": "none",  # hidden until a row is selected
                "flexDirection": "row",  # stack horizontally
                "marginTop": "20px",
                #"marginBottom": "30px",
                "display": "flex",
                "gap": "25px",
                "justifyContent": "space-between",
            },
            children=[
                # --- Left: History Table ---
                html.Div(
                    id="shipment-history-container",
                    style={
                        "flex": "1 1 50%",
                        "width": "50%",
                        "backgroundColor": "#FAFAFA",
                        "padding": "10px",
                        "borderRadius": "12px",
                        "boxShadow": "0 2px 6px rgba(0, 0, 0, 0.1)",
                        "overflowY": "auto",
                        "maxHeight": "45vh",
                        "marginLeft": "10px",
                        #"marginRight": "10px",
                    },
                    children=[
                        html.H4(
                            "Shipment History",
                            id="shipment-history-title",
                            style={"color": "#004C99", "marginLeft": "10px"},
                        ),
                        dash_table.DataTable(
                            id="shipment-history-table",
                            cell_selectable=False,  # disables focus/active selection
                            css=[                   # kill hover & any cell focus styles
                                {"selector": "tr:hover", "rule": "background-color: inherit !important; cursor: default;"},
                                {"selector": "tr:hover td", "rule": "background-color: inherit !important;"},
                                {"selector": "td.dash-cell.focused", "rule": "background-color: inherit !important; box-shadow: none !important;"},
                                {"selector": "td.cell--active", "rule": "background-color: inherit !important;"},
                                {"selector": "td.cell--selected", "rule": "background-color: inherit !important;"},
                            ],
                            columns=[
                                {"name": "Date", "id": "date"},
                                {"name": "Shipper / Receiver", "id": "person"},
                                {"name": "Location", "id": "location"},
                                {"name": "Comments", "id": "comments"},
                            ],
                            data=[],
                            fixed_rows={"headers": True},
                            style_table={
                                "height": "40vh",
                                "overflowY": "auto",
                                "overflowX": "auto", 
                                "tableLayout": "fixed",
                                "width": "100%",
                            },
                            style_cell={
                                "textAlign": "center",
                                "fontFamily": "Arial, sans-serif",
                                "fontSize": "15px",
                                "whiteSpace": "normal",
                                "padding": "6px",
                            },
                            style_header={
                                "backgroundColor": "#4A90E2",
                                "color": "white",
                                "fontWeight": "bold",
                                "fontSize": "15px",
                                "whiteSpace": "normal",
                                "position": "sticky",
                                "top": 0,
                                "zIndex": 1,
                            },
                            style_cell_conditional=[
                                {"if": {"column_id": "date"},       "width": "50px", "minWidth": "50px", "maxWidth": "50px"},
                                {"if": {"column_id": "person"},     "width": "50px", "minWidth": "50px", "maxWidth": "50px"},
                                {"if": {"column_id": "location"},   "width": "100px"},
                                {"if": {"column_id": "comments"},   "width": "100px"},
                            ],
                            style_data_conditional=[ # Zebra striping
                                {
                                    "if": {"row_index": "odd"},
                                    "backgroundColor": "#F9F9F9",
                                },
                                {
                                    "if": {"row_index": "even"},
                                    "backgroundColor": "white",
                                },
                                {"if": {"state": "active"},   "backgroundColor": "inherit", "border": "inherit"},
                                {"if": {"state": "selected"}, "backgroundColor": "inherit", "border": "inherit"},
                                # Optional hover highlight
                                #{
                                #    "if": {"state": "active"},
                                #    "backgroundColor": "#E3F2FD",
                                #    "border": "1px solid #4A90E2",
                                #},
                            ],
                        ),
                    ],
                ),

                # --- Right: Info Boxes ---
                html.Div(
                    id="shipment-info-cards",
                    #style={
                    #    "display": "grid",
                    #    "gridTemplateColumns": "repeat(2, auto)", # define the grid
                    #    "gap": "18px",
                    #    "alignItems": "start",
                    #    "marginLeft": "10px",
                    #    "marginRight": "10px",
                    #},
                    style={
                        "flex": "1 1 50%",
                        "width": "50%",
                        #"marginLeft": "10px",
                        "marginRight": "10px",
                        "marginTop": "10px",
                    },
                    children=[

                        html.H4("📦 Shipment Details", style={"color": "#004C99", "marginBottom": "10px"}),

                        # --- Download Label Button (compact, top) ---
                        html.Div(
                            [
                                html.Button(
                                    "⬇️ Download Shipping Label",
                                    id={"type": "download-button", "index": "shippinglabel"},
                                    n_clicks=0,
                                    className="shiplabel-btn",
                                ),
                                dcc.Store(id={"type": "image-id-store", "index": "shippinglabel"}),
                                dcc.Store(id={"type": "image-status-store", "index": "shippinglabel"}), 
                            ],
                            style={
                                "display": "flex",
                                "justifyContent": "center",
                                "marginBottom": "12px"
                            },
                        ),
    
                        dbc.Accordion(
                            [
                                # ────────────────────────────────
                                # 1️Contents: Sub-components
                                # ────────────────────────────────
                                html.Div(
                                    dbc.AccordionItem(
                                        [
                                            dash_table.DataTable(
                                                id="subcomp-info-table",
                                                cell_selectable=False,
                                                css=[
                                                    {"selector": "tr:hover", "rule": "background-color: inherit !important; cursor: default;"},
                                                    {"selector": "tr:hover td", "rule": "background-color: inherit !important;"},
                                                    {"selector": "td.dash-cell.focused", "rule": "background-color: inherit !important; box-shadow: none !important;"},
                                                    {"selector": "td.cell--active", "rule": "background-color: inherit !important;"},
                                                    {"selector": "td.cell--selected", "rule": "background-color: inherit !important;"},
                                                ],
                                                columns=[
                                                    {"name": "Type Name" , "id": "subtype"},
                                                    {"name": "Func. Pos.", "id": "subfunc"},
                                                    {"name": "PID"       , "id": "subpid"},
                                                ],
                                                data=[],
                                                style_table={
                                                    "width": "100%",
                                                    "overflowX": "hidden",
                                                    "borderRadius": "8px",
                                                },
                                                style_cell={
                                                    "textAlign": "left",
                                                    "fontFamily": "Arial, sans-serif",
                                                    "fontSize": "15px",
                                                    "padding": "6px 10px",
                                                },
                                                style_header={
                                                    "backgroundColor": "#4A90E2",
                                                    "color": "white",
                                                    "fontWeight": "bold",
                                                    "fontSize": "16px",
                                                },
                                                style_data={
                                                    "backgroundColor": "white",
                                                },
                                                style_cell_conditional=[
                                                    {"if": {"column_id": "field"}, "width": "30%", "fontWeight": "bold"},
                                                    {"if": {"column_id": "value"}, "width": "70%"},
                                                ],
                                                style_data_conditional=[
                                                    {"if": {"state": "active"},   "backgroundColor": "inherit", "border": "inherit"},
                                                    {"if": {"state": "selected"}, "backgroundColor": "inherit", "border": "inherit"},
                                                ],
                                            ),
                                        ],
                                        title="Contents (sub-components):",
                                        item_id="subcomp-info",
                                    ),
                                    style={"marginBottom": "16px"},
                                ),

                                # ────────────────────────────────
                                # 2️Pre-shipping
                                # ────────────────────────────────
                                html.Div(
                                    dbc.AccordionItem(
                                        [
                                            html.Div("Consortium QA Rep: —"    , id="info-box-qarep", className="info-card"),
                                            html.Div("POC: —"                  , id="info-box-poc"  , className="info-card"),
                                            html.Div("Origin: —"               , id="info-box-ori"  , className="info-card"),
                                            html.Div("Destination: —"          , id="info-box-des"  , className="info-card"),
                                            html.Div("Dimension: —"            , id="info-box-dim"  , className="info-card"),
                                            html.Div("Weight: —"               , id="info-box-wei"  , className="info-card"),
                                            html.Div("FF name: —"              , id="info-box-ffn"  , className="info-card"),
                                            html.Div("Mode of Trans.: —"       , id="info-box-mod"  , className="info-card"),
                                            html.Div("Expected Arrival Date: —", id="info-box-exd"  , className="info-card"),
                                            html.Div("Acknowledged by who?: —" , id="info-box-acn"  , className="info-card"),
                                            html.Div("When acknowledged?: —"   , id="info-box-act"  , className="info-card"),
                                            html.Div("Visual Inspection: —"    , id="info-box-vis"  , className="info-card"),
                                        ],
                                        title="Pre-shipping",
                                        item_id="preshipping",
                                    ),
                                    style={"marginBottom": "16px"},
                                ),

                                # ────────────────────────────────
                                # 3️Shipping
                                # ────────────────────────────────
                                html.Div(
                                    dbc.AccordionItem(
                                        [
                                            html.Div(
                                                [
                                                    html.Button(
                                                        "⬇️ Download Bill of Lading",
                                                        id={"type": "download-button", "index": "bol"},
                                                        n_clicks=0,
                                                        className="bol-btn",
                                                    ),
                                                    dcc.Store(id={"type": "image-id-store", "index": "bol"}),
                                                    dcc.Store(id={"type": "image-status-store", "index": "bol"}), 
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "justifyContent": "center",
                                                    "marginBottom": "12px"
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    html.Button(
                                                        "⬇️ Download Proforma Invoice",
                                                        id={"type": "download-button", "index": "proforma"},
                                                        n_clicks=0,
                                                        className="proforma-btn",
                                                    ),
                                                    dcc.Store(id={"type": "image-id-store", "index": "proforma"}),
                                                    dcc.Store(id={"type": "image-status-store", "index": "proforma"}), 
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "justifyContent": "center",
                                                    "marginBottom": "12px"
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    html.Button(
                                                        "⬇️ Download final approval message",
                                                        id={"type": "download-button", "index": "approval"},
                                                        n_clicks=0,
                                                        className="approval-btn",
                                                    ),
                                                    dcc.Store(id={"type": "image-id-store", "index": "approval"}),
                                                    dcc.Store(id={"type": "image-status-store", "index": "approval"}), 
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "justifyContent": "center",
                                                    "marginBottom": "12px"
                                                },
                                            ),
                                            html.Div("Final approved by who?: —"  , id="info-box-appwho", className="info-card"),
                                            html.Div("Final approved when?: —"    , id="info-box-apptime", className="info-card"),
                                            html.Div("Shipping label attached?: —", id="info-box-attached", className="info-card"),
                                            html.Div("Shipment insured?: —"       , id="info-box-insured", className="info-card"),
                                        ],
                                        title="Shipping",
                                        item_id="shipping",
                                    ),
                                    style={"marginBottom": "16px"},
                                ),

                                # ────────────────────────────────
                                # 4️Warehouse
                                # ────────────────────────────────
                                html.Div(
                                    dbc.AccordionItem(
                                        [
                                            html.Div("SKU: —"               , id="info-wh-sku", className="info-card"),
                                            html.Div("PalletID: —"          , id="info-wh-pal", className="info-card"),
                                            html.Div("Scanned date/time: —" , id="info-wh-tim", className="info-card"),
                                            html.Div("Person received: —"   , id="info-wh-per", className="info-card"),
                                            html.Div("Visual inspection: —" , id="info-wh-vis", className="info-card"),
                                        ],
                                        title="Info @ Warehouse",
                                        item_id="warehouse",
                                    ),
                                    style={"marginBottom": "16px"},
                                ),

                            ],
                            start_collapsed=True,  # all closed initially
                            #flush=True,            # flat edges, no borders between items
                            always_open=True,      # allows multiple open at once
                            id="shipment-info-accordion",
                        ),

                    ],
                ),
            ],
        ),


        

    ],
)

# The next project tab
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
                    dcc.Tab(label="The next project", value="down-tab", className="custom-tab"),
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
    
    html.Div(
        id="tab-typegetter-content",
        children=[typegetter_layout()],
        style={"display": "none"},  # hidden initially; switch_tabs() will show it
    ),
    plot_tab_layout,
    shipment_tab_layout,
    down_tab_layout,

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
    
