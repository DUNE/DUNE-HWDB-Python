import json as _strict_json
import os
import math
from pathlib import Path
from html import escape as _html_escape
from urllib.parse import quote_plus

try:
    import json5 as _json5
    _HAS_JSON5 = True
except Exception:  # keep the Dashboard usable even before json5 is installed
    _json5 = None
    _HAS_JSON5 = False

from dash import Input, Output, State, callback_context, dcc, html, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from Sisyphus.Configuration import config
try:
    from Sisyphus.Gui.Dashboard.utils.config import get_hierarchy_json_path
except Exception:
    get_hierarchy_json_path = None

from Sisyphus.Gui.Dashboard.utils.config import get_fdvd_json_path

logger = config.getLogger(__name__)


def _normalize_chart_kind(value: str | None) -> str:
    """
    Normalize the user-facing chart selector.

    Supported values:
      fdvd / FD-VD / vd  -> fdvd_layout.json
      fdhd / FD-HD / hd  -> fdhd_layout.json
    """
    s = str(value or "fdvd").strip().lower().replace("_", "-")
    if s in ("fd-hd", "fdhd", "hd"):
        return "fdhd"
    return "fdvd"


def _chart_label(chart_kind: str | None) -> str:
    return "FD-HD" if _normalize_chart_kind(chart_kind) == "fdhd" else "FD-VD"



DEFAULT_FDVD_LAYOUT = {'version': 3,
 'title': 'FD-VD demo layout',
 'canvas': {'width': 1600,
            'height': 900,
            'background': 'white',
            'scale_text_with_zoom': True,
            'scale_markers_with_zoom': True,
            'arrowhead_scale_with_zoom': False,
            'stroke_scale_with_zoom': False,
            'default_coords': 'relative'},
 'palette': {'white': '#ffffff',
             'black': '#111111',
             'text_dark': '#222222',
             'dune_blue': '#174cff',
             'dune_green': '#107020',
             'signal_red': '#ff4b3e',
             'signal_orange': '#ff9f1c',
             'highlight_yellow': '#ffd000',
             'band_pink': '#f6cccc',
             'band_blue': '#dce9ff',
             'box_gray': '#e8e8e8'},
 'defaults': {'box': {'fill': 'dune_blue',
                      'text_color': 'white',
                      'font': {'size': 13, 'bold': True, 'family': 'Arial'},
                      'border_color': '#333333',
                      'border_width': 1,
                      'border_style': 'solid',
                      'label_rel': [0.5, 0.5],
                      'label_offset': [0, 0]},
              'band': {'fill': 'band_pink',
                       'label_color': 'text_dark',
                       'font': {'size': 14, 'bold': True, 'family': 'Arial'},
                       'border_style': 'none',
                       'border_width': 0,
                       'opacity': 0.85,
                       'label_rel': [0.0, 0.5],
                       'label_offset': [12, 0]},
              'arrow': {'stroke': 'signal_red',
                        'stroke_width': 1,
                        'line_style': 'solid',
                        'arrow_start': False,
                        'arrow_end': True,
                        'font': {'size': 13,
                                 'bold': False,
                                 'family': 'Arial',
                                 'color': 'signal_red'},
                        'dot_spacing': 10,
                        'dot_size': 3,
                        'dash_length': 18,
                        'dash_gap': 14}},
 'items': [{'id': 'band_mezzanine',
            'type': 'band',
            'label': 'Mezzanine racks',
            'x': 0.0,
            'y': 0.061,
            'w': 1.0,
            'h': 0.1,
            'label_rel': [0.03, 0.5],
            'details': {'title': 'Mezzanine racks',
                        'bullets': ['Example horizontal band using relative coordinates.'],
                        'links': []}},
           {'id': 'band_roof',
            'type': 'band',
            'label': 'Cryostat roof',
            'x': 0.0,
            'y': 0.344,
            'w': 1.0,
            'h': 0.05,
            'label_rel': [0.1, -0.15],
            'details': {'title': 'Cryostat roof',
                        'bullets': ['Example horizontal band using relative coordinates.'],
                        'links': []}},
           {'id': 'pds_lv_ps',
            'type': 'box',
            'label': 'PDS LV PS',
            'x': 0.48125,
            'y': 0.0889,
            'w': 0.075,
            'h': 0.0356,
            'fill': 'dune_blue',
            'details': {'title': 'PDS LV PS',
                        'bullets': ['Example standard component type.',
                                    'This is a JSON5-driven box. Edit this file and press Reload '
                                    'JSON.',
                                    'This item uses coords: relative and palette color aliases.'],
                        'links': [{'label': 'Example documentation link',
                                   'url': 'https://dune-daq-sw.readthedocs.io/'}]}},
           {'id': 'pds_rack',
            'type': 'box',
            'label': 'PDS rack (40)',
            'x': 0.5,
            'y': 0.228,
            'w': 0.0844,
            'h': 0.0356,
            'fill': 'dune_blue',
            'details': {'title': 'PDS rack (40)',
                        'bullets': ['Example rack box.', 'Clicking the box opens this modal.'],
                        'links': []}},
           {'id': 'crp_cable_tray',
            'type': 'box',
            'label': 'CRP Cable Tray',
            'x': 0.80625,
            'y': 0.561,
            'w': 0.0906,
            'h': 0.0356,
            'fill': 'dune_green',
            'details': {'title': 'CRP Cable Tray',
                        'subtitle': 'Example enhanced modal template with system/subsystem/type '
                                    'information.',
                        'system_name': 'FD-VD detector',
                        'system_id': '000',
                        'subsystem_name': 'CRP / cable handling',
                        'subsystem_id': '000',
                        'bullets': ['Example green box.',
                                    'Details can contain bullets, URLs, and structured component '
                                    'type information.'],
                        'types': [{'name': 'CRP Cable Tray',
                                   'id': 'D00000000001',
                                   'description': 'Example component type description. Replace '
                                                  'this with the real HWDB component type '
                                                  'description.',
                                   'links': [{'label': 'DUNE',
                                              'url': 'https://www.dunescience.org/'}],
                                   'parents': [{'name': 'Example parent component type',
                                                'id': 'D00000000000'}],
                                   'children': [{'name': 'Example child component type A',
                                                 'id': 'D00000000002'},
                                                {'name': 'Example child component type B',
                                                 'id': 'D00000000003'}]}],
                        'links': [{'label': 'DUNE', 'url': 'https://www.dunescience.org/'}]}},
           {'id': 'arrow_pds_power',
            'type': 'arrow',
            'from_id': 'pds_lv_ps',
            'from_anchor': 'bottom',
            'to_id': 'pds_rack',
            'to_anchor': 'top',
            'label': 'power',
            'label_position': 'right',
            'details': {'title': 'PDS power connection',
                        'bullets': ['Example solid arrow using relative coordinates.'],
                        'links': []}},
           {'id': 'arrow_crp_signal',
            'type': 'arrow',
            'from': [0.85, 0.394],
            'to_id': 'crp_cable_tray',
            'to_anchor': 'top',
            'line_style': 'dotted',
            'label': 'signal path',
            'label_position': 'right',
            'label_angle': -90,
            'details': {'title': 'CRP signal path',
                        'bullets': ['Example dashed arrow using relative coordinates.'],
                        'links': []}}]}


DEFAULT_FDVD_LAYOUT_JSON5 = r'''
{
  // FD-VD demo layout.
  // This file is parsed with JSON5, so comments, trailing commas,
  // and unquoted object keys are allowed when the python json5 package is installed.
  version: 3,
  title: "FD-VD demo layout",

  canvas: {
    // width/height define the drawing coordinate system.
    // Items with coords: "relative" are scaled against this size.
    width: 1600,
    height: 900,
    background: "white",

    // When true, screen-pixel-sized labels and marker dots grow/shrink
    // as you zoom, so they stay visually proportional to boxes and bands.
    scale_text_with_zoom: true,
    scale_markers_with_zoom: true,

    // Usually false because triangle arrowheads are drawn in data coordinates,
    // so they already scale naturally with the canvas when zoomed.
    arrowhead_scale_with_zoom: false,
    stroke_scale_with_zoom: false,

    // Optional file-wide coordinate mode:
    default_coords: "relative",
    // If omitted, items default to absolute coordinates unless they set coords: "relative".
  },

  palette: {
    // Color aliases used by fill, stroke, text_color, label_color, and canvas.background.
    white: "#ffffff",
    black: "#111111",
    text_dark: "#222222",
    dune_blue: "#174cff",
    dune_green: "#107020",
    signal_red: "#ff4b3e",
    signal_orange: "#ff9f1c",
    highlight_yellow: "#ffd000",
    band_pink: "#f6cccc",
    band_blue: "#dce9ff",
    box_gray: "#e8e8e8",
  },

  defaults: {
    // Optional defaults by item type.
    // Each item below may override any of these fields.
    // Nested font dictionaries are merged, so font: {size: 18}
    // overrides only the size while keeping bold/family/color defaults.
    box: {
      fill: "dune_blue",
      text_color: "white",
      font: {size: 13, bold: true, family: "Arial"},
      border_color: "#333333",
      border_width: 1,
      border_style: "solid",
      label_rel: [0.5, 0.5],
      label_offset: [0, 0],
    },

    band: {
      fill: "band_pink",
      label_color: "text_dark",
      font: {size: 14, bold: true, family: "Arial"},
      border_style: "none",
      border_width: 0,
      opacity: 0.85,
      label_rel: [0.0, 0.5],
      label_offset: [12, 0],
    },

    arrow: {
      stroke: "signal_red",
      stroke_width: 1,
      line_style: "solid",
      arrow_start: false,
      arrow_end: true,
      font: {size: 13, bold: false, family: "Arial", color: "signal_red"},
      dot_spacing: 10,
      dot_size: 3,
      dash_length: 18,
      dash_gap: 14,
    },
  },

  items: [

    { // Example horizontal band using relative coordinates.
      id: "band_mezzanine",
      type: "band",
      label: "Mezzanine racks",
      x: 0.0,
      y: 0.061,
      w: 1.0,
      h: 0.10,
      label_rel: [0.03, 0.5],
      details: {
        title: "Mezzanine racks",
        bullets: [
          "Example horizontal band using relative coordinates.",
        ],
        links: [],
      },
    },

    {
      id: "band_roof",
      type: "band",
      label: "Cryostat roof",
      x: 0.0,
      y: 0.344,
      w: 1.0,
      h: 0.05,
      label_rel: [0.1, -0.15],
      details: {
        title: "Cryostat roof",
        bullets: ["Example horizontal band using relative coordinates."],
        links: [],
      },
    },

    { // Example clickable box using relative coordinates and palette color aliases.
      id: "pds_lv_ps",
      type: "box",
      label: "PDS LV PS",
      x: 0.48125,
      y: 0.0889,
      w: 0.075,
      h: 0.0356,
      fill: "dune_blue",
      details: {
        title: "PDS LV PS",
        bullets: [
          "Example standard component type.",
          "This is a JSON5-driven box. Edit this file and press Reload JSON.",
          "This item uses coords: relative and palette color aliases.",
        ],
        links: [
          {label: "Example documentation link", url: "https://dune-daq-sw.readthedocs.io/"},
        ],
      },
    },

    {
      id: "pds_rack",
      type: "box",
      label: "PDS rack (40)",
      x: 0.50,
      y: 0.228,
      w: 0.0844,
      h: 0.0356,
      fill: "dune_blue",
      details: {
        title: "PDS rack (40)",
        bullets: [
          "Example rack box.",
          "Clicking the box opens this modal.",
        ],
        links: [],
      },
    },

    {
      id: "crp_cable_tray",
      type: "box",
      label: "CRP Cable Tray",
      x: 0.80625,
      y: 0.561,
      w: 0.0906,
      h: 0.0356,
      fill: "dune_green",
      details: {
        title: "CRP Cable Tray",
        subtitle: "Example enhanced modal template with system/subsystem/type information.",

        // These can also be written as:
        // system: {name: "FD-VD", id: "D"},
        // subsystem: {name: "CRP", id: "123"},
        system_name: "FD-VD detector",
        system_id: "000",
        subsystem_name: "CRP / cable handling",
        subsystem_id: "000",

        bullets: [
          "Example green box.",
          "Details can contain bullets, URLs, and structured component type information.",
        ],

        // If url is omitted for a type/parent/child, the Dashboard automatically
        // creates an HWDB browser link using the active profile:
        //   development: https://dbweb2.fnal.gov:8443/cdbdev/view/component_types?pid=&sid=&ssid=&part=<TYPE_ID>&name=&cate=&comm=&crea=&subs=
        //   production:  https://dbweb2.fnal.gov:8443/cdb/view/component_types?pid=&sid=&ssid=&part=<TYPE_ID>&name=&cate=&comm=&crea=&subs=
        types: [
          {
            name: "CRP Cable Tray",
            id: "D00000000001",
            description: "Example component type description. Replace this with the real HWDB component type description.",
            links: [
              {label: "DUNE", url: "https://www.dunescience.org/"},
            ],
            parents: [
              {name: "Example parent component type", id: "D00000000000"},
            ],
            children: [
              {name: "Example child component type A", id: "D00000000002"},
              {name: "Example child component type B", id: "D00000000003"},
            ],
          },
        ],

        links: [
          {label: "DUNE", url: "https://www.dunescience.org/"},
        ],
      },
    },

    { // Example solid arrow using names
      id: "arrow_pds_power",
      type: "arrow",
      from_id: "pds_lv_ps",
      from_anchor: "bottom",
      to_id: "pds_rack",
      to_anchor: "top",
      label: "power",
      label_position: "right",
      details: {
        title: "PDS power connection",
        bullets: ["Example solid arrow using relative coordinates."],
        links: [],
      },
    },

    { // Example dashed arrow using relative coordinates and name
      id: "arrow_crp_signal",
      type: "arrow",
      from: [0.85, 0.394],
      to_id: "crp_cable_tray",
      to_anchor: "top",
      line_style: "dotted",
      label: "signal path",
      label_position: "right",
      label_angle: -90,
      details: {
        title: "CRP signal path",
        bullets: ["Example dashed arrow using relative coordinates."],
        links: [],
      },
    },
  ],
}
'''


