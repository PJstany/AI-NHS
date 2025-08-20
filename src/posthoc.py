from __future__ import annotations
import pandas as pd

def override_rates_by_group(df_overrides: pd.DataFrame, df_events: pd.DataFrame) -> pd.DataFrame:
    # Join to get subgroup/decile context if needed later
    return df_overrides.groupby(["day"]).size().reset_index(name="overrides")

