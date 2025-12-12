import json, pandas as pd, numpy as np
from Sisyphus.RestApiV1 import get_hwitem, get_hwitem_test

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

# Recursive flattener
def flatten_dict(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            # Recurse into nested dicts
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            if all(isinstance(i, dict) for i in v):
                # Flatten list of dicts: index them
                for idx, i in enumerate(v):
                    items.extend(flatten_dict(i, f"{new_key}{sep}{idx}", sep=sep).items())
            else:
                # Keep list as-is (may be numeric data)
                items.append((new_key, v))
        else:
            items.append((new_key, v))
    return dict(items)

# Load and flatten JSON
def load_data(data) -> pd.DataFrame:

    # If input is a JSON string, parse it
    if isinstance(data, str):
        data = json.loads(data)
    if not data:
        raise ValueError("No data provided or could not parse JSON.")

    # If data is a list of dicts, flatten each
    if isinstance(data, list):
        flat_data = [flatten_dict(record) if isinstance(record, dict) else record for record in data]
    elif isinstance(data, dict):
        flat_data = [flatten_dict(data)]
    else:
        raise ValueError("Data must be a dict or list of dicts")

    #-----------------------------
    for record in flat_data:         # flat_data is a list of dicts
        # find all list-valued keys with more than one element
        list_keys = [k for k, v in record.items() if isinstance(v, list) and len(v) > 1]
        if list_keys:
            for k in list_keys:
                del record[k]          # remove from original dict
    #-----------------------------
    #expanded_records = []
    #for record in flat_data:
    #    list_keys = [k for k, v in record.items() if isinstance(v, list)]
    #    if not list_keys:
    #        expanded_records.append(record)
    #        continue
    #    max_len = max(len(record[k]) for k in list_keys)
    #    for i in range(max_len):
    #        new_row = {}
    #        for k, v in record.items():
    #            if isinstance(v, list):
    #                new_row[k] = v[i] if i < len(v) else None
    #            else:
    #                new_row[k]=v
    #        expanded_records.append(new_row)
    #flat_data = expanded_records
    #-----------------------------
    
    df = pd.DataFrame(flat_data)

    # --- Clean column names ---
    df.columns = [str(c).replace(".", "_") for c in df.columns]
    
    return df

# GET Test DATA from each PIDs
def GETTestLog(myDATA, testtype_string):

    eachPID = myDATA["part_id"]

    # Get item and test info
    resp_item = get_hwitem(eachPID)
    #item_data = resp_item["data"]
    item_data = resp_item.get("data", {})

    resp_test = get_hwitem_test(eachPID,testtype_string)
    test_data = {}
    
    if resp_test.get("data"):
        test_data = resp_test["data"][0]  

    # Initialize combined row
    combined = {}

    # Prefix keys to avoid collisions
    if isinstance(item_data, dict):
        for k, v in item_data.items():
            combined[f"ITEM: {k}"] = v
    if isinstance(test_data, dict):
        for k, v in test_data.items():
            combined[f"TEST: {k}"] = v
        
    return combined
