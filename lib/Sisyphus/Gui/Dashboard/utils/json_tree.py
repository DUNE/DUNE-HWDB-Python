# lib/Sisyphus/Gui/Dashboard/utils/json_tree.py

from dash import html, dcc

def _is_list_of_dicts(v):
    return (
        isinstance(v, list)
        and len(v) > 0
        and isinstance(v[0], dict)
    )

def _is_leaf(v):
    """Leaf means scalar-like (no further dict / list-of-dicts structure)."""
    if isinstance(v, dict):
        return False
    if _is_list_of_dicts(v):
        return False
    # list of scalars is treated as leaf (user gets the whole list)
    return True


def render_json_tree(data, prefix=""):
    """
    Recursively render JSON dict/list structure as a tree of checkboxes.

    - Only *leaf* nodes are selectable via checkboxes.
    - Branch nodes are labels; their children are wrapped in a container that
      gets a vertical dashed border via CSS.
    """
    nodes = []

    # ---------- dict ----------
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key

            if _is_leaf(value):
                # Leaf under a dict: checkbox here
                nodes.append(
                    html.Div(
                        dcc.Checklist(
                            id={"type": "schema-checkbox", "path": path},
                            options=[{"label": path, "value": path}],
                            value=[],
                            style={"marginLeft": "8px"},
                        ),
                        className="json-leaf",
                    )
                )
            else:
                # Branch: label only, recurse into children
                child_tree = render_json_tree(value, path)
                nodes.append(
                    html.Div(
                        [
                            html.Div(
                                path,
                                className="json-branch-label",
                            ),
                            html.Div(
                                child_tree,
                                className="json-branch-children",
                            ),
                        ],
                        className="json-branch",
                    )
                )

    # ---------- list of dicts ----------
    elif _is_list_of_dicts(data):
        # Represent array-of-objects using [*] convention
        path = f"{prefix}[*]" if prefix else "[*]"
        first = data[0]

        # list node itself is a branch (no checkbox)
        nodes.append(
            #html.Div(
                #[
                    #html.Div(
                    #    #f"{path}  (list detected at {prefix or 'root'}; "
                    #    #f"showing keys of first element)",
                    #    path,
                    #    className="json-branch-label json-list-label",
                    #    style={
                    #        "fontWeight": "bold",
                    #        "marginLeft": "10px",
                    #        "marginTop": "4px",
                    #    },
                    #),
                html.Div(
                    render_json_tree(first, path),
                    #className="json-branch-children",
                    style={"marginLeft": "20px"},
                )
                #],
                #className="json-branch",
            #)
        )

    # ---------- scalar or list-of-scalars ----------
    else:
        if prefix:
            nodes.append(
                html.Div(
                    dcc.Checklist(
                        id={"type": "schema-checkbox", "path": prefix},
                        options=[{"label": prefix, "value": prefix}],
                        value=[],
                        style={"marginLeft": "8px"},
                    ),
                    className="json-leaf",
                )
            )

    return nodes
