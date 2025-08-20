from __future__ import annotations
import os
import pandas as pd

def main_table(run_dir: str) -> pd.DataFrame:
    overall = pd.read_csv(os.path.join(run_dir, "overall.csv"))
    gaps = pd.read_csv(os.path.join(run_dir, "gaps.csv"))
    tbl = overall.pivot_table(index="subgroup", values=["mean_wait","median_wait","P90","P95","same_day_rate","within_3d_rate","within_14d_rate"])
    return tbl.reset_index()