def _json5_sibling(path: str | os.PathLike) -> Path:
    """Return a .json5 path next to the configured fdvd_layout.json path."""
    p = Path(path).expanduser()
    if p.suffix.lower() == ".json5":
        return p
    if p.suffix.lower() == ".json":
        return p.with_suffix(".json5")
    return Path(str(p) + ".json5")


def _json_sibling(path: str | os.PathLike) -> Path:
    """Return a .json path next to a possible fdvd_layout.json5 path."""
    p = Path(path).expanduser()
    if p.suffix.lower() == ".json":
        return p
    if p.suffix.lower() == ".json5":
        return p.with_suffix(".json")
    return Path(str(p) + ".json")


def _candidate_layout_paths(chart_kind: str | None = None) -> list[Path]:
    """
    Return layout-file candidates for the selected hierarchy chart.

    Preferred user-facing files are:

      fdvd_layout.json    for the FD-VD chart
      fdhd_layout.json    for the FD-HD chart

    The files may still use JSON5 syntax when the python json5 package is
    installed.  We also support .json5 siblings for backward compatibility.
    """
    kind = _normalize_chart_kind(chart_kind)

    if get_hierarchy_json_path is not None:
        configured = Path(get_hierarchy_json_path(kind)).expanduser()
    else:
        # Backward-compatible fallback for older config.py files.
        configured = Path(get_fdvd_json_path()).expanduser()
        if kind == "fdhd":
            configured = configured.with_name("fdhd_layout.json")

    json_path = _json_sibling(configured)
    json5_path = _json5_sibling(configured)

    candidates = []
    for p in (json_path, json5_path):
        if p not in candidates:
            candidates.append(p)
    return candidates


def _selected_layout_path_for_read(chart_kind: str | None = None) -> Path:
    candidates = _candidate_layout_paths(chart_kind)
    for p in candidates:
        if p.exists():
            return p

    # No user file exists yet. Create <chart>_layout.json by default.
    return candidates[0]


def _parser_for_path(path: Path):
    """
    Use json5 when available. If it is unavailable, fall back to strict json.
    A JSON5 file with comments will then raise a clear load error.
    """
    if _HAS_JSON5:
        return _json5
    return _strict_json



def _deep_merge_dicts(base: dict, incoming: dict) -> dict:
    """
    Recursively merge incoming into base and return base.

    Used for palette/defaults blocks from included FD-VD layout fragments.
    Lists are not merged here; item lists are appended separately.
    """
    if not isinstance(base, dict):
        base = {}
    if not isinstance(incoming, dict):
        return base

    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge_dicts(base[key], value)
        else:
            base[key] = value
    return base


