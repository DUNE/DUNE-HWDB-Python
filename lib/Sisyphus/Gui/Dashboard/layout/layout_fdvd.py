from dash import dcc, html
import dash_bootstrap_components as dbc


def hierarchy_chart_layout():
    """
    Experimental Hierarchy Chart tab.

    The boxes/arrows/bands are loaded from a user-editable JSON/JSON5 file by
    callbacks_fdvd.py.  The dcc.Graph is present in the initial layout so that
    callbacks may safely use fdvd-graph.relayoutData for zoom-aware scaling.
    """
    return html.Div(
        id="fdvd-tab-content-inner",
        className="fdvd-page",
        children=[
            dcc.Store(id="fdvd-layout-store"),
            dcc.Store(id="fdvd-selected-id"),
            dcc.Interval(id="fdvd-init", interval=250, n_intervals=0, max_intervals=1),

            html.Div(
                className="fdvd-toolbar",
                children=[
                    html.Div(
                        [
                            html.H3("Hierarchy Chart", className="fdvd-title"),
                            dbc.RadioItems(
                                id="hierarchy-chart-kind",
                                className="hierarchy-chart-toggle",
                                inputClassName="btn-check",
                                labelClassName="btn btn-outline-primary btn-sm",
                                labelCheckedClassName="active",
                                options=[
                                    {"label": "FD-VD", "value": "fdvd"},
                                    {"label": "FD-HD", "value": "fdhd"},
                                ],
                                value="fdvd",
                                inline=True,
                                style={"marginBottom": "0.35rem"},
                            ),
                            html.Div(
                                id="fdvd-json-path",
                                className="fdvd-json-path",
                            ),
                        ],
                    ),
                    html.Div(
                        [
                            dbc.Button(
                                "Reload JSON",
                                id="fdvd-reload-json",
                                color="primary",
                                size="sm",
                                className="me-2",
                            ),
                            dbc.Button(
                                "Clear Highlight",
                                id="fdvd-clear-selection",
                                color="secondary",
                                size="sm",
                                outline=True,
                            ),
                        ],
                    ),
                ],
            ),

            dbc.Alert(
                id="fdvd-status",
                color="info",
                is_open=False,
                dismissable=True,
                className="fdvd-status",
            ),

            html.Div(
                id="fdvd-svg-container",
                className="fdvd-svg-container",
                children=[
                    dcc.Graph(
                        id="fdvd-graph",
                        figure={},
                        config={
                            "displaylogo": False,
                            "scrollZoom": True,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        },
                        style={"width": "100%", "height": "78vh"},
                        className="fdvd-graph",
                    )
                ],
            ),

            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(id="fdvd-modal-title")),
                    dbc.ModalBody(id="fdvd-modal-body"),
                    dbc.ModalFooter(
                        dbc.Button("Close", id="fdvd-modal-close", className="ms-auto", n_clicks=0)
                    ),
                ],
                id="fdvd-detail-modal",
                is_open=False,
                size="lg",
                scrollable=True,
            ),
        ],
    )


# Backward-compatible alias.
# layout_main.py may still import fdvd_layout while the visible tab is now
# "Hierarchy Chart".
def fdvd_layout():
    return hierarchy_chart_layout()
