from dash import html, dcc
import dash_bootstrap_components as dbc

# =========================
# Pre-Filters
# =========================
prefilter_panel = html.Div(
    [
        html.H4("Pre-Filters", className="prefilter-title"),

        html.Div(
            [

                html.Div(
                    [
                        html.Label("PID"),
                        dcc.Input(
                            id="prefilter-pid",
                            placeholder="Enter a PID",
                            type="text",
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),

                html.Div(
                    [
                        html.Label("Serial Number"),
                        dcc.Input(
                            id="prefilter-serialnum",
                            placeholder="Enter a Serial #",
                            type="text",
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),

                html.Div(
                    [
                        html.Label("Manufacturer"),
                        dcc.Input(
                            id="prefilter-manu",
                            placeholder="Enter a Manufacturer",
                            type="text",
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),

                html.Div(
                    [
                        html.Label("Creator"),
                        dcc.Input(
                            id="prefilter-creator",
                            placeholder="Enter a Creator",
                            type="text",
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),

                html.Div(
                    [
                        html.Label("Comments"),
                        dcc.Input(
                            id="prefilter-comments",
                            placeholder="Enter comments",
                            type="text",
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),

                html.Div(
                    [
                        html.Label("Location"),
                        dcc.Input(
                            id="prefilter-location",
                            placeholder="Enter a location ID",
                            type="text",
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),

                html.Div(
                    [
                        html.Label("Country of Origin"),
                        dcc.Input(
                            id="prefilter-country",
                            placeholder="Enter a country name",
                            type="text",
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),

                html.Div(
                    [
                        html.Label("Institution"),
                        dcc.Input(
                            id="prefilter-institution",
                            placeholder="Institution name",
                            type="text",
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),

                html.Div(
                    [
                        html.Label("Component Status"),
                        dcc.Dropdown(
                            id="prefilter-status",
                            options=[
                                {"label": s, "value": s}
                                for s in [
                                    "Unknown",
                                    "In Fabrication",
                                    "Waiting on QA/QC Tests",
                                    "QA/QC Tests - Passed All",
                                    "QA/QC Tests - Non-conforming",
                                    "QA/QC Tests - Use As Is",
                                    "In Rework",
                                    "In Repair",
                                    "Permanently Unavailable",
                                    "Broken or Needs Repair",
                                    "Available (deprecated)",
                                    "Temporarily Unavailable (deprecated)",
                                    "Permanently Unavailable (deprecated)",
                                ]
                            ],
                            placeholder="Select status",
                            clearable=True,
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),

                html.Div(
                    [
                        html.Label("Is Installed?"),
                        dcc.Dropdown(
                            id="prefilter-isinstalled",
                            options=[{"label": d, "value": d} for d in ["YES", "NO"]],
                            placeholder="Select detector",
                            clearable=True,
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),

                html.Div(
                    [
                        html.Label("Consoritum QA/QC certified?"),
                        dcc.Dropdown(
                            id="prefilter-consortiumcert",
                            options=[{"label": d, "value": d} for d in ["YES", "NO"]],
                            placeholder="Select detector",
                            clearable=True,
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),

                html.Div(
                    [
                        html.Label("QA/QC tests/docs uploaded?"),
                        dcc.Dropdown(
                            id="prefilter-qaqcuploaded",
                            options=[{"label": d, "value": d} for d in ["YES", "NO"]],
                            placeholder="Select detector",
                            clearable=True,
                            style={"width": "100%"},
                        ),
                    ],
                    className="filter-cell",
                ),
            ],
            className="filter-grid",
        ),
    ],
    className="prefilter-panel",
)


def plots_layout():
    """Layout for the Plots tab."""
    return html.Div(
        id="plot-tab-content",
        children=[
            html.Div(style={"marginBottom": "40px"}),  # some space...

            # ------------------------
            # Pre-filters
            # ------------------------
            prefilter_panel,
            html.Div(style={"marginBottom": "50px"}),

            # ------------------------
            # Type ID, Test Type, Sync, Uploads
            # ------------------------
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
                            "width": "250px",
                            "height": "45px",
                            "fontSize": "16px",
                            "fontWeight": "400",
                            "padding": "10px 15px",
                            "borderRadius": "12px",
                            "border": "2px solid #007BFF",
                            "marginLeft": "10px",
                            "marginRight": "50px",
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
                            "width": "350px",
                            "height": "45px",
                            "fontSize": "16px",
                            "fontWeight": "400",
                            "padding": "10px 15px",
                            "borderRadius": "12px",
                            "border": "2px solid #007BFF",
                            "marginRight": "50px",
                            "textAlign": "center",
                        },
                    ),
                    # Sync button
                    html.Button(
                        "Sync to the HWDB",
                        id="load-json",
                        n_clicks=0,
                        style={
                            "fontSize": "20px",
                            "padding": "14px 32px",
                            "backgroundColor": "#4CAF50",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "8px",
                            "cursor": "pointer",
                            "transition": "all 0.2s ease-in-out",
                            "gap": "15px",
                            "marginRight": "50px",
                        },
                    ),
                    # Select JSON/CSV/PKL
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
                                "transition": "all 0.2s ease-in-out",
                                "marginRight": "50px",
                            },
                        ),
                        multiple=False,
                        accept=".pkl,.pickle,.csv",
                    ),
                    # Overlay CSV
                    dcc.Upload(
                        id="upload-overlay",
                        children=html.Button(
                            "Select a csv to overlay",
                            style={
                                "fontSize": "20px",
                                "padding": "14px 32px",
                                "backgroundColor": "#9C27B0",
                                "color": "white",
                                "border": "none",
                                "borderRadius": "8px",
                                "cursor": "pointer",
                                "transition": "all 0.2s ease-in-out",
                                "marginRight": "50px",
                            },
                        ),
                        multiple=False,
                        accept=".csv",
                    ),
                    dcc.Store(id="overlay-store"),
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": "1px"},
            ),

            # Display information about downloaded contents
            html.Div(id="downloaded-output"),
            html.Div(style={"marginBottom": "40px"}),

            html.Hr(),
            html.Div(style={"marginBottom": "20px"}),

            # ------------------------
            # Plot settings
            # ------------------------
            html.Label(
                "Select chart type:",
                style={
                    "fontSize": "20px",
                    "padding": "4px 32px",
                    "backgroundColor": "#BEBDB8",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "8px",
                    "cursor": "pointer",
                    "marginLeft": "10px",
                },
            ),
            html.Div(
                [
                    dcc.Dropdown(
                        id="chart-type",
                        options=[
                            {"label": "Histogram", "value": "histogram"},
                            {"label": "Histogram (log-Y)", "value": "histogram_log"},
                            {"label": "Cumulative Histogram", "value": "cumhist"},
                            {"label": "Scatter", "value": "scatter"},
                            #{"label": "2D Histogram", "value": "hist2d"},
                            {"label": "Line", "value": "line"},
                            {"label": "Boxplot", "value": "box"},
                        ],
                        value="histogram",
                        placeholder="Select a type",
                        clearable=False,
                        style={
                            "fontSize": "20px",
                            "padding": "0px 0px",
                            "width": "300px",
                            "backgroundColor": "#D9DDDC",
                            "color": "gray",
                            "border": "none",
                            "borderRadius": "8px",
                            "cursor": "pointer",
                            "font-family": "Arial, sans-serif",
                            "marginRight": "50px",
                            "marginLeft": "10px",
                        },
                    ),
                    # number of bins
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
            html.Div(style={"marginBottom": "20px"}),

            # ------------------------
            # 1D variable selection
            # ------------------------
            html.Label(
                "Select a variable for 1D distribution:",
                id="plot-column-label",
                style={
                    "fontSize": "20px",
                    "padding": "4px 32px",
                    "backgroundColor": "#BEBDB8",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "8px",
                    "font-family": "Arial, sans-serif",
                    "cursor": "pointer",
                    "marginLeft": "10px",
                },
            ),
            html.Div(
                dcc.Dropdown(
                    id="plot-column",
                    options=[],
                    value=None,
                    placeholder="Select a variable",
                    clearable=False,
                    style={
                        "fontSize": "20px",
                        "padding": "0px 0px",
                        "backgroundColor": "#D9DDDC",
                        "color": "gray",
                        "border": "none",
                        "borderRadius": "8px",
                        "cursor": "pointer",
                        "boxShadow": "0 6px 10px rgba(0, 0, 0, 0.3)",
                        "transition": "all 0.2s ease-in-out",
                        "font-family": "Arial, sans-serif",
                        "marginLeft": "10px",
                    },
                ),
                style={"marginLeft": "10px", "marginRight": "10px"},
            ),

            # ------------------------
            # Variable filter
            # ------------------------
            html.Div(
                [
                    html.Label(
                        "Select values of the selected variable (only on X-axis):",
                        style={
                            "fontSize": "20px",
                            "padding": "4px 32px",
                            "backgroundColor": "#BEBDB8",
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
                            "fontSize": "20px",
                            "width": "600px",
                            "padding": "0px 0px",
                            "backgroundColor": "#D9DDDC",
                            "color": "gray",
                            "border": "none",
                            "borderRadius": "8px",
                            "cursor": "pointer",
                            "font-family": "Arial, sans-serif",
                            "transition": "all 0.2s ease-in-out",
                            "marginLeft": "10px",
                        },
                    ),
                    dbc.Checklist(
                        id="invert-selection-toggle",
                        options=[
                            {"label": "Exclude selected bins", "value": "exclude"}
                        ],
                        value=[],
                        switch=True,
                        style={"marginLeft": "15px", "marginTop": "6px"},
                    ),
                ],
                id="filter-container",
                style={"display": "none", "marginLeft": "10px"},
            ),

            html.Div(style={"marginBottom": "20px"}),

            # ------------------------
            # Scatter controls (2D)
            # ------------------------
            html.Div(
                [
                    html.Label(
                        "Select X-axis:",
                        style={"font-family": "Arial, sans-serif"},
                    ),
                    dcc.Dropdown(
                        id="scatter-x",
                        options=[],
                        value=None,
                        placeholder="Select X column",
                        style={"font-family": "Arial, sans-serif"},
                    ),
                    html.Label(
                        "Select Y-axis:",
                        style={"font-family": "Arial, sans-serif"},
                    ),
                    dcc.Dropdown(
                        id="scatter-y",
                        options=[],
                        value=None,
                        placeholder="Select Y column",
                        style={"font-family": "Arial, sans-serif"},
                    ),
                ],
                id="scatter-controls",
                style={"display": "none"},
            ),

            html.Hr(),

            # ------------------------
            # Histogram 2D plot
            # ------------------------
            html.Div(
                [
                    html.Label(
                        "Select X-axis:",
                        style={"font-family": "Arial, sans-serif"}
                    ),
                    dcc.Dropdown(
                        id="hist2d-x",
                        options=[],
                        value=None,
                        placeholder="Select X column",
                        style={"font-family": "Arial, sans-serif"}
                    ),
                    html.Label(
                        "Select Y-axis:",
                        style={"font-family": "Arial, sans-serif"}
                    ),
                    dcc.Dropdown(
                        id="hist2d-y",
                        options=[],
                        value=None,
                        placeholder="Select Y column",
                        style={"font-family": "Arial, sans-serif"}
                    ),
                ],
                id="hist2d-controls",
                style={"display":"none"}
            ),

            # ------------------------
            # Conditions controls
            # ------------------------
            html.Div(
                [
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
                        options=[
                            {"label": "AND", "value": "and"},
                            {"label": "OR", "value": "or"},
                        ],
                        value="and",
                        clearable=False,
                    ),
                    html.Button(
                        "Add condition",
                        id="add-condition",
                        n_clicks=0,
                        style={
                            "fontSize": "20px",
                            "padding": "14px 32px",
                            "backgroundColor": "#4CAF50",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "8px",
                            "cursor": "pointer",
                            "transition": "all 0.2s ease-in-out",
                            "font-family": "Arial, sans-serif",
                            "marginRight": "30px",
                        },
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

            # List of applied conditions (chips)
            html.Div(
                id="condition-container",
                style={
                    "fontSize": "18px",
                    "marginRight": "15px",
                    "font-family": "Arial, sans-serif",
                    "textAlign": "center",
                },
            ),

            html.Hr(),

            # ------------------------
            # Graph + status
            # ------------------------
            html.Div(
                [
                    html.Div(
                        id="conditions-display",
                        style={
                            "textAlign": "center",
                            "marginBottom": "15px",
                            "fontWeight": "bold",
                            "font-family": "Arial, sans-serif",
                            "display": "flex",
                            "flexWrap": "wrap",
                            "justifyContent": "center",
                            "gap": "10px",
                        },
                    ),
                    html.Div(
                        id="status-display",
                        style={
                            "textAlign": "left",
                            "fontFamily": "Arial, sans-serif",
                            "fontSize": "18px",
                            "color": "gray",
                            "marginBottom": "10px",
                            "height": "25px",
                            "marginLeft": "5px",
                        },
                    ),
                    dcc.Loading(
                        id="loading-plot",
                        type="circle",
                        color="#007ACC",
                        children=dcc.Graph(id="distribution-plot"),
                    ),
                ]
            ),

            html.Hr(),

            # ------------------------
            # Save filtered CSV
            # ------------------------
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
                            "fontSize": "20px",
                            "padding": "14px 32px",
                            "backgroundColor": "#4CAF50",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "8px",
                            "cursor": "pointer",
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

            dcc.Interval(
                id="save-status-timer", interval=3000, n_intervals=0, disabled=True
            ),
            dcc.Download(id="download-dataframe-csv"),

            # ------------------------
            # Hidden stores
            # ------------------------
            dcc.Store(id="data-store", storage_type="memory"),
            dcc.Store(id="filtered-store", storage_type="memory"),  # This needs to be right after data-store!
            dcc.Store(id="plot-config-store", storage_type="memory"),
            #
            # To update the download completion status
            dcc.Store(id="plots-job-id", storage_type="memory"),
            dcc.Store(id="plots-total", storage_type="memory"),
            dcc.Store(id="plots-processed", storage_type="memory"),
            dcc.Interval(id="plots-interval", interval=1000, disabled=True),
            dcc.Store(id="plot-sync-job-id", storage_type="memory"),
            dcc.Interval(id="plot-sync-interval", interval=1000, disabled=True),
            dcc.Store(id="sync-status", data=None), # only state, no UI stuff
        ],
        style={"display": "block"},
    )