def _as_list(value):
    """Return value as a list, treating None as an empty list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _include_spec_enabled(spec) -> bool:
    """Return whether an include spec is enabled."""
    if not isinstance(spec, dict):
        return True
    return bool(spec.get("enabled", True))


def _include_spec_path(spec):
    """Return the path/glob part of an include spec."""
    if isinstance(spec, str):
        return spec
    if isinstance(spec, dict):
        return spec.get("path") or spec.get("file") or spec.get("glob") or spec.get("dir")
    return None


def _matched_include_paths(spec, base_dir: Path) -> list[Path]:
    """
    Resolve one include spec into concrete files.

    Supported examples:
      includes: ["PDS/*.json", "HVS/CPA/*.json"]
      includes: [{path: "HVS", recursive: true}]
      includes: [{path: "CRP/cable_tray.json", enabled: true}]
    """
    raw = _include_spec_path(spec)
    if not raw:
        return []

    raw_path = Path(str(raw)).expanduser()
    if not raw_path.is_absolute():
        raw_path = base_dir / raw_path

    recursive = False
    if isinstance(spec, dict):
        recursive = bool(spec.get("recursive", False))

    # Directory include: read *.json and *.json5 from the directory.
    if raw_path.exists() and raw_path.is_dir():
        patterns = ["**/*.json", "**/*.json5"] if recursive else ["*.json", "*.json5"]
        out = []
        for pattern in patterns:
            out.extend(raw_path.glob(pattern))
        return sorted({p.resolve() for p in out if p.is_file()})

    # Glob include.
    raw_s = str(raw_path)
    if any(ch in raw_s for ch in "*?["):
        return sorted({p.resolve() for p in raw_path.parent.glob(raw_path.name) if p.is_file()})

    # Single file include.
    return [raw_path.resolve()] if raw_path.exists() and raw_path.is_file() else []


def _read_fdvd_fragment(path: Path):
    """Read one FD-VD JSON/JSON5 fragment file."""
    parser = _parser_for_path(path)
    with open(path, "r", encoding="utf-8") as f:
        return parser.load(f)


def _merge_fdvd_fragment(main_data: dict, fragment, fragment_path: Path, seen: set[Path]) -> None:
    """
    Merge one fragment into the main layout.

    Fragment formats supported:
      1) {items: [...], palette: {...}, defaults: {...}}
      2) [{...}, {...}]       # a bare item list
      3) {...}                # a single bare item object with type/id
    """
    base_dir = fragment_path.parent

    if isinstance(fragment, list):
        main_data.setdefault("items", []).extend(fragment)
        return

    if not isinstance(fragment, dict):
        logger.warning("Ignoring FD-VD include with unsupported top-level type: %s", fragment_path)
        return

    # Recurse first so a folder-level file can itself include smaller fragments.
    _expand_fdvd_includes(fragment, base_dir, seen)

    for key in ("palette", "defaults"):
        if isinstance(fragment.get(key), dict):
            _deep_merge_dicts(main_data.setdefault(key, {}), fragment[key])

    # Canvas is intentionally not deeply merged by default, because the main
    # file should own the global coordinate system. Allow explicit opt-in.
    if bool(fragment.get("merge_canvas", False)) and isinstance(fragment.get("canvas"), dict):
        _deep_merge_dicts(main_data.setdefault("canvas", {}), fragment["canvas"])

    if isinstance(fragment.get("items"), list):
        main_data.setdefault("items", []).extend(fragment["items"])
    elif fragment.get("type") and fragment.get("id"):
        # Convenient for tiny one-object files.
        main_data.setdefault("items", []).append(fragment)


def _expand_fdvd_includes(data: dict, base_dir: Path, seen: set[Path] | None = None) -> dict:
    """
    Expand modular FD-VD layout includes into one in-memory layout.

    Top-level supported keys:
      includes: ["PDS/*.json", "HVS/CPA/*.json"]
      include:  "CRP/cable_tray.json"
      item_files: [...]       # alias
      files: [...]            # alias

    Include paths are resolved relative to the file that contains them.
    The include keys are left in the data for transparency, but they are ignored
    by rendering after expansion.
    """
    if seen is None:
        seen = set()
    if not isinstance(data, dict):
        return data

    include_specs = []
    for key in ("includes", "include", "item_files", "files"):
        include_specs.extend(_as_list(data.get(key)))

    if not include_specs:
        return data

    data.setdefault("items", [])

    for spec in include_specs:
        if not _include_spec_enabled(spec):
            continue
        matches = _matched_include_paths(spec, base_dir)
        if not matches:
            logger.warning("FD-VD include matched no files: %r relative to %s", spec, base_dir)
            continue

        for path in matches:
            path = path.resolve()
            if path in seen:
                logger.warning("Skipping repeated/cyclic FD-VD include: %s", path)
                continue
            seen.add(path)
            try:
                fragment = _read_fdvd_fragment(path)
                _merge_fdvd_fragment(data, fragment, path, seen)
            except Exception:
                logger.exception("Failed to read FD-VD include file: %s", path)
                raise

    return data


def _ensure_default_layout(path: Path, chart_kind: str | None = None) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)

    if _HAS_JSON5:
        # Intentionally write JSON5-style content even when the file extension
        # is .json. The loader uses json5 when available, so comments,
        # trailing commas, and unquoted keys are supported.
        path.write_text(DEFAULT_FDVD_LAYOUT_JSON5.lstrip(), encoding="utf-8")
    else:
        # Strict fallback for environments where json5 has not been installed yet.
        path.write_text(_strict_json.dumps(DEFAULT_FDVD_LAYOUT, indent=2), encoding="utf-8")

    logger.info("Created default hierarchy layout file: %s", path)


def _load_layout(chart_kind: str | None = None) -> tuple[dict, str, str | None]:
    kind = _normalize_chart_kind(chart_kind)
    label = _chart_label(kind)
    path = _selected_layout_path_for_read(kind)
    try:
        _ensure_default_layout(path, kind)
        parser = _parser_for_path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = parser.load(f)
        if not isinstance(data, dict):
            raise ValueError("Hierarchy layout file must contain a top-level object/dictionary.")

        # Allow a tiny redirect/root file such as:
        #   { include: "fdvd/main.json" }
        # or:
        #   { include: "fdhd/main.json" }
        # The included file can then define canvas/palette/defaults/items.
        _expand_fdvd_includes(data, path.parent, seen={path.resolve()})

        if "canvas" not in data or "items" not in data:
            raise ValueError("Hierarchy layout file must contain 'canvas' and 'items' after includes are expanded.")
        data.setdefault("_chart_kind", kind)
        data.setdefault("_chart_label", label)
        return data, str(path), None
    except Exception as exc:
        logger.exception("Failed to load hierarchy layout file")
        hint = ""
        if not _HAS_JSON5:
            hint = " The python package 'json5' is not installed, so JSON5 comments/trailing commas cannot be parsed."
        fallback = dict(DEFAULT_FDVD_LAYOUT)
        fallback["_chart_kind"] = kind
        fallback["_chart_label"] = label
        return fallback, str(path), str(exc) + hint

def _item_details(item: dict) -> dict:
    """Return the details block for an item, with a backward-compatible default."""
    details = item.get("details") or {}
    if not isinstance(details, dict):
        details = {}
    out = {
        "title": item.get("label", item.get("id", "FD-VD item")),
        "bullets": [],
        "links": [],
    }
    out.update(details)
    return out


def _active_profile_name(default: str = "development") -> str:
    """Return the active Sisyphus profile name with a safe fallback."""
    try:
        name = str(config.config_data.get("active profile") or default).strip().lower()
        if name in ("development", "production"):
            return name
    except Exception:
        pass
    try:
        rest_api = str(config.active_profile.profile_data.get("rest api", "")).lower()
        if "cdbdev" in rest_api:
            return "development"
        if "cdb" in rest_api:
            return "production"
    except Exception:
        pass
    return default


def _hwdb_view_base_url() -> str:
    """Base HWDB browser URL root, matched to the active profile."""
    if _active_profile_name() == "production":
        return "https://dbweb2.fnal.gov:8443/cdb/view/"
    return "https://dbweb2.fnal.gov:8443/cdbdev/view/"


def _hwdb_component_type_url(part_type_id: str) -> str:
    """Return the HWDB browser URL for a component type ID.

    The HWDB browser expects component-type links in the filtered
    component_types page, for example:
      production:  https://dbweb2.fnal.gov:8443/cdb/view/component_types?pid=&sid=&ssid=&part=D00502000021&name=&cate=&comm=&crea=&subs=
      development: https://dbweb2.fnal.gov:8443/cdbdev/view/component_types?pid=&sid=&ssid=&part=D00502000021&name=&cate=&comm=&crea=&subs=
    """
    part = quote_plus(str(part_type_id or "").strip())
    return (
        _hwdb_view_base_url()
        + "component_types"
        + f"?pid=&sid=&ssid=&part={part}&name=&cate=&comm=&crea=&subs="
    )


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _first_present(mapping: dict, *keys, default=None):
    if not isinstance(mapping, dict):
        return default
    for key in keys:
        if key in mapping and mapping.get(key) not in (None, ""):
            return mapping.get(key)
    return default


def _entity_name(entity: dict | str | None) -> str:
    if isinstance(entity, dict):
        return str(_first_present(entity, "name", "type_name", "label", "title", default=""))
    if entity is None:
        return ""
    return str(entity)


def _entity_id(entity: dict | str | None) -> str:
    if isinstance(entity, dict):
        return str(_first_present(entity, "id", "type_id", "part_type_id", "component_type_id", default=""))
    return ""


def _entity_url(entity: dict | str | None) -> str | None:
    """Return explicit URL or an HWDB view URL inferred from a component type id."""
    if isinstance(entity, dict):
        explicit = _first_present(entity, "url", "href", "link", default=None)
        if explicit:
            return str(explicit)
        eid = _entity_id(entity)
        if eid:
            return _hwdb_component_type_url(eid)
    return None


def _entity_label(entity: dict | str | None, fallback: str = "item") -> str:
    if isinstance(entity, dict):
        name = _entity_name(entity)
        eid = _entity_id(entity)
        if name and eid:
            return f"{name} ({eid})"
        return name or eid or fallback
    if entity is None:
        return fallback
    return str(entity)


def _entity_link(entity: dict | str | None, fallback: str = "item"):
    label = _entity_label(entity, fallback=fallback)
    url = _entity_url(entity)
    if url:
        return html.A(label, href=url, target="_blank")
    return html.Span(label)


def _normalize_type_entry(value):
    """Normalize several convenient JSON spellings into a type-entry dict."""
    if not isinstance(value, dict):
        return {"name": str(value)}
    out = dict(value)
    # Accept type_name/type_id aliases but keep original keys too.
    if "name" not in out and "type_name" in out:
        out["name"] = out.get("type_name")
    if "id" not in out:
        for key in ("type_id", "part_type_id", "component_type_id"):
            if key in out:
                out["id"] = out.get(key)
                break
    return out


def _type_entries_from_details(details: dict) -> list[dict]:
    """Collect type entries from details.types, details.component_types, or single-type fields."""
    raw = None
    for key in ("types", "component_types", "componentTypes"):
        if key in details:
            raw = details.get(key)
            break
    if raw is not None:
        return [_normalize_type_entry(v) for v in _as_list(raw)]

    # Single type shorthand.
    if any(k in details for k in ("type_name", "type_id", "part_type_id", "component_type_id")):
        return [_normalize_type_entry({
            "name": details.get("type_name"),
            "id": _first_present(details, "type_id", "part_type_id", "component_type_id"),
            "description": details.get("type_description") or details.get("description"),
            "links": details.get("type_links") or [],
            # Parent may be a single object or an array.  Preserve both spellings.
            "parents": (
                details.get("parents")
                or details.get("parent_types")
                or details.get("parent")
                or details.get("parent_type")
                or []
            ),
            "children": details.get("children") or details.get("child_types") or [],
        })]
    return []


def _links_ul(links, empty_text: str | None = None):
    links = [x for x in _as_list(links) if x]
    if not links:
        return html.Div(empty_text) if empty_text else None
    lis = []
    for link in links:
        if isinstance(link, dict):
            label = link.get("label") or link.get("title") or link.get("url") or "link"
            url = link.get("url") or link.get("href") or "#"
            lis.append(html.Li(html.A(str(label), href=str(url), target="_blank")))
        else:
            lis.append(html.Li(str(link)))
    return html.Ul(lis)


def _details_subtitle(details: dict):
    """
    Render optional subtitle plus System/Sub-system metadata.

    Earlier versions returned immediately when `subtitle` existed, which meant
    `system_name/system_id` and `subsystem_name/subsystem_id` were hidden.
    This version shows both: the subtitle first, then a compact metadata block.
    """
    subtitle = details.get("subtitle")

    system = details.get("system") or {}
    subsystem = details.get("subsystem") or {}
    system_name = _first_present(details, "system_name", default=_entity_name(system))
    system_id = _first_present(details, "system_id", default=_entity_id(system))
    subsystem_name = _first_present(details, "subsystem_name", default=_entity_name(subsystem))
    subsystem_id = _first_present(details, "subsystem_id", default=_entity_id(subsystem))

    children = []

    if subtitle:
        children.append(html.Div(str(subtitle), className="text-muted mb-2"))

    rows = []
    if system_name or system_id:
        rows.append(
            html.Div(
                [
                    html.B("System: "),
                    html.Span(str(system_name or "—")),
                    html.Span(f" ({system_id})" if system_id else ""),
                ],
                className="mb-1",
            )
        )
    if subsystem_name or subsystem_id:
        rows.append(
            html.Div(
                [
                    html.B("Subsystem: "),
                    html.Span(str(subsystem_name or "—")),
                    html.Span(f" ({subsystem_id})" if subsystem_id else ""),
                ],
                className="mb-1",
            )
        )

    if rows:
        children.append(
            html.Div(
                rows,
                className="border rounded p-2 mb-3",
                style={"backgroundColor": "#f8f9fa"},
            )
        )

    if children:
        return html.Div(children)
    return None


def _render_type_card(type_entry: dict, index: int, total: int):
    t = _normalize_type_entry(type_entry)
    name = _entity_name(t) or f"Type {index}"
    tid = _entity_id(t)
    title = _entity_link(t, fallback=name)
    description = _first_present(t, "description", "brief", "summary", default=None)
    links = t.get("links") or t.get("urls") or []
    parents_raw = (
        t.get("parents")
        or t.get("parent_types")
        or t.get("parent")
        or t.get("parent_type")
        or []
    )
    parents = [_normalize_type_entry(p) for p in _as_list(parents_raw) if p]
    children = t.get("children") or t.get("child_types") or []

    card_children = [
        html.H5(title, className="mb-2"),
    ]
    if description:
        card_children.append(html.P(str(description), className="mb-2"))

    links_ul = _links_ul(links)
    if links_ul:
        card_children.extend([html.Div(html.B("Documentation / external links")), links_ul])

    if parents:
        parent_heading = "Parent type" if len(parents) == 1 else "Parent types"
        card_children.extend([
            html.Div(html.B(parent_heading), className="mt-2"),
            html.Ul([html.Li(_entity_link(parent, fallback="Parent type")) for parent in parents]),
        ])

    children = [_normalize_type_entry(c) for c in _as_list(children)]
    if children:
        card_children.extend([
            html.Div(html.B("Children"), className="mt-2"),
            html.Ul([html.Li(_entity_link(child, fallback="Child type")) for child in children]),
        ])

    if tid and not _entity_url(t):
        card_children.append(html.Div(f"Type ID: {tid}", className="text-muted"))

    return html.Div(
        card_children,
        className="border rounded p-3 mb-3",
        style={"backgroundColor": "#fafafa"},
    )


def _modal_body(details: dict):
    """
    Render the details modal.

    Backward-compatible fields:
      title, bullets, links

    New optional fields:
      subtitle
      system: {name, id} or system_name/system_id
      subsystem: {name, id} or subsystem_name/subsystem_id
      types: [
        {
          name/type_name, id/type_id/part_type_id,
          description,
          links: [{label, url}],
          // parent can still be a single object for backward compatibility:
          parent: {name, id, url?},

          // preferred when there may be more than one parent:
          parents: [{name, id, url?}, ...],

          children: [{name, id, url?}, ...],
        }
      ]

    If url is omitted for a type/parent/child, the callback generates an HWDB
    browser URL using the active Sisyphus profile:
      development -> https://dbweb2.fnal.gov:8443/cdbdev/view/component_types?pid=&sid=&ssid=&part=<TYPE_ID>&name=&cate=&comm=&crea=&subs=
      production  -> https://dbweb2.fnal.gov:8443/cdb/view/component_types?pid=&sid=&ssid=&part=<TYPE_ID>&name=&cate=&comm=&crea=&subs=
    """
    bullets = details.get("bullets") or []
    links = details.get("links") or []
    type_entries = _type_entries_from_details(details)

    children = []

    subtitle = _details_subtitle(details)
    if subtitle:
        children.append(subtitle)

    if bullets:
        children.append(html.Ul([html.Li(str(b)) for b in bullets]))
    elif not type_entries:
        children.append(html.Div("No details have been added for this item yet."))

    if type_entries:
        if bullets:
            children.append(html.Hr())
        children.append(html.H5("Component type information"))
        for i, type_entry in enumerate(type_entries, start=1):
            children.append(_render_type_card(type_entry, i, len(type_entries)))

    links_ul = _links_ul(links)
    if links_ul:
        children.extend(
            [
                html.Hr(),
                html.H5("Links"),
                links_ul,
            ]
        )

    return children


def _find_item(data: dict, item_id: str | None) -> dict | None:
    if not item_id:
        return None
    for item in data.get("items", []):
        item_with_defaults = _with_defaults(item, data)
        if item_with_defaults.get("id") == item_id:
            return item_with_defaults
    return None


def _num(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)




def _bool_from_item_or_canvas(item: dict, data: dict | None, key: str, default: bool = False) -> bool:
    """Resolve a boolean option, allowing per-item override or canvas default."""
    if isinstance(item, dict) and key in item:
        return bool(item.get(key))
    canvas = (data or {}).get("canvas") or {}
    return bool(canvas.get(key, default))


def _zoom_scale_from_relayout(relayout_data, canvas_width: float, canvas_height: float) -> float:
    """
    Estimate Plotly zoom scale from relayoutData.

    Full-canvas view returns 1.0.  If the user zooms into half the canvas width,
    this returns about 2.0.  This is used only for screen-pixel-sized things
    such as fonts and marker dots.  Geometric objects drawn in data coordinates
    such as boxes, bands, arrow paths, dash spacing, and triangle arrowheads
    already scale naturally with the Plotly axes.
    """
    rd = relayout_data or {}
    if not isinstance(rd, dict):
        return 1.0

    # Reset/autoscale/home buttons should behave like full canvas.
    if rd.get("xaxis.autorange") or rd.get("yaxis.autorange"):
        return 1.0

    def _range(axis_name: str):
        direct = rd.get(f"{axis_name}.range")
        if isinstance(direct, (list, tuple)) and len(direct) >= 2:
            return _num(direct[0], 0), _num(direct[1], 0)
        k0 = f"{axis_name}.range[0]"
        k1 = f"{axis_name}.range[1]"
        if k0 in rd and k1 in rd:
            return _num(rd[k0], 0), _num(rd[k1], 0)
        return None

    xr = _range("xaxis")
    yr = _range("yaxis")

    scales = []
    if xr:
        span = abs(xr[1] - xr[0])
        if span > 1e-9:
            scales.append(float(canvas_width) / span)
    if yr:
        span = abs(yr[1] - yr[0])
        if span > 1e-9:
            scales.append(float(canvas_height) / span)

    if not scales:
        return 1.0

    # With scaleanchor='x', these are usually the same.  The geometric mean is
    # stable if only one axis range is reported or if the viewport aspect differs.
    scale = 1.0
    for v in scales:
        scale *= max(v, 1e-9)
    scale = scale ** (1.0 / len(scales))

    # Avoid absurd font/marker sizes after extreme zooming.
    return max(0.25, min(float(scale), 12.0))


def _scale_value(value, zoom_scale: float, enabled: bool, min_value: float | None = None, max_value: float | None = None):
    """Scale a pixel-sized Plotly value when requested."""
    out = _num(value, value)
    if enabled:
        out *= max(float(zoom_scale or 1.0), 0.01)
    if min_value is not None:
        out = max(float(min_value), out)
    if max_value is not None:
        out = min(float(max_value), out)
    return out


def _palette(data: dict | None) -> dict:
    palette = (data or {}).get("palette") or {}
    return palette if isinstance(palette, dict) else {}


def _deep_merge_dicts(base: dict | None, override: dict | None) -> dict:
    """Recursively merge dictionaries without modifying either input."""
    out = dict(base or {})
    for key, value in (override or {}).items():
        if (
            isinstance(value, dict)
            and isinstance(out.get(key), dict)
        ):
            out[key] = _deep_merge_dicts(out.get(key), value)
        else:
            out[key] = value
    return out


def _with_defaults(item: dict | None, data: dict | None) -> dict:
    """
    Apply top-level defaults by item type.

    JSON5 example:
      defaults: {
        box: {font: {size: 13, bold: true, family: "Arial"}},
        arrow: {stroke: "signal_red", arrow_end: true},
      }

    Item values override defaults. Nested dictionaries, especially font, are
    merged instead of replaced, so font: {size: 18} keeps default bold/family.
    """
    item = dict(item or {})
    defaults = (data or {}).get("defaults") or {}
    if not isinstance(defaults, dict):
        return item

    item_type = str(item.get("type", "")).strip().lower()
    base = defaults.get(item_type) or {}
    if not isinstance(base, dict):
        return item

    return _deep_merge_dicts(base, item)


def _resolve_color(value, palette: dict | None = None, default="#111111"):
    """
    Resolve a color value from either a direct CSS color/hex value or a palette alias.

    Examples:
      "dune_blue" -> "#174cff" when palette["dune_blue"] exists
      "#174cff"   -> "#174cff"
      "red"       -> "red" unless palette["red"] exists
    """
    if value is None or value == "":
        return default
    if isinstance(value, str):
        p = palette or {}
        if value in p and not value.startswith("_"):
            return p[value]
    return value


def _coords_mode(item: dict, data: dict | None = None) -> str:
    """
    Coordinate mode may be defined per item with coords='relative'.
    Optionally, canvas.default_coords can set a file-wide default.
    Default remains absolute for backward compatibility.
    """
    canvas = (data or {}).get("canvas") or {}
    mode = item.get("coords", canvas.get("default_coords", "absolute"))
    return str(mode or "absolute").lower()


def _resolve_x(value, canvas_width: float, coords: str = "absolute", default=0.0) -> float:
    v = _num(value, default)
    if str(coords).lower() in ("relative", "rel", "fraction", "normalized", "normalised"):
        return v * canvas_width
    return v


def _resolve_y(value, canvas_height: float, coords: str = "absolute", default=0.0) -> float:
    v = _num(value, default)
    if str(coords).lower() in ("relative", "rel", "fraction", "normalized", "normalised"):
        return v * canvas_height
    return v


def _resolve_w(value, canvas_width: float, coords: str = "absolute", default=0.0) -> float:
    return _resolve_x(value, canvas_width, coords, default)


def _resolve_h(value, canvas_height: float, coords: str = "absolute", default=0.0) -> float:
    return _resolve_y(value, canvas_height, coords, default)


def _resolve_point(point, canvas_width: float, canvas_height: float, coords: str = "absolute") -> tuple[float, float]:
    try:
        x, y = point
    except Exception:
        x, y = 0, 0
    return _resolve_x(x, canvas_width, coords), _resolve_y(y, canvas_height, coords)


def _border_dash_value(style) -> str:
    """
    Resolve Plotly shape border style.

    Supported JSON values:
      border_style: "solid", "dashed", "dotted", "dashdot", "longdash", "none"

    Plotly layout shapes support a limited set of dash names rather than
    arbitrary px patterns, so this helper maps friendly aliases to those names.
    """
    style = str(style or "solid").strip().lower().replace("-", "_")
    mapping = {
        "": "solid",
        "solid": "solid",
        "line": "solid",
        "none": "solid",   # handled by width=0 in _shape_line
        "no_border": "solid",
        "noborder": "solid",
        "dash": "dash",
        "dashed": "dash",
        "shortdash": "dash",
        "longdash": "longdash",
        "long_dash": "longdash",
        "dot": "dot",
        "dotted": "dot",
        "dashdot": "dashdot",
        "dash_dot": "dashdot",
        "longdashdot": "longdashdot",
        "long_dash_dot": "longdashdot",
    }
    return mapping.get(style, "solid")


def _shape_line(selected: bool, color="#333333", palette: dict | None = None, item: dict | None = None, default_width=1):
    """
    Resolve the border/outline style for boxes and bands.

    New JSON options supported for box/band items:
      border_color: "signal_red"   # palette alias or direct color
      border_width: 3
      border_style: "dashed"       # solid, dashed, dotted, dashdot, longdash, none

    Backward-compatible aliases:
      line_color, stroke_color
      line_width, stroke_width, border_thickness
      line_style, border_dash
    """
    item = item or {}

    raw_style = item.get("border_style", item.get("border_dash", item.get("box_border_style", None)))
    if raw_style is None:
        # For boxes/bands, line_style is accepted as a border alias.  Arrows
        # already use line_style for arrow bodies, but they do not call this helper.
        raw_style = item.get("line_style", "solid")

    style_name = str(raw_style or "solid").strip().lower().replace("-", "_")

    raw_width = item.get(
        "border_width",
        item.get(
            "border_thickness",
            item.get("box_border_width", item.get("line_width", item.get("stroke_width", default_width))),
        ),
    )
    width = _num(raw_width, default_width)

    if style_name in ("none", "no_border", "noborder"):
        width = 0

    raw_color = item.get(
        "border_color",
        item.get("box_border_color", item.get("line_color", item.get("stroke_color", color))),
    )
    border_color = _resolve_color(raw_color, palette, color)

    if selected:
        border_color = _resolve_color("highlight_yellow", palette, "#ffd000")
        width = max(width, 5)

    return {
        "color": border_color,
        "width": max(width, 0),
        "dash": _border_dash_value(style_name),
    }




def _fdvd_item_map(data: dict | None) -> dict:
    """Return a dictionary of diagram items keyed by their JSON id."""
    out = {}
    for raw in (data or {}).get("items", []) or []:
        if not isinstance(raw, dict):
            continue
        item_id = raw.get("id")
        if item_id:
            out[str(item_id)] = raw
    return out


def _object_geometry(item: dict, data: dict, canvas_width: float, canvas_height: float):
    """
    Return (x, y, w, h) for a box-like object.

    This is used by arrows that connect to boxes/bands by id.  The same default
    and coordinate rules used by the visible box/band renderers are applied here.
    """
    item = _with_defaults(item, data)
    coords = _coords_mode(item, data)
    x = _resolve_x(item.get("x"), canvas_width, coords)
    y = _resolve_y(item.get("y"), canvas_height, coords)
    w = _resolve_w(item.get("w"), canvas_width, coords)
    h = _resolve_h(item.get("h"), canvas_height, coords)
    return x, y, w, h


def _port_fraction(port, ports, default=0.5) -> float:
    """
    Convert a 1-based port index into a fraction along a box side.

    Example: port=2, ports=5 -> 2/(5+1) = 0.333...
    This keeps multiple incoming/outgoing arrows from landing on the same point.
    """
    try:
        n_ports = int(ports)
        n_port = int(port)
    except Exception:
        return float(default)

    if n_ports <= 0:
        return float(default)

    n_port = max(1, min(n_port, n_ports))
    return n_port / (n_ports + 1.0)


def _anchor_point(
    obj_item: dict,
    data: dict,
    canvas_width: float,
    canvas_height: float,
    anchor="center",
    port=None,
    ports=None,
    offset=None,
    offset_coords=None,
) -> tuple[float, float]:
    """
    Resolve a point on a box/band by anchor name.

    Supported anchors:
      center, top, bottom, left, right,
      top_left, top_right, bottom_left, bottom_right

    For side anchors, port/ports can spread multiple arrows along the side:
      to_anchor: "left", to_port: 2, to_ports: 5

    offset is added after anchor resolution.  By default, offset uses the
    connected object's coordinate mode; set offset_coords: "absolute" or
    "relative" to override that.
    """
    x, y, w, h = _object_geometry(obj_item, data, canvas_width, canvas_height)
    a = str(anchor or "center").strip().lower().replace("-", "_").replace(" ", "_")

    if a in ("top_left", "upper_left", "tl"):
        px, py = x, y
    elif a in ("top_right", "upper_right", "tr"):
        px, py = x + w, y
    elif a in ("bottom_left", "lower_left", "bl"):
        px, py = x, y + h
    elif a in ("bottom_right", "lower_right", "br"):
        px, py = x + w, y + h
    elif a in ("top", "north", "n"):
        frac = _port_fraction(port, ports, default=0.5)
        px, py = x + w * frac, y
    elif a in ("bottom", "south", "s"):
        frac = _port_fraction(port, ports, default=0.5)
        px, py = x + w * frac, y + h
    elif a in ("left", "west", "w"):
        frac = _port_fraction(port, ports, default=0.5)
        px, py = x, y + h * frac
    elif a in ("right", "east", "e"):
        frac = _port_fraction(port, ports, default=0.5)
        px, py = x + w, y + h * frac
    else:
        px, py = x + w / 2.0, y + h / 2.0

    if offset is not None:
        obj_coords = _coords_mode(_with_defaults(obj_item, data), data)
        oc = str(offset_coords or obj_coords or "absolute").lower()
        ox, oy = _resolve_point(offset, canvas_width, canvas_height, oc)
        px += ox
        py += oy

    return px, py


def _connected_endpoint(
    item: dict,
    data: dict,
    canvas_width: float,
    canvas_height: float,
    *,
    end: str,
    fallback_point=None,
):
    """
    Resolve one arrow endpoint.

    end must be "from" or "to".  If from_id/to_id is present, the endpoint is
    attached to that object.  Otherwise the provided coordinate fallback is used.
    """
    item_map = _fdvd_item_map(data)
    key_id = f"{end}_id"
    target_id = item.get(key_id)

    if target_id:
        target = item_map.get(str(target_id))
        if isinstance(target, dict):
            return _anchor_point(
                target,
                data,
                canvas_width,
                canvas_height,
                anchor=item.get(f"{end}_anchor", "center"),
                port=item.get(f"{end}_port", item.get(f"{end}_port_index")),
                ports=item.get(f"{end}_ports", item.get(f"{end}_port_count")),
                offset=item.get(f"{end}_offset"),
                offset_coords=item.get(f"{end}_offset_coords", item.get("offset_coords")),
            )
        logger.warning("[FD-VD] Arrow %r references missing %s=%r", item.get("id"), key_id, target_id)

    coords = _coords_mode(item, data)
    if fallback_point is not None:
        return _resolve_point(fallback_point, canvas_width, canvas_height, coords)
    return _resolve_point(item.get(end, [0, 0]), canvas_width, canvas_height, coords)

def _add_click_target(fig, item_id, x, y, hover_text, size=28):
    """
    Plotly layout shapes themselves are not reliably clickable.
    This transparent marker gives each item a stable clickable target.
    """
    fig.add_trace(
        go.Scatter(
            x=[x],
            y=[y],
            mode="markers",
            marker={"size": size, "color": "rgba(0,0,0,0.01)", "line": {"width": 0}},
            customdata=[item_id],
            hovertemplate=str(hover_text) + "<extra></extra>",
            showlegend=False,
        )
    )


def _font_options(item: dict, data: dict | None, default_size=13, default_color="#111111", default_bold=False, zoom_scale: float = 1.0):
    """
    Resolve font options for an item's visible label.

    Supported JSON styles:

      font: {
        size: 13,
        color: "white",
        family: "Arial",
        bold: true,
      }

    Legacy/shorthand keys are also still supported:
      font_size, font_color, font_family, font_bold, bold
    """
    palette = _palette(data)
    canvas = (data or {}).get("canvas") or {}
    default_font = canvas.get("default_font") or {}
    font = item.get("font") or {}
    if not isinstance(font, dict):
        font = {}
    if not isinstance(default_font, dict):
        default_font = {}

    size = font.get("size", item.get("font_size", default_font.get("size", default_size)))
    family = font.get("family", item.get("font_family", default_font.get("family", None)))
    bold = font.get("bold", item.get("font_bold", item.get("bold", default_font.get("bold", default_bold))))
    color = font.get("color", item.get("font_color", default_font.get("color", default_color)))

    scale_text = bool(font.get("scale_with_zoom", item.get("font_scale_with_zoom", item.get("scale_text_with_zoom", default_font.get("scale_with_zoom", canvas.get("scale_text_with_zoom", True))))))

    return {
        "size": _scale_value(size, zoom_scale, scale_text, min_value=1, max_value=240),
        "family": family,
        "bold": bool(bold),
        "color": _resolve_color(color, palette, default_color),
    }


def _plotly_label_text(text, bold=False):
    """Return label text safe for Plotly's limited HTML rendering."""
    escaped = _html_escape(str(text))
    return f"<b>{escaped}</b>" if bold else escaped


