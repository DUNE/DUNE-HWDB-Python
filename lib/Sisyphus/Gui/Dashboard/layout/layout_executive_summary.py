from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import dash_ag_grid as dag

# Turn-on/off the scanner feature
import os
#ENABLE_SCANNER = os.getenv("HWDB_ENABLE_SCANNER", "0") == "1"
ENABLE_SCANNER = 0

#---------------------------------------


visible_cols = [
    {"field":"parent_pid","headerName":"Parent PID","minWidth":220, "aggFunc":"first"},
    {"field":"n_children","headerName":"# of children","width":140, "minWidth":160, "aggFunc":"first"},    # wider
    #{"field":"type_name","headerName":"Type Name","minWidth":260, "width":320, "aggFunc":"first"},        # longer
    {"field":"type_name", "headerName":"Type Name", "minWidth":260, "flex": 2, "aggFunc":"first"},         # let EAT the extra space
    #{"field":"position_name","headerName":"Position Name","minWidth":220, "width":260, "aggFunc":"first"},
    {"field":"position_name", "headerName":"Position Name", "minWidth":220, "flex": 1, "aggFunc":"first"}, # let EAT the extra space

    {"field":"status","headerName":"Status","width":230, "minWidth": 250, "aggFunc":"first"},
    {"field":"certified","headerName":"Certified","width":130, "minWidth":150, "aggFunc":"first"},         # wider
    {"field":"uploaded","headerName":"Uploaded","width":130, "minWidth":150, "aggFunc":"first"},           # wider
]



# Hidden grouping columns (triangles come from these groups)
hidden_group_cols = [
    {"headerName": "L0",  "field": "g0",  "rowGroup": True, "hide": True},
    {"headerName": "L1",  "field": "g1",  "rowGroup": True, "hide": True},
    {"headerName": "L2",  "field": "g2",  "rowGroup": True, "hide": True},
    {"headerName": "L3",  "field": "g3",  "rowGroup": True, "hide": True},
    {"headerName": "L4",  "field": "g4",  "rowGroup": True, "hide": True},
    {"headerName": "L5",  "field": "g5",  "rowGroup": True, "hide": True},
    {"headerName": "L6",  "field": "g6",  "rowGroup": True, "hide": True},
    {"headerName": "L7",  "field": "g7",  "rowGroup": True, "hide": True},
    {"headerName": "L8",  "field": "g8",  "rowGroup": True, "hide": True},
    {"headerName": "L9",  "field": "g9",  "rowGroup": True, "hide": True},
    {"headerName": "L10", "field": "g10", "rowGroup": True, "hide": True},
    {"headerName": "L11", "field": "g11", "rowGroup": True, "hide": True},
]

group_display_col = {
    "colId": "hierarchy",
    "headerName": "Hierarchy",
    "minWidth": 260,
    "width": 300,              # set an initial width
    #"flex": 1,                 # take remaining space
    "suppressSizeToFit": True, # prevents flex/sizeToFit from re-widening it
    
    # show full text on hover!!
    "tooltipField": "g11",   # this doesn't matter much; we would override via valueGetter
    "tooltipValueGetter": {
        "function": """
        function(p){
          // group rows: key is the displayed PID
          if (p.node && p.node.group) return p.node.key || '';
          // leaf rows: if you ever show them
          return (p.data && p.data.pid) || (p.value || '');
        }
        """
    },
    
    "showRowGroup": True,      # renders the grouping UI
    "cellRenderer": "agGroupCellRenderer",
    "cellRendererParams": {"suppressCount": True},
}



