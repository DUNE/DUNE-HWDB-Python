from dash import html, dcc
from dash import dash_table
import dash_bootstrap_components as dbc

# Reusable table defaults (consistent with your style)
_TABLE_STYLE = {
    "height": "70vh",
    "overflowY": "auto",
    "borderRadius": "12px",
}
_CELL_STYLE = {
    "whiteSpace": "normal",
    "height": "auto",
    "fontFamily": "Arial, sans-serif",
    "fontSize": "16px",
    "textAlign": "left",
    "padding": "8px 12px",
}
_HEADER_STYLE = {
    "fontWeight": "bold",
    "fontSize": "16px",
    "textAlign": "center",
    "backgroundColor": "#f5f5f5",
    "borderBottom": "2px solid #ccc",
}

def _page_header(title, right_children=None, left_children=None):
    return html.Div(
        className="tg-page-header",
        children=[
            html.Div(left_children or []),
            html.H3(title, className="tg-page-title"),
            html.Div(right_children or [], className="tg-header-right"),
        ],
    )

def typegetter_layout():
    """
    Returns the full Type Getter tab layout (4 sliding pages).
    """
    return html.Div(
        id="typegetter-root",
        style={
            "padding": "20px",
            "backgroundColor": "#ffffff",
            "color": "#111",
        },
        children=[
            
            # Navigation state + cache
            dcc.Store(id="tg-sync-projects-trigger", storage_type="memory"),
            dcc.Store(id="tg-sync-systems-trigger", storage_type="memory"),
            dcc.Store(id="tg-sync-subsystems-trigger", storage_type="memory"),
            dcc.Store(id="tg-sync-types-trigger", storage_type="memory"),
            dcc.Store(id="tg-current-level", data="projects", storage_type="session"),
            dcc.Store(id="tg-cache", storage_type="local"),
            dcc.Store(
                id="tg-selected",
                data={"project": None, "system": None, "subsystem": None, "type": None},
                storage_type="local",   # persist selection
            ),
            dcc.Store(id="tg-click", data=0),
            dcc.Store(id="tg-copy-buffer", storage_type="memory"),
            # --- Per-table persistent data stores ---
            dcc.Store(id="tg-systems-store", storage_type="local"),
            dcc.Store(id="tg-subsystems-store", storage_type="local"),
            dcc.Store(id="tg-types-store", storage_type="local"),
            # Bread-crumb-ish text
            html.Div(id="tg-crumbs", className="tg-crumbs"),
            # Clipboard for TypeID copy
            dcc.Clipboard(id="tg-clipboard", content="", style={"display": "none"}),
            # Sliding container
            html.Div(
                id="tg-pages",
                className="tg-container",
                style={
                    "transform": "translateX(0%)",   # start on projects page
                    "display": "flex",
                    "width": "400%",
                    "overflow": "hidden",           # hides other pages
                    "transition": "transform 0.35s ease-in-out",
                    "scrollBehavior": "none",       # prevent smooth scroll attempts
                    "overscrollBehaviorX": "contain",  # block horizontal drag
                    "overflowX": "clip",            # newer CSS3 property; hides horizontal scrollbars
                },
                children=[
                    # --- Projects Page ---
                    html.Div(
                        id="tg-page-projects",
                        className="tg-page",
                        children=[
                            _page_header(
                                "Projects",
                                right_children=[
                                    dbc.Button(
                                        "Sync to the HWDB",
                                        id="tg-sync-projects",
                                        n_clicks=0,
                                        color="primary",
                                        className="tg-sync-btn",
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
                                ]
                            ),
                            dash_table.DataTable(
                                id="tg-table-projects",
                                columns=[
                                    {"name": "Project ID", "id": "id"},
                                    {"name": "Project Name", "id": "name"},
                                ],
                                data=[],
                                #row_selectable=False,
                                #active_cell=None,
                                fixed_rows={'headers': True},
                                style_table=_TABLE_STYLE,
                                style_cell=_CELL_STYLE,
                                style_header=_HEADER_STYLE,
                                style_data_conditional=[
                                    {
                                        "if": {"state": "active"},
                                         "backgroundColor": "rgba(0, 123, 255, 0.15)",
                                         "border": "1px solid rgba(0, 123, 255, 0.25)",
                                    },
                                    {
                                        "if": {"state": "selected"},
                                        "backgroundColor": "rgba(0, 123, 255, 0.15)",
                                         "border": "1px solid rgba(0, 123, 255, 0.25)",
                                    },
                                ],
                            ),
                        ],
                    ),

                    # --- Systems Page ---
                    html.Div(
                        id="tg-page-systems",
                        className="tg-page",
                        children=[
                            _page_header(
                                "Systems",
                                left_children=[dbc.Button("← Back", id="tg-back-systems", color="secondary")],
                                right_children=[
                                    dbc.Button(
                                        "Sync to HWDB",
                                        id="tg-sync-systems",
                                        n_clicks=0,
                                        color="primary",
                                        className="tg-sync-btn",
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
                                ]
                            ),
                            dash_table.DataTable(
                                id="tg-table-systems",
                                columns=[
                                    {"name": "System ID", "id": "id"},
                                    {"name": "System Name", "id": "name"},
                                ],
                                data=[],
                                fixed_rows={'headers': True},
                                row_selectable=False,
                                active_cell=None,
                                style_table=_TABLE_STYLE,
                                style_cell=_CELL_STYLE,
                                style_header=_HEADER_STYLE,
                                style_data_conditional=[
                                    {
                                        "if": {"state": "active"},
                                         "backgroundColor": "rgba(0, 123, 255, 0.15)",
                                         "border": "1px solid rgba(0, 123, 255, 0.25)",
                                    },
                                    {
                                        "if": {"state": "selected"},
                                        "backgroundColor": "rgba(0, 123, 255, 0.15)",
                                         "border": "1px solid rgba(0, 123, 255, 0.25)",
                                    },
                                ],
                            ),
                        ],
                    ),

                    # --- Subsystems Page ---
                    html.Div(
                        id="tg-page-subsystems",
                        className="tg-page",
                        children=[
                            _page_header(
                                "Subsystems",
                                left_children=[dbc.Button("← Back", id="tg-back-subsystems", color="secondary")],
                                right_children=[
                                    dbc.Button(
                                        "Sync to HWDB",
                                        id="tg-sync-subsystems",
                                        n_clicks=0,
                                        color="primary",
                                        className="tg-sync-btn",
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
                            ),
                            dash_table.DataTable(
                                id="tg-table-subsystems",
                                columns=[
                                    {"name": "Subsystem ID", "id": "id"},
                                    {"name": "Subsystem Name", "id": "name"},
                                ],
                                data=[],
                                fixed_rows={'headers': True},
                                row_selectable=False,
                                style_table=_TABLE_STYLE,
                                style_cell=_CELL_STYLE,
                                style_header=_HEADER_STYLE,
                                style_data_conditional=[
                                    {
                                        "if": {"state": "active"},
                                         "backgroundColor": "rgba(0, 123, 255, 0.15)",
                                         "border": "1px solid rgba(0, 123, 255, 0.25)",
                                    },
                                    {
                                        "if": {"state": "selected"},
                                        "backgroundColor": "rgba(0, 123, 255, 0.15)",
                                         "border": "1px solid rgba(0, 123, 255, 0.25)",
                                    },
                                ],
                            ),
                        ],
                    ),

                    # --- Types Page ---
                    html.Div(
                        id="tg-page-types",
                        className="tg-page",
                        children=[
                            _page_header(
                                "Types",
                                left_children=[dbc.Button("← Back", id="tg-back-types", color="secondary")],
                                right_children=[
                                    dbc.Button(
                                        "Sync to HWDB",
                                        id="tg-sync-types",
                                        n_clicks=0,
                                        color="primary",
                                        className="tg-sync-btn",
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
                            ),
                            html.Div(
                                id="tg-typeid-status",
                                className="tg-typeid-status",
                                children=html.Span("", id="tg-typeid-text")
                            ),
                            dash_table.DataTable(
                                id="tg-table-types",
                                columns=[
                                    {"name": "Part Type ID", "id": "id"},
                                    {"name": "Type Name (full name)", "id": "name"},
                                ],
                                data=[],
                                fixed_rows={'headers': True},
                                row_selectable=False,
                                style_table=_TABLE_STYLE,
                                style_cell=_CELL_STYLE,
                                style_header=_HEADER_STYLE,
                                style_data_conditional=[
                                    {
                                        "if": {"column_id": "id"},
                                        "textAlign": "center",
                                        #"fontWeight": "bold",
                                        #"color": "#003366",
                                    },
                                    {
                                        "if": {"state": "active"},
                                         "backgroundColor": "rgba(0, 123, 255, 0.15)",
                                         "border": "1px solid rgba(0, 123, 255, 0.25)",
                                    },
                                    {
                                        "if": {"state": "selected"},
                                        "backgroundColor": "rgba(0, 123, 255, 0.15)",
                                         "border": "1px solid rgba(0, 123, 255, 0.25)",
                                    },
                                ],
                            ),
                            #html.Div(id="tg-typeid-status", className="tg-typeid-status"),
                        ],
                    ),
                ],
            ),
        ],
    )
