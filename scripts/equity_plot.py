#!/usr/bin/env python3
"""
Equity analysis visualization module.

Generates comprehensive plots for analyzing health equity across subgroups:
- Wait time distributions (KDE plots)
- Equity gaps (P90/P95 differences)
- Utilization impact on equity
- Risk decile analysis
"""
import os
import glob
import json
from typing import List, Dict, Optional
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


def load_runs(out_dir: str = "outputs") -> pd.DataFrame:
    """
    Load all simulation runs from output directory.

    Returns:
        DataFrame with events from all runs, including metadata
    """
    runs = []
    for run_dir in glob.glob(os.path.join(out_dir, "run_seed_*_hash_*")):
        events_path = os.path.join(run_dir, "events.csv")
        manifest_path = os.path.join(run_dir, "manifest.json")

        if not os.path.exists(events_path):
            continue

        df = pd.read_csv(events_path)
        df["run_id"] = os.path.basename(run_dir)

        # Attach metadata
        if os.path.exists(manifest_path):
            meta = json.load(open(manifest_path))
            df["seed"] = meta.get("seed")
            df["scenario"] = meta.get("scenario")
            df["utilization"] = meta.get("utilization")
            df["days"] = meta.get("days")

        runs.append(df)

    if not runs:
        raise ValueError(f"No runs found in {out_dir}")

    return pd.concat(runs, ignore_index=True)


def plot_wait_time_distributions(
    df: pd.DataFrame,
    scenario: str = "hybrid",
    utilization: float = 1.2,
    out_path: str = "outputs/equity_wait_distributions.png"
):
    """
    Plot wait time distributions by subgroup using KDE.

    Shows kernel density estimates for wait times, highlighting
    differences between demographic subgroups.
    """
    # Filter to attended patients in specified scenario/utilization
    mask = (
        (df["attended"] == True) &
        (df["scenario"] == scenario) &
        (df["utilization"] == utilization)
    )
    plot_df = df[mask].copy()

    if len(plot_df) == 0:
        print(f"No data for scenario={scenario}, utilization={utilization}")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        f"Wait Time Distributions by Subgroup\n{scenario} scenario, utilization={utilization}",
        fontsize=14,
        fontweight='bold'
    )

    # 1. Overall KDE by subgroup
    ax = axes[0, 0]
    for subgroup in sorted(plot_df["subgroup"].unique()):
        sub_data = plot_df[plot_df["subgroup"] == subgroup]["wait_days"]
        sub_data.plot.kde(ax=ax, label=f"Subgroup {subgroup}", linewidth=2)
    ax.set_xlabel("Wait Days")
    ax.set_ylabel("Density")
    ax.set_title("Overall Wait Time Distribution")
    ax.legend()
    ax.set_xlim(0, plot_df["wait_days"].quantile(0.99))

    # 2. Urgent vs Routine by subgroup
    ax = axes[0, 1]
    for subgroup in sorted(plot_df["subgroup"].unique()):
        for pclass in ["urgent", "routine"]:
            mask = (plot_df["subgroup"] == subgroup) & (plot_df["pclass"] == pclass)
            data = plot_df[mask]["wait_days"]
            if len(data) > 1:
                data.plot.kde(
                    ax=ax,
                    label=f"{subgroup}-{pclass}",
                    linewidth=2,
                    linestyle='-' if pclass == 'urgent' else '--'
                )
    ax.set_xlabel("Wait Days")
    ax.set_ylabel("Density")
    ax.set_title("By Priority Class")
    ax.legend()
    ax.set_xlim(0, plot_df["wait_days"].quantile(0.99))

    # 3. Box plot comparison
    ax = axes[1, 0]
    plot_df.boxplot(column="wait_days", by="subgroup", ax=ax)
    ax.set_xlabel("Subgroup")
    ax.set_ylabel("Wait Days")
    ax.set_title("Wait Time Box Plots")
    plt.sca(ax)
    plt.xticks(rotation=0)

    # 4. Cumulative distribution
    ax = axes[1, 1]
    for subgroup in sorted(plot_df["subgroup"].unique()):
        sub_data = plot_df[plot_df["subgroup"] == subgroup]["wait_days"].sort_values()
        cumulative = np.arange(1, len(sub_data) + 1) / len(sub_data)
        ax.plot(sub_data, cumulative, label=f"Subgroup {subgroup}", linewidth=2)
    ax.set_xlabel("Wait Days")
    ax.set_ylabel("Cumulative Probability")
    ax.set_title("Cumulative Distribution Function")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, plot_df["wait_days"].quantile(0.99))

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"Saved wait time distributions to {out_path}")
    plt.close()


