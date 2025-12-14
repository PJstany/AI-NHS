from __future__ import annotations
import os, json
from typing import Dict, List
import numpy as np
import pandas as pd
import polars as pl

from .metrics import kpi_flags, equity_summary, risk_deciles, high_risk_same_day_share

def summarize(df: pd.DataFrame, thresholds: Dict[str, int], warmup_days: int = 0, compute_ci: bool = False) -> Dict:
    """
    Summarize simulation results with optional bootstrap confidence intervals.
    FIXED: Now includes ALL patients (attended + reneged) for equity analysis.

    Args:
        df: Event dataframe from simulation
        thresholds: Dictionary of threshold days for breach calculations
        warmup_days: Number of initial days to exclude from analysis
        compute_ci: If True, compute bootstrap CIs for wait time metrics (requires multiple patients)

    Returns:
        Dictionary with 'overall', 'gaps', and 'deciles' dataframes
    """
    # Apply warm-up filter if requested
    if warmup_days and "arrival_day" in df.columns:
        df = df[df["arrival_day"] >= warmup_days].copy()
    df = kpi_flags(df, thresholds["same_day"], thresholds["within_3d"], thresholds["within_14d"])
    
    # FIXED: Include ALL patients (attended + reneged) for equity summary
    # This captures the "invisible victims" who abandoned the queue
    overall, gaps = equity_summary(df.copy())
    
    # For deciles and high-risk share, still use attended patients only
    attended_df = df[df["attended"] == True].copy()
    deciles = risk_deciles(attended_df)
    high_share = high_risk_same_day_share(attended_df)

    # Add bootstrap CIs if requested
    if compute_ci:
        overall = add_bootstrap_cis(df.copy(), overall)

    return {
        "overall": overall.assign(high_risk_same_day_share=high_share),
        "gaps": gaps,
        "deciles": deciles
    }

def bootstrap_ci(values: np.ndarray, reps: int = 1000, alpha: float = 0.05, rng=None):
    """
    Compute bootstrap confidence interval for the mean.

    Args:
        values: Array of values to bootstrap
        reps: Number of bootstrap resamples
        alpha: Significance level (default 0.05 for 95% CI)
        rng: Random number generator (for reproducibility)

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if rng is None:
        rng = np.random.default_rng(123)
    n = len(values)
    if n < 2:
        return (float(values[0]), float(values[0])) if n == 1 else (np.nan, np.nan)
    samples = [np.mean(rng.choice(values, size=n, replace=True)) for _ in range(reps)]
    lo = np.quantile(samples, alpha/2)
    hi = np.quantile(samples, 1 - alpha/2)
    return float(lo), float(hi)

def add_bootstrap_cis(df: pd.DataFrame, overall: pd.DataFrame, reps: int = 1000) -> pd.DataFrame:
    """
    Add bootstrap confidence intervals to overall summary statistics.

    Args:
        df: Event dataframe (filtered to attended=True)
        overall: Summary statistics dataframe by subgroup
        reps: Number of bootstrap resamples

    Returns:
        Enhanced overall dataframe with CI columns
    """
    rng = np.random.default_rng(42)
    ci_rows = []

    for idx, row in overall.iterrows():
        subgroup = row["subgroup"]
        subdf = df[df["subgroup"] == subgroup]
        wait_values = subdf["wait_days"].values

        # Compute CIs for mean wait time
        if len(wait_values) >= 2:
            mean_lo, mean_hi = bootstrap_ci(wait_values, reps=reps, rng=rng)
        else:
            mean_lo, mean_hi = np.nan, np.nan

        ci_rows.append({
            "subgroup": subgroup,
            "mean_wait_ci_lo": mean_lo,
            "mean_wait_ci_hi": mean_hi
        })

    ci_df = pd.DataFrame(ci_rows)
    return overall.merge(ci_df, on="subgroup", how="left")

def save_summary(run_dir: str, summary: Dict):
    os.makedirs(run_dir, exist_ok=True)
    summary["overall"].to_csv(os.path.join(run_dir, "overall.csv"), index=False)
    summary["gaps"].to_csv(os.path.join(run_dir, "gaps.csv"), index=False)
    summary["deciles"].to_csv(os.path.join(run_dir, "risk_deciles.csv"), index=False)