def _object_label_xy(item: dict, x: float, y: float, w: float, h: float, default_rel=(0.5, 0.5), default_offset=(0, 0)):
    """
    Resolve a label position relative to its own object.

    Preferred JSON keys for boxes/bands:
      label_rel: [0.5, 0.5]       // relative inside this object
      label_offset: [0, 0]        // pixel offset by default
      label_offset_coords: "relative"  // optional; offset is fraction of object size

    Optional absolute/canvas-coordinate override:
      label_x: ...
      label_y: ...

    For object-relative positions:
      [0.0, 0.0] = top-left of the object
      [0.5, 0.5] = center of the object
      [1.0, 1.0] = bottom-right of the object
    """
    if "label_rel" in item:
        rel = item.get("label_rel")
    elif "label_position" in item:
        # A few human-readable aliases for convenience.
        aliases = {
            "center": (0.5, 0.5),
            "middle": (0.5, 0.5),
            "left": (0.0, 0.5),
            "right": (1.0, 0.5),
            "top": (0.5, 0.0),
            "bottom": (0.5, 1.0),
            "top_left": (0.0, 0.0),
            "top-left": (0.0, 0.0),
            "top_right": (1.0, 0.0),
            "top-right": (1.0, 0.0),
            "bottom_left": (0.0, 1.0),
            "bottom-left": (0.0, 1.0),
            "bottom_right": (1.0, 1.0),
            "bottom-right": (1.0, 1.0),
        }
        rel = aliases.get(str(item.get("label_position", "")).lower(), default_rel)
    else:
        rel = default_rel

    try:
        rx, ry = rel
    except Exception:
        rx, ry = default_rel

    lx = x + _num(rx, default_rel[0]) * w
    ly = y + _num(ry, default_rel[1]) * h

    offset = item.get("label_offset", default_offset)
    try:
        dx, dy = offset
    except Exception:
        dx, dy = default_offset

    if str(item.get("label_offset_coords", "absolute")).lower() in ("relative", "rel", "fraction", "normalized", "normalised"):
        lx += _num(dx, default_offset[0]) * w
        ly += _num(dy, default_offset[1]) * h
    else:
        lx += _num(dx, default_offset[0])
        ly += _num(dy, default_offset[1])

    return lx, ly


