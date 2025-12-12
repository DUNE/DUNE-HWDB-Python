import re
import pandas as pd

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)


def split_path(path: str):
    """Split a path on '.' or '/' and drop empties."""
    return [p for p in re.split(r"[./]", path) if p]


def find_array_paths(schema_fields):
    """
    From schema paths like
      'test_data.DATA[*].SiPM[*].Counts'
    collect array paths:
      'test_data.DATA[*]', 'test_data.DATA[*].SiPM[*]'

    Returned list is sorted outer → inner so that we always
    set indices for outer arrays before inner ones.
    """
    array_paths = set()

    for f in schema_fields:
        parts = re.split(r"[./]", f)
        cur = ""
        for seg in parts:
            if not seg:
                continue
            cur = f"{cur}.{seg}" if cur else seg
            if seg.endswith("[]") or seg.endswith("[*]"):
                array_paths.add(cur)

    def array_depth(path: str) -> int:
        # count both syntaxes: '[]' and '[*]'
        return path.count("[]") + path.count("[*]")

    # outer arrays (depth=1) before inner (depth=2, 3, …)
    return sorted(array_paths, key=array_depth)


def get_array_list(entry, array_path, idx_map):
    """
    Given a JSON entry and an array_path like 'test_data.DATA[*]'
    or 'test_data.DATA[*].SiPM[*]', return the list at that node,
    respecting already-chosen indices for outer arrays.
    """
    parts = re.split(r"[./]", array_path)
    v = entry
    cur = ""
    for seg in parts:
        if not seg:
            continue
        cur = f"{cur}.{seg}" if cur else seg

        if seg.endswith("[]") or seg.endswith("[*]"):
            base = seg.replace("[]", "").replace("[*]", "")

            if not isinstance(v, dict):
                logger.debug(f"[DL] get_array_list: {cur}: parent not dict")
                return []

            lst = v.get(base)
            if not isinstance(lst, list):
                logger.debug(f"[DL] get_array_list: {cur}: not a list")
                return []

            if cur == array_path:
                # This is the array we want to expand at this stage
                return lst

            # Otherwise this is an *outer* array we've already indexed
            idx = idx_map.get(cur)
            if idx is None or idx < 0 or idx >= len(lst):
                logger.debug(f"[DL] get_array_list: {cur}: bad index {idx}")
                return []
            v = lst[idx]

        else:
            # normal dict hop
            if isinstance(v, dict):
                v = v.get(seg)
            else:
                logger.debug(f"[DL] get_array_list: {cur}: parent not dict (scalar hop)")
                return []
    return []


def extract_field(entry, path, idx_map):
    """
    Extract a scalar value from entry following a schema path like:
      'test_data.DATA[*].SiPM[*].Counts'
    using indices stored in idx_map for each array path.
    """
    parts = re.split(r"[./]", path)
    v = entry
    cur = ""
    for seg in parts:
        if not seg:
            continue
        cur = f"{cur}.{seg}" if cur else seg

        if seg.endswith("[]") or seg.endswith("[*]"):
            base = seg.replace("[]", "").replace("[*]", "")

            if not isinstance(v, dict):
                return None

            lst = v.get(base)
            if not isinstance(lst, list):
                return None

            idx = idx_map.get(cur)
            if idx is None or idx < 0 or idx >= len(lst):
                return None

            v = lst[idx]

        else:
            # normal dict key
            if isinstance(v, dict):
                v = v.get(seg)
            else:
                return None
    return v


def clean_col_name(path: str) -> str:
    """
    Return only the leaf field name from a full schema path.
    Example:
      'test_data.DATA[*].SiPM[*].Comment' → 'Comment'
    """
    parts = re.split(r"[./]", path)
    leaf = parts[-1] if parts else path
    leaf = leaf.replace("[*]", "").replace("[]", "")

    return (
        leaf.replace(" ", "_")
        .replace("-", "_")
    )


def build_csv_rows_for_entry(entry, pid, fields, array_paths):
    """
    Given a single HWDB test entry (dict), PID string, selected schema
    fields, and precomputed array_paths, return a *list* of flattened
    row dicts (one per combination of array indices).
    """
    # Each state is (row_dict, idx_map)
    # idx_map maps array_path -> index (e.g. 'test_data.DATA[*]': 0)
    states = [({"External_ID": pid}, {})]

    # Expand along each array path
    for apath in array_paths:
        new_states = []
        for row, idx_map in states:
            lst = get_array_list(entry, apath, idx_map)
            if not lst:
                # No list at this level: carry row unchanged
                new_states.append((row, idx_map.copy()))
            else:
                for i in range(len(lst)):
                    new_row = row.copy()
                    new_idx = idx_map.copy()
                    new_idx[apath] = i
                    new_states.append((new_row, new_idx))
        states = new_states

    logger.info(
        f"[DL] PID={pid} expanded into {len(states)} row(s) with array_paths={array_paths}"
    )

    # Fill fields
    rows = []
    for row, idx_map in states:
        for f in fields:
            cname = clean_col_name(f)
            val = extract_field(entry, f, idx_map)
            row[cname] = val
        rows.append(row)

    return rows
