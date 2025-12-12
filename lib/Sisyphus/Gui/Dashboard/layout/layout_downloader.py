from dash import html, dcc
import dash_bootstrap_components as dbc


def downloader_layout():
    return html.Div(
        id="downloader-tab-content",
        style={"padding": "25px"},
        children=[
            
            dcc.Store(id="downloader-testdata-store", storage_type="memory"),
            dcc.Store(id="downloader-schema-store", storage_type="memory"),
            #dcc.Store(id="downloader-pid-store", storage_type="memory"),
            dcc.Store(id="downloader-memory-store", storage_type="local"),
            dcc.Store(id="downloader-job-id", storage_type="memory"),   # shared state
            dcc.Interval(id="downloader-interval",
                interval=1000,  # in ms = 1sec)
                n_intervals=0,
                disabled=True), # gets enabled by "start_download_job"
            # for binaries
            dcc.Store(id="binary-memory-store", storage_type="local"),
            dcc.Store(id="binary-file-meta", storage_type="memory"),
            dcc.Store(id="binary-sync-trigger", storage_type="memory"),
            dcc.Interval(id="binary-download-interval", interval=1000, disabled=True),
            dcc.Store(id="binary-download-job-id", data=None),
        
            #html.H2(
            #    "Downloader",
            #    style={
            #        "textAlign": "center",
            #        "fontWeight": "bold",
            #        "marginBottom": "20px",
            #        "fontFamily": "Arial, sans-serif",
            #    },
            #),

            html.Div(style={"marginBottom": "20px"}),

            # ===========================
            # MODE SELECTOR: tests/binaries
            # ===========================
            html.Div(
                [
                    html.Label(
                        "What do you want to download?",
                        style={
                            "fontSize": "20px",
                            "fontFamily": "Arial, sans-serif",
                            "marginRight": "25px",
                        },
                    ),
                    dbc.RadioItems(
                        id="download-mode",
                        options=[
                            {"label": "Test Data", "value": "tests"},
                            {"label": "Binaries", "value": "binaries"},
                        ],
                        value="tests",  # default
                        inline=True,
                        style={"fontSize": "18px", "fontFamily": "Arial, sans-serif"},
                    ),
                ],
                style={"display": "flex", "alignItems": "center"},
            ),

            html.Hr(),

            # ============================================================
            # TEST DATA SECTION  (existing UI wrapped here)
            # ============================================================
            html.Div(
                id="downloader-test-section",
                children=[
            
                    # ==== File Format Selection (only for Test Data) ====
                    html.Div(
                        id="format-selection",
                        style={"display": "block"},  # visible when mode == test
                        children=[
                            html.Label(
                                "Download Test Data as:",
                                style={
                                    "fontSize": "20px",
                                    "fontFamily": "Arial, sans-serif",
                                },
                            ),
                            dbc.RadioItems(
                                id="testdata-format",
                                options=[
                                    {"label": "CSV", "value": "csv"},
                                    {"label": "JSON", "value": "json"},
                                ],
                                value="csv",  # default
                                inline=True,
                                style={
                                    "fontSize": "18px",
                                    "fontFamily": "Arial, sans-serif",
                                    "marginLeft": "25px",
                                },
                            ),
                        ],
                    ),

                    html.Hr(),

                    # ==== Component Type ID + Test Type ====
                    html.Div(
                        style={
                            "marginTop": "10px",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "35px",
                        },
                        children=[
                            dcc.Input(
                                id="downloader-refpid",
                                type="text",
                                placeholder="Enter a Reference PID",
                                className="text-center",
                                style={
                                    "width": "220px",
                                    "height": "45px",
                                    "fontSize": "16px",
                                    "borderRadius": "10px",
                                    "border": "2px solid #007BFF",
                                },
                            ),
                            dcc.Input(
                                id="downloader-testname",
                                type="text",
                                placeholder="Enter Test Type Name",
                                className="text-center",
                                style={
                                    "width": "350px",
                                    "height": "45px",
                                    "fontSize": "16px",
                                    "borderRadius": "10px",
                                    "border": "2px solid #007BFF",
                                },
                            ),
                            html.Button(
                                "Sync to the HWDB",
                                id="downloader-sync",
                                n_clicks=0,
                                style={
                                    "fontSize": "20px",
                                    "padding": "14px 32px",
                                    "backgroundColor": "#4CAF50",
                                    "color": "white",
                                    "border": "none",
                                    "borderRadius": "8px",
                                    "cursor": "pointer",
                                },
                            ),
                        ],
                    ),

                    html.Div(style={"marginTop": "30px"}),

                    # ==== Placeholder where schema UI will appear ====
                    html.Div(
                        id="downloader-schema-ui",
                        style={
                            "display": "none",
                            "padding": "10px",
                            "marginTop": "15px",
                        },
                    ),

                    # ==== Placeholder for PID selection UI ====
                    html.Div(
                        id="downloader-pid-list",
                        style={
                            "display": "none",
                            "padding": "10px",
                            "marginTop": "15px",
                        },
                    ),


                    # === PIDs selector ===
                    html.Div(
                        id="downloader-pid-range-ui",
                        style={
                            "display": "none", # Hide unti "synced"
                            "marginTop": "20px"
                        },
                        children=[
                    
                            html.Label("Select PID Range (optional):", style={"fontSize": "18px"}),

                            html.Div(
                                style={"display": "flex", "gap": "20px", "marginTop": "10px", "alignItems": "center"},
                                children=[
                                    dcc.Input(
                                        id="downloader-first-pid",
                                        type="text",
                                        placeholder="First PID",
                                        style={
                                            "width": "250px",
                                            "height": "45px",
                                            "fontSize": "16px",
                                            "borderRadius": "10px",
                                            "border": "2px solid #007BFF",
                                            "textAlign": "center",
                                        },
                                    ),
                                    dcc.Input(
                                        id="downloader-last-pid",
                                        type="text",
                                        placeholder="Last PID",
                                        style={
                                            "width": "250px",
                                            "height": "45px",
                                            "fontSize": "16px",
                                            "borderRadius": "10px",
                                            "border": "2px solid #007BFF",
                                            "textAlign": "center",
                                        },
                                    ),
                                ],
                            ),
                    
                            html.Div(id="downloader-pid-count", style={"fontSize": "18px", "marginBottom": "10px"}),
                        ],
                    ),
            
                    # ==== Download button placeholder ====
                    html.Div(
                        id="downloader-final-actions",
                        style={
                            "display": "none",
                            "padding": "10px",
                            "marginTop": "20px",
                        },
                        children=[
                            html.Button(
                                "Download Selected Data",
                                id="downloader-start-download",
                                n_clicks=0,
                                disabled=False,
                                style={
                                    "fontSize": "20px",
                                    "padding": "14px 32px",
                                    "backgroundColor": "#4CAF50",
                                    #"backgroundColor": "#FF5722",
                                    "color": "white",
                                    "border": "none",
                                    "borderRadius": "8px",
                                    "cursor": "pointer",
                                    "textAlign": "center",
                                    "margin": "0 auto"
                                },
                            ),
                            html.Div(id="downloader-status", style={"marginTop": "15px", "color": "green"})
                        ],
                    ),
                ],
            ),
            # ============================================================
            # BINARIES SECTION (new)
            # ============================================================
            html.Div(
                id="downloader-binary-section",
                style={"display": "none", "marginTop": "25px"},
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "12px"},
                        children=[
                            dcc.Input(
                                id="binary-id-input",
                                type="text",
                                placeholder="Enter a Component Type ID or a PID",
                                style={
                                    "width": "360px",
                                    "height": "45px",
                                    "fontSize": "16px",
                                    "borderRadius": "10px",
                                    "border": "2px solid #007BFF",
                                    "textAlign": "center",
                                },
                            ),
                            dbc.Button(
                                "Sync to the HWDB",
                                id="binary-sync-button",
                                n_clicks=0,
                                style={
                                    "fontSize": "18px",
                                    "padding": "10px 30px",
                                    "backgroundColor": "#4CAF50",
                                    "color": "white",
                                    "border": "none",
                                    "borderRadius": "8px",
                                },
                            ),
                        ],
                    ),

                    html.Div(id="binary-sync-status", style={"marginTop": "10px"}),

                    # LIST + SELECT/DESELECT
                    html.Div(
                        style={"marginTop": "18px"},
                        children=[
                            html.Div(
                                style={"display": "flex", "gap": "10px", "marginBottom": "8px"},
                                children=[
                                    dbc.Button(
                                        "Select all",
                                        id="binary-select-all",
                                        size="sm",
                                        style={
                                            "backgroundColor": "#2196F3",
                                            "color": "white",
                                            "border": "none",
                                            "borderRadius": "6px",
                                            "padding": "4px 12px",
                                        },
                                    ),
                                    dbc.Button(
                                        "Deselect all",
                                        id="binary-deselect-all",
                                        size="sm",
                                        style={
                                            "backgroundColor": "#2196F3",
                                            "color": "white",
                                            "border": "none",
                                            "borderRadius": "6px",
                                            "padding": "4px 12px",
                                        },
                                    ),
                                ],
                            ),
                            html.Div(
                                id="binary-file-list-container",
                                style={
                                    "maxHeight": "260px",
                                    "overflowY": "auto",
                                    "border": "1px solid #ccc",
                                    "padding": "8px 12px",
                                    "borderRadius": "6px",
                                },
                                children=[
                                    dcc.Checklist(
                                        id="binary-file-checklist",
                                        options=[],
                                        value=[],
                                        style={"fontFamily": "Courier New, monospace", "fontSize": "15px"},
                                        labelStyle={"display": "block", "marginBottom": "4px"},
                                    )
                                ],
                            ),
                        ],
                    ),

                    html.Div(
                        style={"marginTop": "18px"},
                        children=[
                            dbc.Button(
                                "Download",
                                id="binary-download-button",
                                n_clicks=0,
                                style={
                                    "fontSize": "18px",
                                    "padding": "10px 30px",
                                    "backgroundColor": "#4CAF50",
                                    "color": "white",
                                    "borderRadius": "8px",
                                    "border": "none",
                                },
                            ),
                            html.Span(
                                id="binary-download-status",
                                style={"marginLeft": "12px", "fontSize": "16px"},
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