def execsum_layout():

    mode_btn = dbc.Button(
        "DETAIL",
        id="execsum-mode-toggle",
        n_clicks=0,
        color="secondary",
        outline=True,
        style={"height":"45px","borderRadius":"10px","marginRight":"8px","fontWeight":"900"},
    )
    
    # -----------------------------
    # Scanner UI blocks (Option A)
    # -----------------------------
    scan_bits = []
    scan_btn = None

    if ENABLE_SCANNER:
        scan_btn = dbc.Button(
            "📷",
            id="execsum-scan-open",
            n_clicks=0,
            color="secondary",
            outline=True,
        )

        scan_bits = [
            # Scanning
            dcc.Store(id="execsum-scan-token", storage_type="memory"),
            dcc.Store(id="execsum-scan-url", storage_type="memory"),
            dcc.Store(id="execsum-scan-open-url", storage_type="memory"),
            html.Div(id="execsum-scan-open-url-sink", style={"display": "none"}),
            dcc.Interval(id="execsum-scan-poll", interval=600, disabled=True),

            dbc.Modal(
                id="execsum-scan-modal",
                is_open=False,
                centered=True,
                size="lg",
                children=[
                    dbc.ModalHeader(dbc.ModalTitle("Scan with your phone")),
                    dbc.ModalBody(
                        [
                            html.Div("1) Open your phone camera and scan this QR:", style={"fontWeight": "700"}),
                            html.Br(),
                            html.Img(
                                id="execsum-scan-qr-img",
                                src="",
                                style={
                                    "width": "260px",
                                    "height": "260px",
                                    "display": "block",
                                    "margin": "0 auto",
                                    "borderRadius": "12px",
                                    "border": "1px solid #E0E6EF",
                                    "backgroundColor": "white",
                                },
                            ),
                            html.Br(),
                            html.Div(
                                "2) The phone page will scan your QR/barcode and send it back.",
                                style={"color": "#555"},
                            ),
                            html.Div(id="execsum-scan-status", style={"marginTop": "10px", "color": "#666"}),
                            html.Hr(),
                            html.Div("If QR doesn’t work, try these on your phone:", style={"fontWeight": "700"}),
                            html.Div(
                                id="execsum-scan-link",
                                style={"wordBreak": "break-all", "whiteSpace": "pre-wrap"},
                            ),
                        ],
                        style={"maxHeight": "70vh", "overflowY": "auto"},
                    ),
                    dbc.ModalFooter(
                        dbc.Button("Close", id="execsum-scan-close", n_clicks=0, color="secondary")
                    ),
                ],
            ),
        ]
            
    return html.Div(
        #id="execsum-tab-content",
        id="execsum-inner",
        style={"padding": "15px"},
        children=[
            # -----------------------------
            # Stores (parallel to Shipment)
            # -----------------------------
            dcc.Store(id="execsum-config-store", storage_type="local"),          # uploaded JSON config
            dcc.Store(id="execsum-typeid-memory", storage_type="local"),         # persist last typeid
            dcc.Store(id="execsum-type-name", storage_type="local"), 
            #dcc.Store(id="execsum-items-cache", storage_type="memory"),          # items list from get_hwitems
            dcc.Store(id="execsum-job-id", storage_type="memory"),
            #dcc.Store(id="execsum-total", storage_type="memory"),
            #dcc.Store(id="execsum-trigger", storage_type="memory"),
            dcc.Interval(id="execsum-interval", interval=500, disabled=True),

            dcc.Store(id="execsum-plot-selected-pids", data=[], storage_type="memory"), # the "Selected" column
            dcc.Store(id="execsum-todos-existing", storage_type="memory"),              # latest todos payload from HWDB ES test
            dcc.Store(id="execsum-todos-state", storage_type="memory"),                 # current UI checkbox state
            
            dcc.Store(id="execsum-cache-key", storage_type="memory"),
            dcc.Store(id="execsum-selected-pid", storage_type="memory"),
            #dcc.Store(id="execsum-sync-job-id", storage_type="memory"),
            dcc.Store(id="execsum-selected-status", storage_type="memory"),
            #dcc.Store(id="execsum-plot-selected-pids", data=[], storage_type="local"),
            dcc.Store(id="execsum-whoami-name", storage_type="memory"),
            dcc.Store(id="execsum-es-existing", storage_type="memory"),     # existing ES list from HWDB
            dcc.Store(id="execsum-es-status", storage_type="memory"),       # derived status: uploaded ranks, next allowed, etc.
            dcc.Store(id="execsum-signoff-datetime-store", storage_type="memory"),
            #html.Div(id="execsum-signoff-datetime", style={"display":"none"}),
            #dcc.Store(id="execsum-details-state", data={"loading": False}, storage_type="memory"),


            dcc.Store(id="execsum-subcomp-job", storage_type="memory"),
            dcc.Interval(id="execsum-subcomp-interval", interval=250, disabled=True),

            dcc.Store(id="execsum-details-job", storage_type="memory"),
            dcc.Interval(id="execsum-details-interval", interval=250, disabled=True),

            dcc.Store(id="execsum-pdf-job", storage_type="memory"),
            dcc.Interval(id="execsum-pdf-interval", interval=300, disabled=True),


            # for signee buttons
            dcc.Store(id="execsum-sig-job", storage_type="memory"),
            dcc.Store(id="execsum-sig-busy", storage_type="memory"),   # {"name": "..."} while uploading, else None
            dcc.Interval(id="execsum-sig-interval", interval=250, disabled=True),
            dcc.Store(id="execsum-whoami-roles", storage_type="memory"),

            # Scanning
            #dcc.Store(id="execsum-scan-token", storage_type="memory"),
            #dcc.Store(id="execsum-scan-url", storage_type="memory"),
            #dcc.Store(id="execsum-scan-open-url", storage_type="memory"),
            #html.Div(id="execsum-scan-open-url-sink", style={"display": "none"}),
            #dcc.Interval(id="execsum-scan-poll", interval=600, disabled=True),

            # toggle button for "default <-> detail" mode
            dcc.Store(id="execsum-mode", data="detail", storage_type="local"),  # "detail" | "default"
            dcc.Store(id="execsum-has-config", data=False, storage_type="memory"),
            dcc.Store(id="execsum-default-signed", data=False, storage_type="memory"),
            dcc.Store(id="execsum-default-signinfo", data=None, storage_type="memory"), # who signed in DEFAULT mode (for PDF + UI)
            
           #  Confirm-reset modal (global to this tab)
           dbc.Modal(
               id="execsum-reset-confirm-modal",
               is_open=False,
               centered=True,
               backdrop="static",   # click outside won't dismiss
               keyboard=False,      # ESC won't dismiss (optional)
               children=[
                   dbc.ModalHeader(dbc.ModalTitle("Confirm RESET")),
                   dbc.ModalBody(
                       "This is going to reset all signatures that have been signed so far.\n"
                       "Are you absolutely sure to reset?"
                   ),
                   dbc.ModalFooter(
                       [
                           dbc.Button(
                               "No, cancel",
                               id="execsum-reset-confirm-no",
                               color="secondary",
                               n_clicks=0,
                               className="me-2",
                           ),
                           dbc.Button(
                               "Yes, RESET",
                               id="execsum-reset-confirm-yes",
                               color="danger",
                               n_clicks=0,
                           ),
                       ]
                   ),
               ],
            ),
            
            html.Div(style={"marginTop": "35px"}),

            # -----------------------------
            # Config upload
            # -----------------------------
            html.Div(
                style={"display":"flex", "justifyContent":"center"},
                children=[
                    html.Div("No config loaded", id="execsum-config-status", style={"color":"#666"})
                    ]
            ),

            html.Br(),

            # -----------------------------
            # TypeID + Sync button
            # -----------------------------
            html.Div(
                style={"display":"flex", "alignItems":"center", "justifyContent":"center", "marginBottom":"6px"},
                children=[
                    
                    #dbc.Button(
                    #    "📷",
                    #    id="execsum-scan-open",
                    #    n_clicks=0,
                    #    color="secondary",
                    #    outline=True,
                    #),
                    scan_btn,
                    mode_btn,
                    dcc.Input(
                        id="execsum-typeid",
                        type="text",
                        placeholder="Enter Component Type ID",
                        className="text-center",
                        style={
                            "width":"250px",
                            "height":"45px",
                            "fontSize":"16px",
                            "padding":"10px 15px",
                            "borderRadius":"12px",
                            "border":"2px solid #007BFF",
                            "marginLeft":"10px",
                            "marginRight":"50px",
                            "textAlign":"center",
                        },
                    ),
                    dbc.Button(
                        "Sync to the HWDB",
                        id="execsum-sync",
                        n_clicks=0,
                        color="primary",
                        style={
                            "fontSize":"20px",
                            "padding":"14px 32px",
                            "backgroundColor":"#4CAF50",
                            "color":"white",
                            "border":"none",
                            "borderRadius":"8px",
                            "cursor":"pointer",
                            "transition":"all 0.2s ease-in-out",
                            "marginRight":"10px",
                        }
                    ),
                ]
            ),
            *scan_bits,
            #dbc.Modal(
            #    id="execsum-scan-modal",
            #    is_open=False,
            #    centered=True,
            #    size="lg",
            #    children=[
            #        dbc.ModalHeader(dbc.ModalTitle("Scan with your phone")),
            #        dbc.ModalBody(
            #            [
            #                html.Div("1) Open your phone camera and scan this QR:", style={"fontWeight": "700"}),
            #                html.Br(),
            #                
            #                html.Img(
            #                    id="execsum-scan-qr-img",
            #                    src="",
            #                    style={
            #                        "width": "260px",
            #                        "height": "260px",
            #                        #"display": "none",
            #                        "display": "block",
            #                        "margin": "0 auto",
            #                        "borderRadius": "12px",
            #                        "border": "1px solid #E0E6EF",
            #                        "backgroundColor": "white",
            #                    },
            #                ),
            #                
            #                html.Br(),
            #                html.Div(
            #                    "2) The phone page will scan your QR/barcode and send it back.",
            #                    style={"color": "#555"},
            #                ),
            #                html.Div(id="execsum-scan-status", style={"marginTop": "10px", "color": "#666"}),
            #                html.Hr(),
            #                html.Div("If QR doesn’t work, try these on your phone:", style={"fontWeight": "700"}),
            #                html.Div(
            #                    id="execsum-scan-link",
            #                    style={"wordBreak": "break-all", "whiteSpace": "pre-wrap"},
            #                ),
            #            ],
            #            style={"maxHeight": "70vh", "overflowY": "auto"},
            #        ),
            #        dbc.ModalFooter(
            #            dbc.Button("Close", id="execsum-scan-close", n_clicks=0, color="secondary")
            #        ),
            #    ],
            #),

            html.Div(style={"marginBottom": "20px"}),
            
            # Type Name
            html.Div(
                id="execsum-type-name-display",
                style={
                    "textAlign": "center",
                    "fontSize": "20px",
                    "fontWeight": "800",
                    "color": "#0b3d91",
                    "marginTop": "6px",
                    "marginBottom": "10px",
                },
                children="",   # will be filled by callback
            ),

            
            
            html.Br(),

            # -----------------------------
            # PID list table
            # -----------------------------
            html.Div(
                style={
                    "backgroundColor":"#F3F3F3",
                    "padding":"10px",
                    "borderRadius":"12px",
                    "boxShadow":"0 2px 6px rgba(0,0,0,0.15)",
                    "marginBottom":"20px",
                    "marginRight":"10px",
                },
                children=[
                    html.H4("List of components (PIDs)", style={"color":"#004C99", "marginLeft":"10px"}),


                    html.Div(
                        [
                            html.Span(
                                "Certified: ",
                                style={
                                    "marginLeft": "10px",
                                    "fontSize": "17px",
                                    "fontWeight": "bold",
                                    "color": "black",
                                },
                            ),
                            dcc.Link(
                                "Consortium Certified QA/QC flag",
                                href="https://dune.github.io/computing-HWDB/shippinghandoff/index.html#the-two-key-flags",
                                target="_blank",
                                style={"fontSize": "17px", "marginRight": "20px"},
                            ),
                            html.Span(
                                "Uploaded: ",
                                style={
                                    "fontSize": "17px",
                                    "fontWeight": "bold",
                                    "color": "black",
                                },
                            ),
                            dcc.Link(
                                "All QA/QC Test and Documentation Uploaded flag",
                                href="https://dune.github.io/computing-HWDB/shippinghandoff/index.html#the-two-key-flags",
                                target="_blank",
                                style={"fontSize": "17px", "marginRight": "20px"},
                            ),
                        ],
                        style={
                            "fontSize": "14px",
                            "color": "gray",
                            "marginBottom": "8px",
                            "marginTop": "-6px",
                            "fontFamily": "Arial, sans-serif",
                        },
                    ),

                    
                    dash_table.DataTable(
                        id="execsum-pid-table",
                        columns=[
                            #{"name": "Plot", "id": "plot"},
                            {"name":"Selected", "id":"selected"},
                            {"name":"PID", "id":"pid"},
                            {"name":"Serial", "id":"serial"},
                            {"name":"Status", "id":"status"},
                            {"name":"Certified", "id":"certified"},
                            {"name":"Uploaded", "id":"uploaded"},
                        ],
                        data=[],
                        fixed_rows={"headers": True},
                        css=[
                            {"selector":"tr:hover", "rule":"background-color:#E3F2FD !important; cursor:pointer;"},
                            {"selector":"tr:hover td", "rule":"background-color:#E3F2FD !important;"},
                        ],
                        style_table={
                            "height":"30vh",
                            "overflowY":"auto",
                            "overflowX":"hidden",
                            "width":"100%",
                            "tableLayout":"fixed",
                        },
                        style_cell={
                            "textAlign":"center",
                            "fontFamily":"Arial, sans-serif",
                            "fontSize":"16px",
                            "padding":"6px",
                            "whiteSpace":"normal",
                            "height":"auto",
                        },
                        style_header={
                            "backgroundColor":"#4A90E2",
                            "color":"white",
                            "fontWeight":"bold",
                            "fontSize":"17px",
                            "position":"sticky",
                            "top":0,
                            "zIndex":1,
                        },
                        style_cell_conditional=[
                             #{
                             #    "if":{"column_id":"plot"},
                             #    "width":"50px",
                             #    "minWidth":"50px",
                             #    "maxWidth":"50px",
                             #    "fontSize": "26px",
                             #    "fontWeight": "700",
                             #    "padding": "0px",
                             #    "lineHeight": "28px",
                             #},
                            {"if":{"column_id":"selected"}, "width":"40px"},
                            {"if":{"column_id":"pid"}, "width":"160px"},
                            {"if":{"column_id":"serial"}, "width":"160px"},
                            {"if":{"column_id":"status"}, "width":"120px"},
                            {"if":{"column_id":"certified"}, "width":"90px"},
                            {"if":{"column_id":"uploaded"}, "width":"90px"},
                        ],
                    ),
                    # the 3 buttons (+ range picker now)
                    html.Div(
                        style={
                            "display":"flex",
                            "gap":"10px",
                            "marginLeft":"10px",
                            "marginTop":"8px",
                            "alignItems": "center",
                            "flexWrap": "wrap",
                        },
                        children=[
                            dbc.Button("Clear", id="execsum-clear-selected", size="sm", color="secondary", n_clicks=0),
                            dbc.Button("Select all", id="execsum-select-all", size="sm", color="secondary", n_clicks=0),
                            #dbc.Button("Deselect all", id="execsum-deselect-all", size="sm", color="secondary", n_clicks=0),

                            html.Div(style={"width": "18px"}),

                            html.Div(
                                "Item Number:",
                                style={"fontWeight": "700", "color": "#444", "marginRight": "4px"},
                            ),

                            dcc.Input(
                                id="execsum-range-start",
                                type="text",
                                placeholder="Start (e.g. 07000)",
                                debounce=True,
                                style={
                                    "width": "150px",
                                    "height": "30px",
                                    "borderRadius": "8px",
                                    "border": "1px solid #BBB",
                                    "padding": "6px 10px",
                                    "textAlign": "center",
                                },
                            ),
                            html.Div("to", style={"marginLeft": "2px", "marginRight": "2px", "opacity": 0.8}),
                            dcc.Input(
                                id="execsum-range-end",
                                type="text",
                                placeholder="End (e.g. 07100)",
                                debounce=True,
                                style={
                                    "width": "150px",
                                    "height": "30px",
                                    "borderRadius": "8px",
                                    "border": "1px solid #BBB",
                                    "padding": "6px 10px",
                                    "textAlign": "center",
                                },
                            ),

                            dbc.Button(
                                "Select PID range",
                                id="execsum-select-range",
                                size="sm",
                                color="secondary",
                                n_clicks=0,
                            ),
                            dbc.Button(
                                "Clear PID range",
                                id="execsum-clear-range",
                                size="sm",
                                color="secondary",
                                n_clicks=0,
                            ),
                            
                        ],
                    ),
                ],
            ),

            # -----------------------------
            # Sub-component table (This should be shown once a PID is selected)
            # -----------------------------
            html.Div(
                id="execsum-subcomp-wrapper",
                style={"display": "none"},   # hidden until PID selected
                children=[
                    dcc.Loading(
                        id="execsum-loading-subcomp",
                        type="circle",          # "circle" | "dot" | "default"
                        fullscreen=False,
                        children=html.Div(
                            id="execsum-subcomp-section",
                            children=[
                                html.Div(
                                    style={
                                        "backgroundColor":"#F3F3F3",
                                        "padding":"10px",
                                        "borderRadius":"12px",
                                        "boxShadow":"0 2px 6px rgba(0,0,0,0.15)",
                                        "marginBottom":"20px",
                                        "marginRight":"10px",
                                    },
                                    children=[
                                        html.H4("List of sub-components", style={"color":"#004C99", "marginLeft":"10px"}),

                                        html.Div(
                                            id="execsum-subcomp-status",
                                            children="",
                                            style={"marginLeft":"10px", "marginTop":"6px", "color":"#666", "fontStyle":"italic"},
                                        ),
                                        
                                        dag.AgGrid(
                                            id="execsum-subcomp-grid",
                                            enableEnterpriseModules=True,
                                            columnDefs = [group_display_col] + hidden_group_cols + visible_cols,
                                            rowData=[],
                                            #defaultColDef={
                                            #    "resizable": True,
                                            #    "sortable": True,
                                            #    "filter": True,
                                            #    "suppressMenu": True,
                                            #    "suppressNavigable": True,
                                            #    "enableValue": True,
                                            #},
                                            getRowId="params.data.id",
                                            dashGridOptions={
                                                "aggregateOnlyChangedColumns": False,
                                                "groupSuppressAutoColumn": True,
                                                "animateRows": True,
                                                "groupDefaultExpanded": 1,
                                                "groupAllowUnbalanced": True,
                                                "rememberGroupStateWhenNewData": True,
                                                "suppressAggFuncInHeader": True,
                                                "groupDisplayType": "custom",
                                                "groupSuppressBlankHeader": True,
                                                "groupUseEntireRow": False,
                                                "isRowSelectable": {
                                                    "function": "function(params){ return !(params.data && params.data.is_leaf_for_group); }"
                                                    },
                                                "isExternalFilterPresent": {"function": "function(){ return false; }"},
                                                "rowClassRules": {
                                                    # hide helper leaf rows that exist only to supply group values
                                                    "execsum-hide-leaf": "params.data && params.data.is_leaf_for_group === true",
                                                },
                                                "getRowHeight": {"function": "function(p){ return (p.data && p.data.is_leaf_for_group) ? 0 : 42; }"},
                                                "domLayout": "normal",     # this is actually default, but make explicit
                                                "enableBrowserTooltips": True,
                                            },
                                            style={"height": "50vh", "width": "100%"},
                                        )
                                    ],
                                ),
                            ],
                        ),
                    ),
                ],
            ),

            # -----------------------------
            # Bridge spinner: to wait for the DETAIL section
            # -----------------------------
            html.Div(
                id="execsum-details-wait-area",
                style={
                    "minHeight": "55vh", # This gives scroll space while waiting!!
                    "display": "none",
                    "pointerEvents": "none",
                },
                children=[
                    dcc.Loading(
                        id="execsum-loading-details-bridge",
                        type="circle",
                        fullscreen=False,
                        delay_show=150,
                        overlay_style={
                            "backgroundColor": "rgba(0,0,0,0)",
                            "pointerEvents": "none",  
                        },
                        children=html.Div(
                            id="execsum-details-sentinel",
                            # This content will be updated by show_details.
                            # it just exists to drive the spinner.
                            style={"height": "1px"},
                            children="",
                        ),
                    ),

                    # Show some text so users understand what they’re waiting for
                    html.Div(
                        "Preparing details…",
                        id="execsum-details-wait-text",
                        style={"marginTop": "10px", "color": "#666"},
                    ),
                ],
            ),

            
            # -----------------------------
            # Dynamic form + plots
            # -----------------------------
            html.Div(
                id="execsum-details-section",
                style={"display":"flex", "gap":"20px", "justifyContent":"space-between", "opacity": 0.0, "height": 0},
                children=[
                    # LEFT PANEL (form)  ---- make Loading the flex item
                    html.Div(
                        id="execsum-form-panel",
                        style={"flex":"1 1 45%", "minWidth": 0},   # minWidth:0 prevents weird overflow pushing panels apart
                        children=[
                            html.Div(
                                style={
                                    "backgroundColor":"#FAFAFA",
                                    "padding":"12px",
                                    "borderRadius":"12px",
                                    "boxShadow":"0 2px 6px rgba(0,0,0,0.10)",
                                    "maxHeight":"100vh",
                                    "overflowY":"auto",
                                },
                                children=[
                                    # spinner will show because this exact Div is updated (children) by show_details
                                    dcc.Loading(
                                        id="execsum-loading-form",
                                        type="circle",
                                        fullscreen=False,
                                        delay_show=150,
                                        overlay_style={"backgroundColor":"rgba(0,0,0,0)"},  # no “white-out”
                                        children=html.Div(
                                            id="execsum-form-block",   # THE new wrapper target
                                            children=[
                                                html.Div(id="execsum-form-title"),
                                                html.Div(id="execsum-form-container"),
                                            ],
                                        ),
                                    ),
                                    
                                    html.Hr(),

                                    html.Div(
                                        id="execsum-reset-wrapper",
                                        children=[
                                            
                                            dbc.Button(
                                                "RESET signatures",
                                                id="execsum-reset-es",
                                                n_clicks=0,
                                                color="danger",
                                                outline=True,
                                                size="sm",
                                                style={
                                                    "alignSelf": "flex-start",
                                                    "marginBottom": "10px",
                                                    "fontWeight": "800",
                                                },
                                            ),

                                            html.Div(
                                                id="execsum-reset-role-msg",
                                                children="",
                                                style={
                                                    "marginTop": "6px",
                                                    "marginBottom": "10px",
                                                    "fontWeight": "800",
                                                    "fontSize": "13px",
                                                    "color": "#666",
                                                    "display": "none",   # will be toggled by callback
                                                },
                                            ),
                                        ],
                                    ),

                                    dbc.Button(
                                        "📄 Generate PDF & Upload to HWDB",
                                        id="execsum-generate-upload",
                                        n_clicks=0,
                                        disabled=True,
                                        style={
                                            "width":"100%",
                                            "fontSize":"18px",
                                            "padding":"12px",
                                            "borderRadius":"10px",
                                        }
                                    ),

                                    # PDF spinner stays local
                                    dcc.Loading(
                                        id="execsum-loading-pdf",
                                        type="circle",
                                        fullscreen=False,
                                        delay_show=150,
                                        overlay_style={"backgroundColor":"rgba(0,0,0,0)"},
                                        children=html.Div(
                                            id="execsum-pdf-status",
                                            style={"marginTop":"10px", "color":"#666"},
                                        ),
                                    ),

                                    # Signature spinner stays local
                                    dcc.Loading(
                                        id="execsum-loading-signature",
                                        type="circle",
                                        fullscreen=False,
                                        delay_show=150,
                                        overlay_style={"backgroundColor":"rgba(0,0,0,0)"},
                                        children=html.Div(
                                            id="execsum-generate-status",
                                            style={"marginTop":"10px", "color":"#666"},
                                        ),
                                    ),
                                ],
                            )
                        ],
                    ),

                    # RIGHT PANEL (plots) ---- make Loading the flex item
                    html.Div(
                        id="execsum-plots-panel",
                        style={"flex":"1 1 55%", "minWidth": 0},
                        children=[
                            html.Div(
                                style={
                                    "backgroundColor":"#FAFAFA",
                                    "padding":"12px",
                                    "borderRadius":"12px",
                                    "boxShadow":"0 2px 6px rgba(0,0,0,0.10)",
                                    "maxHeight":"100vh",
                                    "overflowY":"auto",
                                },
                                children=[
                                    html.H4("Plots", style={"color":"#004C99"}),
                                    html.Hr(style={"marginTop": "10px", "marginBottom": "10px", "opacity": 0.25}),

                                    # spinner will show because this exact Div is updated by show_details
                                    dcc.Loading(
                                        id="execsum-loading-plots",
                                        type="circle",
                                        fullscreen=False,
                                        delay_show=150,
                                        overlay_style={"backgroundColor":"rgba(0,0,0,0)"},
                                        children=html.Div(id="execsum-plots-container"),
                                    ),
                                ],
                            )
                        ],
                    ),
                ]
            )


        ]
    )
