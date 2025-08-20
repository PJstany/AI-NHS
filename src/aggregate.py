from __future__ import annotations
import os, json
from typing import Dict, List
import numpy as np
import pandas as pd
import polars as pl

from .metrics import kpi_flags, equity_summary, risk_deciles, high_risk_same_day_share

def summarize(df: pd.DataFrame, thresholds: Dict[str, int]) -> Dict:
    df = kpi_flags(df, thresholds["same_day"], thresholds["within_3d"], thresholds["within_14d"])
    overall, gaps = equity_summary(df[df["attended"] == True].copy())
    deciles = risk_deciles(df[df["attended"] == True].copy())
    # Add after building 'overall'
    # (This is a placeholder hook; you can extend later to compute CIs across runs.)
    high_share = high_risk_same_day_share(df[df["attended"] == True].copy())
    return {
        "overall": overall.assign(high_risk_same_day_share=high_share),
        "gaps": gaps,
        "deciles": deciles
    }

def bootstrap_ci(values: np.ndarray, reps: int = 1000, alpha: float = 0.05, rng=None):
    if rng is None:
        rng = np.random.default_rng(123)
    n = len(values)
    samples = [np.mean(rng.choice(values, size=n, replace=True)) for _ in range(reps)]
    lo = np.quantile(samples, alpha/2)
    hi = np.quantile(samples, 1 - alpha/2)
    return float(lo), float(hi)

def save_summary(run_dir: str, summary: Dict):
    os.makedirs(run_dir, exist_ok=True)
    summary["overall"].to_csv(os.path.join(run_dir, "overall.csv"), index=False)
    summary["gaps"].to_csv(os.path.join(run_dir, "gaps.csv"), index=False)
    summary["deciles"].to_csv(os.path.join(run_dir, "risk_deciles.csv"), index=False)
