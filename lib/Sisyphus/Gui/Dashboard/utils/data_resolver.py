import pickle
import pandas as pd

def load_df_from_store(store):
    if not store or "path" not in store:
        return pd.DataFrame()

    with open(store["path"], "rb") as f:
        return pickle.load(f)


def apply_row_indices(df, indices):
    if not indices:
        return df.iloc[0:0]  # empty df
    return df.iloc[indices]
