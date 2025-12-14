from __future__ import annotations
import numpy as np
import pandas as pd

def quantiles(series: pd.Series, qs=(0.9, 0.95)):
    return {f"P{int(q*100)}": float(series.quantile(q)) for q in qs}

def kpi_flags(df: pd.DataFrame, same_day:int, within_3:int, within_14:int)->pd.DataFrame:
    out = df.copy()
    out["breach_same_day"] = (out["wait_days"] > same_day)
    out["breach_3d"] = (out["wait_days"] > within_3)
    out["breach_14d"] = (out["wait_days"] > within_14)
    return out

def risk_deciles(df: pd.DataFrame, by: str = "subgroup") -> pd.DataFrame:
    df = df.copy()
    df["risk_decile"] = pd.qcut(df["pred_risk"], 10, labels=False, duplicates="drop")
    g = df.groupby([by, "risk_decile"])
    return g["wait_days"].mean().reset_index(name="mean_wait")

def equity_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute equity summary statistics by subgroup.
    FIXED: Now includes abandonment_rate to track reneged patients.

    Args:
        df: DataFrame with patient events (includes reneged patients)

    Returns:
        Tuple of (overall_summary, equity_gaps) DataFrames
    """
    # Handle empty dataframe
    if len(df) == 0 or "subgroup" not in df.columns:
        empty_overall = pd.DataFrame(columns=[
            "subgroup", "n", "n_reneged", "abandonment_rate", "mean_wait", "median_wait", 
            "P90", "P95", "urgent_breach_rate", "same_day_rate", "within_3d_rate", "within_14d_rate"
        ])
        empty_gaps = pd.DataFrame(columns=["metric", "value"])
        return empty_overall, empty_gaps

    # Ensure reneged column exists
    if "reneged" not in df.columns:
        df = df.copy()
        df["reneged"] = False

    # Overall by subgroup
    rows = []
    for g, gdf in df.groupby("subgroup"):
        n_total = len(gdf)
        n_reneged = int(gdf["reneged"].sum())
        abandonment_rate = n_reneged / n_total if n_total > 0 else 0.0
        
        # For wait stats, include ALL patients (survivors + reneged)
        q = quantiles(gdf["wait_days"])
        
        # For access rates, only count non-reneged patients
        seen = gdf[~gdf["reneged"]]
        n_seen = len(seen)
        
        rows.append({
            "subgroup": g,
            "n": n_total,
            "n_reneged": n_reneged,
            "abandonment_rate": float(abandonment_rate),
            "mean_wait": float(gdf["wait_days"].mean()),
            "median_wait": float(gdf["wait_days"].median()),
            **q,
            "urgent_breach_rate": float((gdf["pclass"].eq("urgent") & gdf["breach_3d"]).mean()),
            "same_day_rate": float((seen["wait_days"] <= 0).mean()) if n_seen > 0 else 0.0,
            "within_3d_rate": float((seen["wait_days"] <= 3).mean()) if n_seen > 0 else 0.0,
            "within_14d_rate": float((seen["wait_days"] <= 14).mean()) if n_seen > 0 else 0.0,
        })
    out = pd.DataFrame(rows)
    
    # P90/P95 gaps + abandonment gap
    if len(out) > 0 and set(out["subgroup"]) >= {"A", "B"}:
        a = out.set_index("subgroup").loc["A"]
        b = out.set_index("subgroup").loc["B"]
        gap = pd.DataFrame([{
            "metric": "P90_gap_B_minus_A",
            "value": float(b["P90"] - a["P90"])
        }, {
            "metric": "P95_gap_B_minus_A",
            "value": float(b["P95"] - a["P95"])
        }, {
            "metric": "abandonment_gap_B_minus_A",
            "value": float(b["abandonment_rate"] - a["abandonment_rate"])
        }])
    else:
        gap = pd.DataFrame(columns=["metric", "value"])
    return out, gap

def high_risk_same_day_share(df: pd.DataFrame, top_frac: float = 0.1) -> float:
    """
    Compute fraction of high-risk patients seen same-day.

    Args:
        df: DataFrame with patient events (should be filtered to attended=True)
        top_frac: Fraction defining "high risk" (default: top 10%)

    Returns:
        Fraction of high-risk patients with wait_days <= 0
    """
    if len(df) == 0 or "pred_risk" not in df.columns:
        return 0.0

    cutoff = df["pred_risk"].quantile(1 - top_frac)
    top = df[df["pred_risk"] >= cutoff]

    if len(top) == 0:
        return 0.0

    return float((top["wait_days"] <= 0).mean())
