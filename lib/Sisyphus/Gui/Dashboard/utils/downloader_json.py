import re
import json

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)


def normalize_path(path: str):
    """
    'test_data.DATA[*].SiPM[*].I_Mean_High'
    -> ['test_data', 'DATA', 'SiPM', 'I_Mean_High']
    """
    parts = re.split(r"[./]", path)
    cleaned = []
    for seg in parts:
        if not seg:
            continue
        seg = seg.replace("[]", "").replace("[*]", "")
        cleaned.append(seg)
    return cleaned


def build_allowed_tree(field_paths):
    """
    Build a tree describing which keys (and subkeys)
    we want to keep from the original JSON.

    Example for fields like:
      test_data.DATA[*].Date
      test_data.DATA[*].SiPM[*].I_Mean_High

    we get something like:
      {
        'test_data': {
          'DATA': {
            'Date': None,
            'SiPM': {
              'I_Mean_High': None,
              'SiPM_Location': None,
              ...
            }
          }
        }
      }
    """
    root = {}
    for path in field_paths:
        parts = normalize_path(path)
        node = root
        for i, seg in enumerate(parts):
            last = (i == len(parts) - 1)
            if seg not in node:
                node[seg] = None if last else {}
            else:
                # If it was previously a leaf (None) and now
                # we need children, promote it to dict
                if not last and node[seg] is None:
                    node[seg] = {}
            if not last:
                node = node[seg]
    return root


def prune(node, allowed):
    """
    Recursively keep only the keys / subkeys
    described by 'allowed'.

    - allowed is None  -> keep node as-is (leaf)
    - allowed is dict  -> keep only those children
    """
    if allowed is None:
        # Leaf: keep full value (scalar or list/dict)
        return node

    if isinstance(node, dict):
        out = {}
        for key, sub in allowed.items():
            if key in node:
                out[key] = prune(node[key], sub)
        return out

    if isinstance(node, list):
        # Same schema applies to every element
        return [prune(elem, allowed) for elem in node]

    # Scalar but allowed is dict (should be rare) -> just return
    return node


def build_json_for_entry(entry, pid, allowed_tree):
    """
    Given a full HWDB entry and the allowed_tree describing which
    branches to keep, return a nested object like:

      {
        "External_ID": PID,
        "test_data": {
          "DATA": [
            ...
          ]
        }
      }
    """
    obj = {"External_ID": pid}
    pruned = prune(entry, allowed_tree)
    if isinstance(pruned, dict):
        obj.update(pruned)
    return obj