def _add_label(
    fig,
    item_id,
    x,
    y,
    text,
    color="#111111",
    size=13,
    bold=False,
    family=None,
    hover_text=None,
    angle=0,
):
    """
    Add a visible label.

    Plotly Scatter text does not support rotated text in older Plotly versions,
    so labels with a non-zero angle are drawn as annotations.  A transparent
    click target is added separately by the caller/item renderer, so modal
    clicking still works.
    """
    textfont = {"color": color, "size": size}
    if family:
        textfont["family"] = family

    label_text = _plotly_label_text(text, bold=bold)
    angle = _num(angle, 0)

    if abs(angle) > 0.001:
        fig.add_annotation(
            x=x,
            y=y,
            xref="x",
            yref="y",
            text=label_text,
            textangle=angle,
            showarrow=False,
            font=textfont,
            align="center",
            bgcolor="rgba(255,255,255,0)",
            borderwidth=0,
            opacity=1,
        )
        return

    fig.add_trace(
        go.Scatter(
            x=[x],
            y=[y],
            mode="text",
            text=[label_text],
            textfont=textfont,
            textposition="middle center",
            customdata=[item_id],
            hovertemplate=str(hover_text or text) + "<extra></extra>",
            showlegend=False,
        )
    )


def _line_style_name(item: dict) -> str:
    """
    Resolve FD-VD arrow line style.

    Supported JSON5 options:
      line_style: "solid", "dashed", "dotted", "dashdot"
      dash: true                         # older shorthand -> dashed

    Unlike earlier versions, dotted/dashed lines are drawn explicitly as
    separate geometry rather than relying on Plotly's line.dash.  This avoids
    the annotation-arrow shaft making dotted lines look solid.
    """
    style = str(item.get("line_style", item.get("dash_style", "")) or "").strip().lower()
    if not style:
        style = "dashed" if item.get("dash") else "solid"

    aliases = {
        "solid": "solid",
        "line": "solid",
        "none": "solid",
        "dashed": "dashed",
        "dash": "dashed",
        "longdash": "dashed",
        "long-dash": "dashed",
        "dotted": "dotted",
        "dot": "dotted",
        "dashdot": "dashdot",
        "dash-dot": "dashdot",
        "dash_dot": "dashdot",
    }
    return aliases.get(style, "solid")