def plot_equity_gaps(
    out_dir: str = "outputs",
    out_path: str = "outputs/equity_gaps.png"
):
    """
    Plot equity gaps (P90/P95 differences) across scenarios and utilizations.

    Shows how equity gaps evolve under different system loads and interventions.
    """
    # Load gaps from all runs
    gap_data = []
    for run_dir in glob.glob(os.path.join(out_dir, "run_seed_*_hash_*")):
        gaps_path = os.path.join(run_dir, "gaps.csv")
        manifest_path = os.path.join(run_dir, "manifest.json")

        if not (os.path.exists(gaps_path) and os.path.exists(manifest_path)):
            continue

        gaps = pd.read_csv(gaps_path)
        meta = json.load(open(manifest_path))

        for _, row in gaps.iterrows():
            gap_data.append({
                "metric": row["metric"],
                "value": row["value"],
                "scenario": meta.get("scenario"),
                "utilization": meta.get("utilization"),
                "seed": meta.get("seed")
            })

    if not gap_data:
        print(f"No gap data found in {out_dir}")
        return

    gap_df = pd.DataFrame(gap_data)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Equity Gaps (B - A) Across Scenarios", fontsize=14, fontweight='bold')

    # 1. P90 gaps
    ax = axes[0]
    p90_data = gap_df[gap_df["metric"] == "P90_gap_B_minus_A"]
    if len(p90_data) > 0:
        for scenario in sorted(p90_data["scenario"].unique()):
            scenario_data = p90_data[p90_data["scenario"] == scenario]
            grouped = scenario_data.groupby("utilization")["value"].agg(["mean", "std", "count"])
            grouped["se"] = grouped["std"] / np.sqrt(grouped["count"])

            ax.errorbar(
                grouped.index,
                grouped["mean"],
                yerr=1.96 * grouped["se"],
                marker='o',
                label=scenario,
                linewidth=2,
                capsize=5
            )
        ax.axhline(0, color='black', linestyle='--', alpha=0.3, label='No gap')
        ax.set_xlabel("Utilization")
        ax.set_ylabel("P90 Gap (days)")
        ax.set_title("P90 Wait Time Gap (B - A)")
        ax.legend()
        ax.grid(True, alpha=0.3)

    # 2. P95 gaps
    ax = axes[1]
    p95_data = gap_df[gap_df["metric"] == "P95_gap_B_minus_A"]
    if len(p95_data) > 0:
        for scenario in sorted(p95_data["scenario"].unique()):
            scenario_data = p95_data[p95_data["scenario"] == scenario]
            grouped = scenario_data.groupby("utilization")["value"].agg(["mean", "std", "count"])
            grouped["se"] = grouped["std"] / np.sqrt(grouped["count"])

            ax.errorbar(
                grouped.index,
                grouped["mean"],
                yerr=1.96 * grouped["se"],
                marker='o',
                label=scenario,
                linewidth=2,
                capsize=5
            )
        ax.axhline(0, color='black', linestyle='--', alpha=0.3, label='No gap')
        ax.set_xlabel("Utilization")
        ax.set_ylabel("P95 Gap (days)")
        ax.set_title("P95 Wait Time Gap (B - A)")
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"Saved equity gaps to {out_path}")
    plt.close()


def plot_utilization_impact(
    out_dir: str = "outputs",
    scenario: str = "hybrid",
    out_path: str = "outputs/utilization_impact.png"
):
    """
    Plot how system utilization impacts wait times by subgroup.

    Shows mean and percentile wait times as a function of utilization.
    """
    # Load overall summaries
    summary_data = []
    for run_dir in glob.glob(os.path.join(out_dir, "run_seed_*_hash_*")):
        overall_path = os.path.join(run_dir, "overall.csv")
        manifest_path = os.path.join(run_dir, "manifest.json")

        if not (os.path.exists(overall_path) and os.path.exists(manifest_path)):
            continue

        overall = pd.read_csv(overall_path)
        meta = json.load(open(manifest_path))

        if meta.get("scenario") != scenario:
            continue

        for _, row in overall.iterrows():
            summary_data.append({
                "subgroup": row["subgroup"],
                "mean_wait": row["mean_wait"],
                "P90": row.get("P90"),
                "P95": row.get("P95"),
                "utilization": meta.get("utilization"),
                "seed": meta.get("seed")
            })

    if not summary_data:
        print(f"No summary data found for scenario={scenario}")
        return

    df = pd.DataFrame(summary_data)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(
        f"Utilization Impact on Wait Times ({scenario} scenario)",
        fontsize=14,
        fontweight='bold'
    )

    metrics = [("mean_wait", "Mean Wait (days)"), ("P90", "P90 (days)"), ("P95", "P95 (days)")]

    for idx, (metric, ylabel) in enumerate(metrics):
        ax = axes[idx]
        for subgroup in sorted(df["subgroup"].unique()):
            sub_data = df[df["subgroup"] == subgroup]
            grouped = sub_data.groupby("utilization")[metric].agg(["mean", "std", "count"])
            grouped["se"] = grouped["std"] / np.sqrt(grouped["count"])

            ax.errorbar(
                grouped.index,
                grouped["mean"],
                yerr=1.96 * grouped["se"],
                marker='o',
                label=f"Subgroup {subgroup}",
                linewidth=2,
                capsize=5
            )

        ax.set_xlabel("Utilization")
        ax.set_ylabel(ylabel)
        ax.set_title(ylabel)
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"Saved utilization impact plot to {out_path}")
    plt.close()


