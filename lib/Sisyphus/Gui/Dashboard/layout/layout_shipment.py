from dash import dcc, html, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc

def shipment_layout():
    return html.Div(
        id="shipment-tab-content",
        style={"padding": "15px"},
        children=[

            dcc.Store(id="fetch-shipments-trigger", storage_type="memory"),
            dcc.Store(id="shipments-selected-pid",data={"pid": None},storage_type="local"),   # ✅ persist selection
            dcc.Store(id="fetch-shipments-store", storage_type="memory"),  # persist synced shipment data until refresh
            dcc.Store(id="shippinglabel-id-store"),
            dcc.Store(id="bol-id-store"),
            dcc.Store(id="shipment-memory-store", storage_type="local"),
            # for displaying completion %
            dcc.Store(id="shipment-job-id", storage_type="memory"),
            dcc.Interval(id="shipment-interval", interval=1000, disabled=True),
            dcc.Store(id="shipment-total", storage_type="memory"),
            dcc.Store(id="shipment-processed", storage_type="memory"),
            dcc.Store(id="shipment-items-cache", storage_type="memory"),
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
                    html.Div(
                        [
                            html.Span("Certified: ", style={"marginLeft": "10px","fontSize": "17px", "fontWeight": "bold", "color": "black"}),
                            dcc.Link(
                                "Consortium Certified QA/QC flag",
                                href="https://dune.github.io/computing-HWDB/shippinghandoff/index.html#the-two-key-flags",
                                target="_blank",
                                style={"fontSize": "17px","marginRight": "20px"},
                            ),

                        html.Span("Uploaded: ", style={"fontSize": "17px","fontWeight": "bold", "color": "black"}),
                        dcc.Link(
                            "All QA/QC Test and Documentation Uploaded flag",
                            href="https://dune.github.io/computing-HWDB/shippinghandoff/index.html#the-two-key-flags",
                            target="_blank",
                            style={"fontSize": "17px","marginRight": "20px"},
                        ),
                        ],
                        style={
                            "fontSize": "14px",
                            "color": "gray",
                            "marginBottom": "8px",
                            "marginTop": "-6px",  # pulls description closer to the title
                            "fontFamily": "Arial, sans-serif",
                        },
                    ),
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