def _dash_pattern_numbers(item: dict) -> tuple[float | None, float | None]:
    """
    Parse a Plotly/CSS-like dash pattern such as "2px,20px".

    Returns the first two positive numbers.  For explicit geometry:
      dotted: first number is dot size, second number is gap
      dashed: first number is dash length, second number is gap
    """
    raw = item.get("dash_pattern", item.get("line_dash", None))
    if not raw:
        return None, None
    text = str(raw)
    nums = []
    for part in text.replace(",", " ").split():
        part = part.strip().lower().replace("px", "")
        try:
            val = float(part)
            if val > 0:
                nums.append(val)
        except Exception:
            pass
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], None
    return None, None


def _polyline_length(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points[:-1], points[1:]):
        total += math.hypot(x2 - x1, y2 - y1)
    return total


def _point_at_distance(points: list[tuple[float, float]], dist: float) -> tuple[float, float]:
    """Return a point at distance dist along a polyline."""
    if not points:
        return 0.0, 0.0
    if dist <= 0:
        return points[0]

    remaining = dist
    for (x1, y1), (x2, y2) in zip(points[:-1], points[1:]):
        seg_len = math.hypot(x2 - x1, y2 - y1)
        if seg_len <= 1e-9:
            continue
        if remaining <= seg_len:
            t = remaining / seg_len
            return x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        remaining -= seg_len
    return points[-1]


def _line_segments_for_dashes(
    points: list[tuple[float, float]],
    dash_length: float,
    dash_gap: float,
) -> tuple[list[float], list[float]]:
    """
    Return x/y arrays with None separators for explicit dashed polyline drawing.
    """
    total = _polyline_length(points)
    if total <= 0:
        return [], []

    dash_length = max(float(dash_length), 1.0)
    dash_gap = max(float(dash_gap), 1.0)

    xs, ys = [], []
    d = 0.0
    while d < total:
        d2 = min(d + dash_length, total)
        x1, y1 = _point_at_distance(points, d)
        x2, y2 = _point_at_distance(points, d2)
        xs.extend([x1, x2, None])
        ys.extend([y1, y2, None])
        d += dash_length + dash_gap
    return xs, ys


def _points_for_dots(
    points: list[tuple[float, float]],
    spacing: float,
) -> tuple[list[float], list[float]]:
    """Return x/y arrays for explicit dotted polyline drawing."""
    total = _polyline_length(points)
    if total <= 0:
        return [], []

    spacing = max(float(spacing), 2.0)
    # Start half a spacing in, so the first visible dot usually does not sit
    # directly under an arrowhead.  This also makes very large spacing useful
    # for debugging, e.g. dash_pattern: "2px,2000px".
    d = min(spacing / 2.0, total)
    xs, ys = [], []
    while d < total:
        x, y = _point_at_distance(points, d)
        xs.append(x)
        ys.append(y)
        d += spacing
    if not xs:
        x, y = _point_at_distance(points, total / 2.0)
        xs.append(x)
        ys.append(y)
    return xs, ys


def _arrowhead_triangle_points(
    tail: tuple[float, float],
    head: tuple[float, float],
    length: float,
    width: float,
) -> list[tuple[float, float]]:
    """
    Triangle points for an arrowhead at `head`, pointing from `tail` to `head`.
    Coordinates use the same screen-like FD-VD convention as the JSON: y grows
    downward, and the Plotly y-axis is reversed to match that convention.
    """
    tx, ty = tail
    hx, hy = head
    dx = hx - tx
    dy = hy - ty
    mag = math.hypot(dx, dy)
    if mag <= 1e-9:
        return [(hx, hy), (hx, hy), (hx, hy)]

    ux = dx / mag
    uy = dy / mag
    # Perpendicular vector.
    px = -uy
    py = ux

    base_x = hx - ux * length
    base_y = hy - uy * length
    half_w = width / 2.0

    return [
        (hx, hy),
        (base_x + px * half_w, base_y + py * half_w),
        (base_x - px * half_w, base_y - py * half_w),
    ]



def _resolve_offset_pair(value, canvas_width, canvas_height, coords="absolute", default=(0.0, 0.0)):
    """
    Resolve an [x, y] offset. By default offsets are in canvas/data units.
    If coords == "relative", x is scaled by canvas width and y by canvas height.
    """
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return float(default[0]), float(default[1])
    try:
        ox = float(value[0])
        oy = float(value[1])
    except Exception:
        return float(default[0]), float(default[1])

    if str(coords or "absolute").lower().strip() in ("relative", "rel", "fraction", "frac"):
        return ox * canvas_width, oy * canvas_height
    return ox, oy


def _arrow_midpoint(points):
    """Return the point halfway along a polyline's actual path length."""
    if not points:
        return 0.0, 0.0
    if len(points) == 1:
        return points[0]
    return _point_at_distance(points, _polyline_length(points) / 2.0)


def _arrow_label_xy(item, points, canvas_width, canvas_height, coords="absolute"):
    """
    Resolve an arrow label position.

    Highest priority:
      label_x / label_y

    Otherwise use label_position / label_side:
      center, middle, mid
      left, left_side
      right, right_side
      top, above
      bottom, below
      start, from
      end, to

    Optional:
      label_distance: distance from path/bounding box for left/right/top/bottom
      label_offset: [dx, dy] final offset in absolute canvas units
      label_offset_coords: "relative" to scale offset by canvas size
    """
    if not points:
        return 0.0, 0.0

    # Base automatic position
    pos = str(
        item.get("label_position", item.get("label_pos", item.get("label_side", "center")))
        or "center"
    ).lower().strip().replace("-", "_").replace(" ", "_")

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    xmid = (xmin + xmax) / 2.0
    ymid = (ymin + ymax) / 2.0

    # For very thin vertical/horizontal paths, this keeps labels away from the line.
    distance = _num(item.get("label_distance", item.get("label_margin", 12)), 12)

    if pos in ("center", "middle", "mid", "path_center", "path_middle"):
        lx, ly = _arrow_midpoint(points)
    elif pos in ("start", "from", "source"):
        lx, ly = points[0]
    elif pos in ("end", "to", "target"):
        lx, ly = points[-1]
    elif pos in ("left", "left_side", "side_left"):
        lx, ly = xmin - distance, ymid
    elif pos in ("right", "right_side", "side_right"):
        lx, ly = xmax + distance, ymid
    elif pos in ("top", "above", "upper"):
        lx, ly = xmid, ymin - distance
    elif pos in ("bottom", "below", "lower"):
        lx, ly = xmid, ymax + distance
    elif pos in ("start_left", "from_left"):
        lx, ly = points[0][0] - distance, points[0][1]
    elif pos in ("start_right", "from_right"):
        lx, ly = points[0][0] + distance, points[0][1]
    elif pos in ("end_left", "to_left"):
        lx, ly = points[-1][0] - distance, points[-1][1]
    elif pos in ("end_right", "to_right"):
        lx, ly = points[-1][0] + distance, points[-1][1]
    else:
        lx, ly = _arrow_midpoint(points)

    # Explicit x/y override automatic position independently.
    if "label_x" in item:
        lx = _resolve_x(item.get("label_x"), canvas_width, coords)
    if "label_y" in item:
        ly = _resolve_y(item.get("label_y"), canvas_height, coords)

    offset_coords = item.get("label_offset_coords", item.get("offset_coords", "absolute"))
    ox, oy = _resolve_offset_pair(item.get("label_offset", [0, 0]), canvas_width, canvas_height, offset_coords)
    return lx + ox, ly + oy


def _add_arrowhead_shape(fig, tail, head, color, line_color=None, length=16, width=12):
    """Draw an arrowhead only, with no solid annotation shaft."""
    pts = _arrowhead_triangle_points(tail, head, length=length, width=width)
    path = "M " + " L ".join(f"{x},{y}" for x, y in pts) + " Z"
    fig.add_shape(
        type="path",
        path=path,
        fillcolor=color,
        line={"color": line_color or color, "width": 0.5},
        layer="above",
    )


def _anchor_family(anchor) -> str:
    """
    Classify an anchor into a side family.

    This is used for simple automatic routing.  Corner anchors such as
    "top_left" are treated as vertical because they include "top"/"bottom".
    """
    a = str(anchor or "").strip().lower().replace("-", "_")
    if "top" in a or "bottom" in a:
        return "vertical"
    if "left" in a or "right" in a:
        return "horizontal"
    return "center"


def _route_mode(item: dict) -> str:
    """Normalize arrow route names."""
    route = str(item.get("route", item.get("routing", "straight")) or "straight").strip().lower()
    route = route.replace("-", "_")
    aliases = {
        "": "straight",
        "direct": "straight",
        "line": "straight",
        "none": "straight",
        "v": "vertical",
        "vert": "vertical",
        "vertical_line": "vertical",
        "h": "horizontal",
        "horiz": "horizontal",
        "horizontal_line": "horizontal",
        "h_then_v": "hv",
        "horizontal_vertical": "hv",
        "v_then_h": "vh",
        "vertical_horizontal": "vh",
        "ortho": "orthogonal",
        "elbow": "orthogonal",
        "right_angle": "orthogonal",
        "rightangle": "orthogonal",
    }
    return aliases.get(route, route)


def _routed_points(item: dict, start: tuple[float, float], finish: tuple[float, float]) -> list[tuple[float, float]]:
    """
    Build a simple routed path between two resolved endpoints.

    Supported route modes:
      straight      start -> finish
      vertical      use a vertical path by aligning x values
      horizontal    use a horizontal path by aligning y values
      hv            horizontal then vertical
      vh            vertical then horizontal
      orthogonal    choose hv/vh from anchors
      auto          vertical for top/bottom anchors, horizontal for left/right anchors

    For route="vertical" and route="horizontal", the default behavior is to
    slide the *source* endpoint along its anchor side so the arrow can be drawn
    truly vertical/horizontal.  This is especially useful for wide bands.

    Optional:
      route_align: "to"   # default; align source x/y to target
      route_align: "from" # align target x/y to source
    """
    sx, sy = start
    fx, fy = finish

    route = _route_mode(item)
    from_anchor = item.get("from_anchor", "center")
    to_anchor = item.get("to_anchor", "center")
    from_family = _anchor_family(from_anchor)
    to_family = _anchor_family(to_anchor)

    if route == "auto":
        if from_family == "vertical" and to_family == "vertical":
            route = "vertical"
        elif from_family == "horizontal" and to_family == "horizontal":
            route = "horizontal"
        elif from_family == "vertical" and to_family == "horizontal":
            route = "vh"
        elif from_family == "horizontal" and to_family == "vertical":
            route = "hv"
        else:
            route = "straight"

    if route == "orthogonal":
        # Leave a side in the direction suggested by from_anchor where possible.
        if from_family == "horizontal":
            route = "hv"
        elif from_family == "vertical":
            route = "vh"
        elif to_family == "horizontal":
            route = "vh"
        elif to_family == "vertical":
            route = "hv"
        else:
            route = "hv"

    align = str(item.get("route_align", item.get("align", "to")) or "to").strip().lower()

    if route == "vertical":
        if align in ("from", "source", "start"):
            return [(sx, sy), (sx, fy)]
        # Default: slide the source point along its top/bottom edge to the
        # target x.  For a full-width band this gives a clean vertical drop.
        return [(fx, sy), (fx, fy)]

    if route == "horizontal":
        if align in ("from", "source", "start"):
            return [(sx, sy), (fx, sy)]
        # Default: slide the source point along its left/right edge to the
        # target y.  For a tall band this gives a clean horizontal arrow.
        return [(sx, fy), (fx, fy)]

    if route == "hv":
        return [(sx, sy), (fx, sy), (fx, fy)]

    if route == "vh":
        return [(sx, sy), (sx, fy), (fx, fy)]

    return [(sx, sy), (fx, fy)]


