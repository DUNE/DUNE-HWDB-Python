import pandas as pd, ast
from dash import dcc, html, Input, Output, State, ctx
import dash
import base64, pickle
import json



from Sisyphus.Configuration import config
from Sisyphus.Gui.Dashboard.utils.colorlog_handler import attach_color_console_handler

logger = config.getLogger(__name__)


def resolve_df_from_store(store):
    if isinstance(store, dict) and "path" in store:
        with open(store["path"], "rb") as f:
            return pickle.load(f)
    return pd.DataFrame(store)

# Add/remove condition input rows
def register_callbacks(app):
    @app.callback(
        Output("condition-container","children", allow_duplicate=True),
        Input("data-store", "data"),
        Input("add-condition","n_clicks"),
        Input({"type":"remove-chip","index":dash.ALL},"n_clicks"),
        State("condition-container","children"),
        State("logic-operator", "value"),
        prevent_initial_call=True
    )
    def update_conditions(data, add_clicks, remove_clicks, children, logic_operator):
        
        #df = pd.DataFrame(data)
        df = resolve_df_from_store(data)

        
        triggered = ctx.triggered_id
        children = list(children) if children else []

        logger.info("Updating conditions...")
        
        # ---- Add condition ----
        if triggered == "add-condition":
            idx = len(children)
            children.append(
                
                html.Div([
                    
                    # Print the logic
                    #html.Label(logix_text,
                    #    style={
                    #        "marginLeft": "10px",
                    #        "font-size": "16px",
                    #        #"fontWeight": "bold",
                    #        "font-family": "Arial, sans-serif",
                    #        "marginRight": rightspace,
                    #        "whiteSpace": "nowrap",
                    #        "alignSelf": "center",
                    #}),
            
                    # Column selection
                    dcc.Dropdown(
                        id={"type":"field","index":idx},
                        options=[{"label": c, "value": c} for c in df.columns],
                        placeholder="Column",
                        # a longer width 
                        style={"width":"600px","height": "36px","fontSize": "14px","font-family": "Arial, sans-serif",
                                "border": "0.1px solid #ccc", "borderRadius": "5px",   
                                "display":"inline-block","marginRight":"5px", "marginLeft":"10px"}
                    ),
                    # Operator + Threshold
                    dcc.Dropdown(
                        id={"type":"operator","index":idx},
                        options=[{"label":op,"value":op} for op in [">","<",">=","<=","==","!=","contains"]],
                        placeholder="Op",
                        style={"width": "100px","height": "36px","fontSize": "14px", "font-family": "Arial, sans-serif",
                                "border": "0.1px solid #ccc", "borderRadius": "5px",   
                                "display":"inline-block","marginRight":"5px"}
                    ), 
                    dcc.Input(
                        id={"type":"threshold","index":idx},
                        type="text",
                        placeholder="Enter value",
                        debounce=True,
                        style={"width": "100px","height": "36px","fontSize": "14px", "font-family": "Arial, sans-serif",
                                "border": "0.1px solid #ccc", "borderRadius": "5px",   
                                "textAlign": "center","marginRight":"5px"}
                    ),

                    # Color selection
                    dcc.Dropdown(
                        id={"type": "color", "index": idx},
                        options=[
                            {"label": c.capitalize(), "value": c} for c in [
                                "red", "blue", "green", "orange", "purple", "pink",
                                "brown", "cyan", "magenta", "yellow", "black", "gray"
                            ]
                        ],
                        placeholder="Select color",
                        style={"width": "120px","height": "36px","fontSize": "14px", "font-family": "Arial, sans-serif",
                                "border": "0.1px solid #ccc", "borderRadius": "5px","marginRight":"30px"}
                    ),

                    # Add/Remove Buttons
                    html.Button(
                        "Apply",
                        id={"type":"apply-condition","index":idx},
                        n_clicks=0,
                        style={"background":"#74B9FF","color":"white","border": "none",
                                "width": "120px","height": "36px","fontSize": "14px", "font-family": "Arial, sans-serif",
                                "padding": "5px 12px","borderRadius":"6px","cursor":"pointer",
                                "marginRight":"10px"}
                    ),
                    html.Button(
                        "Remove",
                        id={"type": "remove-chip", "index": idx},
                        n_clicks=0,
                        style={"backgroundColor": "#c0392b","color": "white","border": "none",
                                "width": "120px","height": "36px","fontSize": "14px", "font-family": "Arial, sans-serif",
                                "padding": "5px 12px","borderRadius":"6px","cursor":"pointer"}
                    )
                    
                ],
                    id={"type":"condition-block","index":idx},
                    style={
                        "display": "flex",
                        "flexDirection": "row",
                        "alignItems": "center",
                        "justifyContent": "flex-start",
                        "gap": "10px",  # optional modern spacing
                        "marginBottom": "5px",
                    }
                )
            )

        # ---- Delete condition ----
        elif isinstance(triggered, dict) and triggered.get("type")=="remove-chip":
            #idx_to_remove = triggered["index"]
            #children = [c for c in children if c["props"]["id"]["index"] != idx_to_remove]
            
            # Find out which button triggered
            triggered_idx = triggered["index"]

            # Check n_clicks for that button
            remove_clicks = remove_clicks or []
            if isinstance(remove_clicks, list) and triggered_idx < len(remove_clicks):
                n = remove_clicks[triggered_idx]
                if not n or n == 0:
                    print(f"[Safety] Ignoring phantom remove-chip trigger at index {triggered_idx}")
                    raise dash.exceptions.PreventUpdate

            # Real removal only when n_clicks > 0
            children = [
                c for c in children
                if c["props"]["id"]["index"] != triggered_idx
            ]

        return children


    # ----------------------------------------------
    # Helper callback: open hidden Upload selector
    # ----------------------------------------------
    @app.callback(
        Output("upload-conditions", "contents", allow_duplicate=True),
        Input("load-conditions", "n_clicks"),
        prevent_initial_call=True
    )
    def open_file_selector(n):
        # Dash will automatically open file selector UI
        # when "Load conditions" is clicked
        return dash.no_update

    
    # ----------------------------------------------
    # Load conditions from uploaded JSON
    # ----------------------------------------------
    @app.callback(
        Output("condition-container", "children", allow_duplicate=True),
        Input("upload-conditions", "contents"),
        State("condition-container", "children"),
        State("typeid-input", "value"),
        State("testtype-input", "value"),
        prevent_initial_call=True
    )
    def load_conditions_from_json(upload_contents, existing_children, current_typeid, current_testtype):
        if not upload_contents:
            raise dash.exceptions.PreventUpdate

        content_type, content_string = upload_contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            cond_data = json.loads(decoded)
        except Exception as e:
            print(f"[Load Conditions] Failed to parse JSON: {e}")
            raise dash.exceptions.PreventUpdate


        # --- Type/Test consistency check ---
        file_typeid = cond_data.get("typeid", "")
        file_testtype = cond_data.get("testtype", "")
        
        # Normalize empty strings
        current_typeid = current_typeid or ""
        current_testtype = current_testtype or ""

        # Compare both
        if file_typeid != current_typeid:
            print(f"[Load Conditions] ❌ Mismatch: file typeid={file_typeid}, current={current_typeid}")
            raise dash.exceptions.PreventUpdate

        # Only check testtype if file has one defined
        if file_testtype and (file_testtype != current_testtype):
            print(f"[Load Conditions] ❌ Mismatch: file testtype={file_testtype}, current={current_testtype}")
            raise dash.exceptions.PreventUpdate

        
        # Build new children list based on loaded fields/operators/thresholds
        children = []
        fields = cond_data.get("fields", [])
        ops = cond_data.get("operators", [])
        thresh = cond_data.get("thresholds", [])
        logic_operator = cond_data.get("logic_operator", "and")

        df_placeholder = pd.DataFrame()  # safe default if needed

        for idx, (f, o, t) in enumerate(zip(fields, ops, thresh)):
            logic_label = "AND" if logic_operator == "and" else "OR"

            children.append(
                html.Div([
                    html.Label(
                        logic_label,
                        style={
                            "marginLeft": "10px",
                            "font-size": "16px",
                            "font-family": "Arial, sans-serif",
                            "marginRight": "10px",
                            "whiteSpace": "nowrap",
                        }
                    ),
                    dcc.Dropdown(
                        id={"type": "field", "index": idx},
                        options=[{"label": f, "value": f} for f in fields],
                        value=f,
                        placeholder="Column",
                        style={"width": "600px", "height": "36px", "marginRight": "5px"}
                    ),
                    dcc.Dropdown(
                        id={"type": "operator", "index": idx},
                        options=[{"label": op, "value": op} for op in [">","<",">=","<=","==","!=","contains"]],
                        value=o,
                        placeholder="Op",
                        style={"width": "100px", "height": "36px", "marginRight": "5px"}
                    ),
                    dcc.Input(
                        id={"type": "threshold", "index": idx},
                        type="text",
                        value=str(t),
                        style={"width": "100px", "height": "36px", "textAlign": "center", "marginRight": "5px"}
                    ),
                    dcc.Dropdown(
                        id={"type": "color", "index": idx},
                        options=[{"label": c.capitalize(), "value": c} for c in [
                            "red","blue","green","orange","purple","pink","brown","cyan","magenta","yellow","black","gray"]],
                        placeholder="Select color",
                        style={"width": "120px", "height": "36px", "marginRight": "30px"}
                    ),
                    html.Button(
                        "Apply",
                        id={"type": "apply-condition", "index": idx},
                        n_clicks=1,
                        style={"background": "#74B9FF", "color": "white", "border": "none",
                            "width": "120px", "height": "36px", "fontSize": "14px",
                            "borderRadius": "6px", "cursor": "pointer", "marginRight": "10px"}
                    ),
                    html.Button(
                        "Remove",
                        id={"type": "remove-chip", "index": idx},
                        n_clicks=0,
                        style={"backgroundColor": "#c0392b", "color": "white", "border": "none",
                            "width": "120px", "height": "36px", "fontSize": "14px",
                            "borderRadius": "6px", "cursor": "pointer"}
                    )
                ],
                id={"type": "condition-block", "index": idx},
                style={
                    "display": "flex",
                    "flexDirection": "row",
                    "alignItems": "center",
                    "justifyContent": "flex-start",
                    "marginBottom": "5px"
                })
            )

        print(f"[Load Conditions] Loaded {len(children)} condition(s).")
        return children