def plot_risk_deciles(
    out_dir: str = "outputs",
    scenario: str = "hybrid",
    utilization: float = 1.2,
    out_path: str = "outputs/risk_deciles.png"
):
    """
    Plot wait times by predicted risk decile and subgroup.

    Shows whether high-risk patients receive prioritized care.
    """
    # Load risk decile data
    decile_data = []
    for run_dir in glob.glob(os.path.join(out_dir, "run_seed_*_hash_*")):
        deciles_path = os.path.join(run_dir, "risk_deciles.csv")
        manifest_path = os.path.join(run_dir, "manifest.json")

        if not (os.path.exists(deciles_path) and os.path.exists(manifest_path)):
            continue

        meta = json.load(open(manifest_path))
        if meta.get("scenario") != scenario or meta.get("utilization") != utilization:
            continue

        deciles = pd.read_csv(deciles_path)
        deciles["seed"] = meta.get("seed")
        decile_data.append(deciles)

    if not decile_data:
        print(f"No decile data found for scenario={scenario}, utilization={utilization}")
        return

    df = pd.concat(decile_data, ignore_index=True)

    fig, ax = plt.subplots(figsize=(12, 7))

    for subgroup in sorted(df["subgroup"].unique()):
        sub_data = df[df["subgroup"] == subgroup]
        grouped = sub_data.groupby("risk_decile")["mean_wait"].agg(["mean", "std", "count"])
        grouped["se"] = grouped["std"] / np.sqrt(grouped["count"])

        ax.errorbar(
            grouped.index,
            grouped["mean"],
            yerr=1.96 * grouped["se"],
            marker='o',
            label=f"Subgroup {subgroup}",
            linewidth=2,
            capsize=5
        )

    ax.set_xlabel("Predicted Risk Decile (0=lowest, 9=highest)")
    ax.set_ylabel("Mean Wait Days")
    ax.set_title(
        f"Wait Time by Risk Decile\n{scenario} scenario, utilization={utilization}",
        fontweight='bold'
    )
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"Saved risk decile plot to {out_path}")
    plt.close()


def generate_all_plots(
    out_dir: str = "outputs",
    scenario: str = "hybrid",
    utilization: float = 1.2
):
    """
    Generate all equity analysis plots.

    Args:
        out_dir: Directory containing simulation outputs
        scenario: Scenario to analyze
        utilization: Utilization level to analyze
    """
    print("Generating equity analysis plots...")
    print(f"Output directory: {out_dir}")
    print(f"Scenario: {scenario}, Utilization: {utilization}")

    os.makedirs(out_dir, exist_ok=True)

    # Load data once for efficiency
    try:
        df = load_runs(out_dir)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Generate all plots
    plot_wait_time_distributions(df, scenario, utilization)
    plot_equity_gaps(out_dir)
    plot_utilization_impact(out_dir, scenario)
    plot_risk_deciles(out_dir, scenario, utilization)

    print("\nAll plots generated successfully!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate equity analysis visualizations"
    )
    parser.add_argument(
        "--out-dir",
        default="outputs",
        help="Directory containing simulation outputs"
    )
    parser.add_argument(
        "--scenario",
        default="hybrid",
        help="Scenario to analyze"
    )
    parser.add_argument(
        "--utilization",
        type=float,
        default=1.2,
        help="Utilization level to analyze"
    )

    args = parser.parse_args()
    generate_all_plots(args.out_dir, args.scenario, args.utilization)