def _arrow_points(item: dict, data: dict, canvas_width: float, canvas_height: float, coords: str | None = None) -> list[tuple[float, float]]:
    """
    Resolve arrow points.

    Supported forms:

      1) Explicit path, old style:
         points: [[x1, y1], [x2, y2], ...]

      2) Straight arrow, old style:
         from: [x1, y1], to: [x2, y2]

      3) Connected arrow:
         from_id: "source_box"
         to_id: "target_box"
         from_anchor: "right"
         to_anchor: "left"
         via: [[x_mid, y_mid], ...]

      4) Connected arrow with automatic/simple routing:
         route: "auto" | "vertical" | "horizontal" | "hv" | "vh" | "orthogonal" | "straight"

    When from_id/to_id are used, "points" is accepted as an alias for "via"
    only if "via" is omitted.  This makes it easy to define a bent arrow whose
    endpoints stay attached to boxes.

    If "via" is provided, it takes priority over route.
    """
    coords = str(coords or _coords_mode(item, data)).lower()
    has_from_id = bool(item.get("from_id"))
    has_to_id = bool(item.get("to_id"))

    raw_points = item.get("points")
    raw_via = item.get("via")

    # New connected-object mode.
    if has_from_id or has_to_id:
        # If an endpoint id is missing, fall back to explicit from/to or,
        # as a convenience, the first/last point in a full path.
        from_fallback = item.get("from")
        to_fallback = item.get("to")
        if isinstance(raw_points, (list, tuple)) and len(raw_points) >= 2 and raw_via is None:
            if from_fallback is None:
                from_fallback = raw_points[0]
            if to_fallback is None:
                to_fallback = raw_points[-1]

        start = _connected_endpoint(
            item,
            data,
            canvas_width,
            canvas_height,
            end="from",
            fallback_point=from_fallback,
        )
        finish = _connected_endpoint(
            item,
            data,
            canvas_width,
            canvas_height,
            end="to",
            fallback_point=to_fallback,
        )

        # Prefer "via"; otherwise, if "points" was supplied with id endpoints,
        # treat points as intermediate waypoints when possible.
        via_raw = raw_via
        if via_raw is None and isinstance(raw_points, (list, tuple)):
            if len(raw_points) > 2:
                via_raw = raw_points[1:-1]
            else:
                via_raw = []

        via_points = []
        if isinstance(via_raw, (list, tuple)):
            for pt in via_raw:
                via_points.append(_resolve_point(pt, canvas_width, canvas_height, coords))

        if via_points:
            points = [start] + via_points + [finish]
        else:
            points = _routed_points(item, start, finish)

    # Old explicit points mode.
    elif isinstance(raw_points, (list, tuple)) and len(raw_points) >= 2:
        points = [_resolve_point(pt, canvas_width, canvas_height, coords) for pt in raw_points]

    # Old straight arrow mode.
    else:
        points = [
            _resolve_point(item.get("from", [0, 0]), canvas_width, canvas_height, coords),
            _resolve_point(item.get("to", [0, 0]), canvas_width, canvas_height, coords),
        ]

    # Remove immediately repeated points so arrowheads have a direction.
    cleaned = []
    for pt in points:
        if not cleaned or pt != cleaned[-1]:
            cleaned.append(pt)
    return cleaned if len(cleaned) >= 2 else [(0.0, 0.0), (0.0, 0.0)]

def _segment_for_end_arrow(points: list[tuple[float, float]]) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return previous-point -> end-point segment, skipping zero-length segments."""
    end = points[-1]
    for prev in reversed(points[:-1]):
        if prev != end:
            return prev, end
    return points[-2], end


def _segment_for_start_arrow(points: list[tuple[float, float]]) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return next-point -> start-point segment, so arrowhead points into start."""
    start = points[0]
    for nxt in points[1:]:
        if nxt != start:
            return nxt, start
    return points[1], start


# NOTE: Earlier versions used Plotly annotation arrows for arrowheads.
# Annotations also draw a solid arrow shaft, which covered dotted/dashed
# arrow bodies.  Arrowheads are now drawn as filled triangle shapes by
# _add_arrowhead_shape(), so there is no annotation shaft.

def _add_band(fig, item, data, canvas_width, canvas_height, selected=False, zoom_scale: float = 1.0):
    item = _with_defaults(item, data)
    item_id = item.get("id", "unknown")
    palette = _palette(data)
    coords = _coords_mode(item, data)
    x = _resolve_x(item.get("x"), canvas_width, coords)
    y = _resolve_y(item.get("y"), canvas_height, coords)
    w = _resolve_w(item.get("w"), canvas_width, coords)
    h = _resolve_h(item.get("h"), canvas_height, coords)
    fill = _resolve_color(item.get("fill", "band_pink"), palette, "#f6cccc")
    opacity = _num(item.get("opacity", 1), 1)
    label = item.get("label", item_id)

    fig.add_shape(
        type="rect",
        x0=x,
        y0=y,
        x1=x + w,
        y1=y + h,
        fillcolor=fill,
        opacity=opacity,
        line=_shape_line(selected, fill, palette, item=item, default_width=0),
        layer="below",
    )

    label_color = _resolve_color(item.get("label_color", item.get("text_color", "text_dark")), palette, "#111111")
    font = _font_options(item, data, default_size=14, default_color=label_color, default_bold=False, zoom_scale=zoom_scale)
    lx, ly = _object_label_xy(
        item,
        x,
        y,
        w,
        h,
        default_rel=(0.0, 0.5),
        default_offset=(12, 0),
    )
    _add_label(
        fig,
        item_id,
        lx,
        ly,
        label,
        color=font["color"],
        size=font["size"],
        bold=font["bold"],
        family=font["family"],
        hover_text=label,
        angle=item.get("label_angle", item.get("angle", 0)),
    )
    _add_click_target(fig, item_id, x + w / 2, y + h / 2, label, size=max(30, min(80, h)))

def _add_box(fig, item, data, canvas_width, canvas_height, selected=False, zoom_scale: float = 1.0):
    item = _with_defaults(item, data)
    item_id = item.get("id", "unknown")
    palette = _palette(data)
    coords = _coords_mode(item, data)
    x = _resolve_x(item.get("x"), canvas_width, coords)
    y = _resolve_y(item.get("y"), canvas_height, coords)
    w = _resolve_w(item.get("w"), canvas_width, coords)
    h = _resolve_h(item.get("h"), canvas_height, coords)
    fill = _resolve_color(item.get("fill", "dune_blue"), palette, "#174cff")
    label = item.get("label", item_id)
    text_color = _resolve_color(item.get("text_color", "white"), palette, "#ffffff")
    font = _font_options(item, data, default_size=13, default_color=text_color, default_bold=True, zoom_scale=zoom_scale)

    fig.add_shape(
        type="rect",
        x0=x,
        y0=y,
        x1=x + w,
        y1=y + h,
        fillcolor=fill,
        opacity=_num(item.get("opacity", 1), 1),
        line=_shape_line(selected, _resolve_color(item.get("line_color", "#333333"), palette, "#333333"), palette, item=item, default_width=1),
        # Keep boxes below text traces. With layer="above", Plotly draws the
        # rectangle over the label, which was why the blue/green box labels disappeared.
        layer="below",
    )

    lx, ly = _object_label_xy(
        item,
        x,
        y,
        w,
        h,
        default_rel=(0.5, 0.5),
        default_offset=(0, 0),
    )
    _add_label(
        fig,
        item_id,
        lx,
        ly,
        label,
        color=font["color"],
        size=font["size"],
        bold=font["bold"],
        family=font["family"],
        hover_text=label,
        angle=item.get("label_angle", item.get("angle", 0)),
    )
    _add_click_target(fig, item_id, x + w / 2, y + h / 2, label, size=max(24, min(60, max(w, h))))

def _add_arrow(fig, item, data, canvas_width, canvas_height, selected=False, zoom_scale: float = 1.0):
    item = _with_defaults(item, data)
    item_id = item.get("id", "unknown")
    palette = _palette(data)
    canvas = data.get("canvas", {}) or {}
    coords = _coords_mode(item, data)

    points = _arrow_points(item, data, canvas_width, canvas_height, coords)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    stroke = _resolve_color(item.get("stroke", "signal_red"), palette, "#ff4b3e")
    sw = _num(item.get("stroke_width", item.get("thickness", item.get("line_width", 2))), 2)
    style = _line_style_name(item)
    label = item.get("label", "")

    stroke_scale = _bool_from_item_or_canvas(item, data, "stroke_scale_with_zoom", False)
    sw_scaled = _scale_value(sw, zoom_scale, stroke_scale, min_value=0.5, max_value=80)
    width = max(sw_scaled, _scale_value(4, zoom_scale, stroke_scale, min_value=4, max_value=80)) if selected else sw_scaled
    color = _resolve_color("highlight_yellow", palette, "#ffd000") if selected else stroke

    # Draw the arrow body explicitly.  This avoids Plotly annotation arrow
    # shafts, which always appear solid and previously covered dotted/dashed
    # Scatter lines.
    if style == "solid":
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": color, "width": width, "dash": "solid"},
                customdata=[item_id for _ in xs],
                hovertemplate=(label or item_id) + "<extra></extra>",
                showlegend=False,
            )
        )
    elif style == "dotted":
        pat_a, pat_b = _dash_pattern_numbers(item)
        dot_size_base = _num(item.get("dot_size", pat_a if pat_a is not None else max(sw * 2.2, 5)), max(sw * 2.2, 5))
        dot_scale = _bool_from_item_or_canvas(item, data, "dot_size_scale_with_zoom", canvas.get("scale_markers_with_zoom", True))
        dot_size = _scale_value(dot_size_base, zoom_scale, dot_scale, min_value=1, max_value=160)
        # If dash_pattern is supplied as "2px,20px", interpret that as
        # dot-size=2 and gap=20, so center-to-center spacing is 22.
        if pat_b is not None:
            spacing_default = (pat_a or dot_size) + pat_b
        else:
            spacing_default = 26
        spacing = _num(item.get("dot_spacing", spacing_default), spacing_default)
        dxs, dys = _points_for_dots(points, spacing)
        fig.add_trace(
            go.Scatter(
                x=dxs,
                y=dys,
                mode="markers",
                marker={"color": color, "size": dot_size, "symbol": "circle"},
                customdata=[item_id for _ in dxs],
                hovertemplate=(label or item_id) + "<extra></extra>",
                showlegend=False,
            )
        )
    elif style == "dashdot":
        pat_a, pat_b = _dash_pattern_numbers(item)
        dash_len = _num(item.get("dash_length", pat_a if pat_a is not None else 18), 18)
        gap = _num(item.get("dash_gap", pat_b if pat_b is not None else 12), 12)
        dxs, dys = _line_segments_for_dashes(points, dash_len, gap)
        fig.add_trace(
            go.Scatter(
                x=dxs,
                y=dys,
                mode="lines",
                line={"color": color, "width": width, "dash": "solid"},
                customdata=[item_id for _ in dxs],
                hovertemplate=(label or item_id) + "<extra></extra>",
                showlegend=False,
            )
        )
        # Add smaller dots in the gaps for a visually clear dash-dot style.
        dot_spacing = dash_len + gap
        dot_offset_points = []
        total = _polyline_length(points)
        d = dash_len + gap / 2.0
        while d < total:
            dot_offset_points.append(_point_at_distance(points, d))
            d += dot_spacing
        if dot_offset_points:
            fig.add_trace(
                go.Scatter(
                    x=[p[0] for p in dot_offset_points],
                    y=[p[1] for p in dot_offset_points],
                    mode="markers",
                    marker={"color": color, "size": _scale_value(max(sw * 1.6, 4), zoom_scale, _bool_from_item_or_canvas(item, data, "dot_size_scale_with_zoom", canvas.get("scale_markers_with_zoom", True)), min_value=1, max_value=160), "symbol": "circle"},
                    customdata=[item_id for _ in dot_offset_points],
                    hovertemplate=(label or item_id) + "<extra></extra>",
                    showlegend=False,
                )
            )
    else:
        # "dashed" and any unrecognized style fall back to explicit dashed.
        pat_a, pat_b = _dash_pattern_numbers(item)
        dash_len = _num(item.get("dash_length", pat_a if pat_a is not None else 18), 18)
        gap = _num(item.get("dash_gap", pat_b if pat_b is not None else 14), 14)
        dxs, dys = _line_segments_for_dashes(points, dash_len, gap)
        fig.add_trace(
            go.Scatter(
                x=dxs,
                y=dys,
                mode="lines",
                line={"color": color, "width": width, "dash": "solid"},
                customdata=[item_id for _ in dxs],
                hovertemplate=(label or item_id) + "<extra></extra>",
                showlegend=False,
            )
        )

    # Backward compatibility: old arrows showed an end arrowhead by default.
    arrow_end = bool(item.get("arrow_end", item.get("arrow", True)))
    arrow_start = bool(item.get("arrow_start", False))
    arrowsize = _num(item.get("arrowsize", item.get("arrow_size", 1.2)), 1.2)

    # Triangle arrowhead geometry.  Separate length/width controls are useful
    # when line thickness and arrowhead size need independent tuning.
    head_length = _num(
        item.get("arrowhead_length", item.get("arrow_length", max(12.0 * arrowsize, width * 4.0))),
        max(12.0 * arrowsize, width * 4.0),
    )
    head_width = _num(
        item.get("arrowhead_width", item.get("arrow_width", max(9.0 * arrowsize, width * 3.0))),
        max(9.0 * arrowsize, width * 3.0),
    )

    arrowhead_scale = _bool_from_item_or_canvas(item, data, "arrowhead_scale_with_zoom", False)
    head_length = _scale_value(head_length, zoom_scale, arrowhead_scale, min_value=1, max_value=500)
    head_width = _scale_value(head_width, zoom_scale, arrowhead_scale, min_value=1, max_value=500)

    if arrow_end:
        tail, head = _segment_for_end_arrow(points)
        _add_arrowhead_shape(fig, tail, head, color, length=head_length, width=head_width)

    if arrow_start:
        tail, head = _segment_for_start_arrow(points)
        _add_arrowhead_shape(fig, tail, head, color, length=head_length, width=head_width)

    # Arrow label position. Explicit label_x/label_y still have highest priority.
    # Otherwise label_position can place the label relative to the arrow path:
    #   center/mid/middle, left/left_side, right/right_side, top/above,
    #   bottom/below, start/from, end/to.
    label_x, label_y = _arrow_label_xy(item, points, canvas_width, canvas_height, coords)

    if label:
        label_color = _resolve_color(item.get("label_color", item.get("text_color", stroke)), palette, stroke)
        font = _font_options(item, data, default_size=12, default_color=label_color, default_bold=False, zoom_scale=zoom_scale)
        _add_label(
            fig,
            item_id,
            label_x,
            label_y,
            label,
            color=font["color"],
            size=font["size"],
            bold=font["bold"],
            family=font["family"],
            hover_text=label,
            angle=item.get("label_angle", item.get("angle", 0)),
        )

    # Click target at center of the polyline bounding box. This is intentionally
    # generous because Plotly lines/dots can be thin and hard to click.
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    _add_click_target(fig, item_id, cx, cy, label or item_id, size=34)


def _render_figure(data: dict, selected_id: str | None = None, relayout_data=None):
    canvas = data.get("canvas", {})
    palette = _palette(data)
    width = int(canvas.get("width", 1600))
    height = int(canvas.get("height", 900))
    bg = _resolve_color(canvas.get("background", "white"), palette, "#ffffff")
    zoom_scale = _zoom_scale_from_relayout(relayout_data, width, height)

    fig = go.Figure()

    # Explicit background rectangle so exported/screenshot views look the same.
    fig.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=width,
        y1=height,
        fillcolor=bg,
        line={"width": 0, "color": bg},
        layer="below",
    )

    # Draw bands first, arrows second, boxes last.
    for wanted_type in ("band", "arrow", "box"):
        for item in data.get("items", []):
            t = item.get("type")
            if t != wanted_type:
                continue
            selected = item.get("id") == selected_id
            if t == "band":
                _add_band(fig, item, data, width, height, selected, zoom_scale=zoom_scale)
            elif t == "box":
                _add_box(fig, item, data, width, height, selected, zoom_scale=zoom_scale)
            elif t == "arrow":
                _add_arrow(fig, item, data, width, height, selected, zoom_scale=zoom_scale)

    fig.update_layout(
        autosize=True,
        margin={"l": 5, "r": 5, "t": 5, "b": 5},
        paper_bgcolor=bg,
        plot_bgcolor=bg,
        hovermode="closest",
        showlegend=False,
        clickmode="event",
        dragmode="pan",
        uirevision="fdvd-layout",
    )
    fig.update_xaxes(
        range=[0, width],
        visible=False,
        fixedrange=False,
        constrain="domain",
    )
    # Reverse Y axis so JSON coordinates behave like screen/SVG coordinates: y=0 at top.
    fig.update_yaxes(
        range=[height, 0],
        visible=False,
        fixedrange=False,
        scaleanchor="x",
        scaleratio=1,
    )
    return fig


def _render_diagram(data: dict, selected_id: str | None = None, relayout_data=None):
    fig = _render_figure(data, selected_id, relayout_data=relayout_data)
    return dcc.Graph(
        id="fdvd-graph",
        figure=fig,
        config={
            "displaylogo": False,
            "scrollZoom": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        },
        style={"width": "100%", "height": "78vh"},
        className="fdvd-graph",
    )


def _clicked_item_id(click_data):
    try:
        points = (click_data or {}).get("points") or []
        if not points:
            return None
        cd = points[0].get("customdata")
        if isinstance(cd, list) and cd:
            return cd[0]
        if isinstance(cd, str):
            return cd
    except Exception:
        logger.exception("Could not parse FD-VD clickData")
    return None


def register_callbacks(app):
    @app.callback(
        Output("fdvd-layout-store", "data"),
        Output("fdvd-json-path", "children"),
        Output("fdvd-status", "children"),
        Output("fdvd-status", "is_open"),
        Output("fdvd-status", "color"),
        Input("fdvd-init", "n_intervals"),
        Input("fdvd-reload-json", "n_clicks"),
        Input("hierarchy-chart-kind", "value"),
        prevent_initial_call=False,
    )
    def load_fdvd_layout(_init, _reload, chart_kind):
        data, path, err = _load_layout(chart_kind)
        if err:
            return (
                data,
                f"{_chart_label(chart_kind)} JSON: {path}",
                f"Could not load {_chart_label(chart_kind)} JSON. Using built-in demo layout. Error: {err}",
                True,
                "warning",
            )
        return data, f"{_chart_label(chart_kind)} JSON: {path}", f"Loaded {_chart_label(chart_kind)} JSON: {path}", True, "success"

    @app.callback(
        Output("fdvd-graph", "figure"),
        Input("fdvd-layout-store", "data"),
        Input("fdvd-selected-id", "data"),
        Input("fdvd-graph", "relayoutData"),
        prevent_initial_call=False,
    )
    def render_fdvd(data, selected_id, relayout_data):
        """
        Render only the Plotly figure.

        The dcc.Graph(id="fdvd-graph") now exists in layout_fdvd.py from the
        beginning, so relayoutData is safe to use as an Input.  This allows the
        callback to detect zoom/pan changes and rescale text/dots/arrowheads
        when those scale-with-zoom options are enabled.
        """
        if not data:
            fig = go.Figure()
            fig.update_layout(
                margin={"l": 5, "r": 5, "t": 5, "b": 5},
                paper_bgcolor="white",
                plot_bgcolor="white",
                showlegend=False,
                annotations=[
                    dict(
                        text="Loading Hierarchy Chart JSON...",
                        x=0.5,
                        y=0.5,
                        xref="paper",
                        yref="paper",
                        showarrow=False,
                        font={"size": 16, "color": "#5d6b82"},
                    )
                ],
            )
            fig.update_xaxes(visible=False)
            fig.update_yaxes(visible=False)
            return fig
        return _render_figure(data, selected_id, relayout_data=relayout_data)

    @app.callback(
        Output("fdvd-selected-id", "data"),
        Output("fdvd-detail-modal", "is_open"),
        Output("fdvd-modal-title", "children"),
        Output("fdvd-modal-body", "children"),
        Input("fdvd-graph", "clickData"),
        Input("fdvd-modal-close", "n_clicks"),
        Input("fdvd-clear-selection", "n_clicks"),
        State("fdvd-layout-store", "data"),
        State("fdvd-detail-modal", "is_open"),
        prevent_initial_call=True,
    )
    def handle_click(click_data, _close, _clear, data, is_open):
        trig = callback_context.triggered_id

        if trig == "fdvd-modal-close":
            return no_update, False, no_update, no_update

        if trig == "fdvd-clear-selection":
            return None, False, no_update, no_update

        if trig == "fdvd-graph":
            item_id = _clicked_item_id(click_data)
            item = _find_item(data or {}, item_id)
            if not item:
                return no_update, is_open, no_update, no_update
            details = _item_details(item)
            title = details.get("title") or item.get("label") or item_id
            return item_id, True, title, _modal_body(details)

        return no_update, is_open, no_update, no_update
