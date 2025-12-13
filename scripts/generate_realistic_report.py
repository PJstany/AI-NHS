#!/usr/bin/env python
"""Generate comprehensive analysis report for realistic NHS GP simulation."""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

OUTPUT_DIR = Path("outputs_realistic")
FIGURES_DIR = OUTPUT_DIR / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

SCENARIOS = ["baseline", "ai_only", "imperfect_ai", "hybrid"]
SCENARIO_LABELS = {
    "baseline": "Baseline\n(No AI)",
    "ai_only": "AI Only",
    "imperfect_ai": "Imperfect AI",
    "hybrid": "Hybrid\n(AI + Override)"
}

def load_aggregate_data():
    """Load aggregate data from all scenarios."""
    dfs = []
    for scenario in SCENARIOS:
        path = OUTPUT_DIR / scenario / "aggregate_with_ci.csv"
        if path.exists():
            df = pd.read_csv(path)
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def load_sample_events(scenario, seed=301):
    """Load sample events from a specific run."""
    pattern = f"run_seed_{seed}_hash_*"
    runs = list((OUTPUT_DIR / scenario).glob(pattern))
    if runs:
        events_path = runs[0] / "events.csv"
        if events_path.exists():
            return pd.read_csv(events_path)
    return pd.DataFrame()

def plot_wait_times_comparison(df):
    """Plot mean wait times comparison across scenarios and utilization."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    utils = [1.0, 1.1, 1.2]
    colors = {'A': '#2ecc71', 'B': '#e74c3c'}

    for idx, util in enumerate(utils):
        ax = axes[idx]
        subset = df[df['utilization'] == util]

        x = np.arange(len(SCENARIOS))
        width = 0.35

        for i, scenario in enumerate(SCENARIOS):
            scenario_data = subset[subset['scenario'] == scenario]
            if len(scenario_data) == 0:
                continue

            a_data = scenario_data[scenario_data['subgroup'] == 'A']
            b_data = scenario_data[scenario_data['subgroup'] == 'B']

            if len(a_data) > 0:
                ax.bar(i - width/2, a_data['mean_wait_avg'].values[0], width,
                      color=colors['A'], alpha=0.8,
                      yerr=[[a_data['mean_wait_avg'].values[0] - a_data['mean_wait_ci_lo'].values[0]],
                            [a_data['mean_wait_ci_hi'].values[0] - a_data['mean_wait_avg'].values[0]]],
                      capsize=3, label='Subgroup A' if i == 0 else '')

            if len(b_data) > 0:
                ax.bar(i + width/2, b_data['mean_wait_avg'].values[0], width,
                      color=colors['B'], alpha=0.8,
                      yerr=[[b_data['mean_wait_avg'].values[0] - b_data['mean_wait_ci_lo'].values[0]],
                            [b_data['mean_wait_ci_hi'].values[0] - b_data['mean_wait_avg'].values[0]]],
                      capsize=3, label='Subgroup B' if i == 0 else '')

        ax.set_xlabel('Scenario')
        ax.set_ylabel('Mean Wait Time (days)')
        ax.set_title(f'Utilization = {util*100:.0f}%')
        ax.set_xticks(x)
        ax.set_xticklabels([SCENARIO_LABELS.get(s, s) for s in SCENARIOS], fontsize=8)
        ax.set_ylim(0, max(df['mean_wait_avg'].max() * 1.3, 0.2))

        if idx == 0:
            ax.legend(loc='upper left')

    plt.suptitle('Mean Wait Times by Scenario and Utilization Level\n(with 95% Bootstrap CI)', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'wait_times_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()

def plot_equity_gaps(df):
    """Plot equity gap (A-B difference) across scenarios."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Calculate gaps
    gaps_data = []
    for scenario in SCENARIOS:
        for util in [1.0, 1.1, 1.2]:
            subset = df[(df['scenario'] == scenario) & (df['utilization'] == util)]
            a_data = subset[subset['subgroup'] == 'A']
            b_data = subset[subset['subgroup'] == 'B']

            if len(a_data) > 0 and len(b_data) > 0:
                gap = a_data['mean_wait_avg'].values[0] - b_data['mean_wait_avg'].values[0]
                gaps_data.append({
                    'scenario': scenario,
                    'utilization': f'{util*100:.0f}%',
                    'gap': gap
                })

    gaps_df = pd.DataFrame(gaps_data)

    # Create grouped bar chart
    x = np.arange(len(SCENARIOS))
    width = 0.25

    colors = ['#3498db', '#f39c12', '#e74c3c']
    for i, util in enumerate(['100%', '110%', '120%']):
        util_data = gaps_df[gaps_df['utilization'] == util]
        values = [util_data[util_data['scenario'] == s]['gap'].values[0] if len(util_data[util_data['scenario'] == s]) > 0 else 0 for s in SCENARIOS]
        ax.bar(x + (i - 1) * width, values, width, label=f'Util: {util}', color=colors[i], alpha=0.8)

    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.set_xlabel('Scenario')
    ax.set_ylabel('Equity Gap (A - B Wait Time, days)')
    ax.set_title('Equity Gap Analysis: Subgroup A vs Subgroup B\n(Positive = A waits longer)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([SCENARIO_LABELS.get(s, s) for s in SCENARIOS])
    ax.legend(title='Utilization')

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'equity_gaps.png', dpi=150, bbox_inches='tight')
    plt.close()

def plot_p95_comparison(df):
    """Plot P95 wait time comparison."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Focus on util=1.2 (highest stress)
    subset = df[df['utilization'] == 1.2]

    x = np.arange(len(SCENARIOS))
    width = 0.35

    colors = {'A': '#9b59b6', 'B': '#1abc9c'}

    for i, scenario in enumerate(SCENARIOS):
        scenario_data = subset[subset['scenario'] == scenario]
        if len(scenario_data) == 0:
            continue

        a_data = scenario_data[scenario_data['subgroup'] == 'A']
        b_data = scenario_data[scenario_data['subgroup'] == 'B']

        if len(a_data) > 0:
            ax.bar(i - width/2, a_data['P95_avg'].values[0], width,
                  color=colors['A'], alpha=0.8,
                  yerr=[[a_data['P95_avg'].values[0] - a_data['P95_ci_lo'].values[0]],
                        [a_data['P95_ci_hi'].values[0] - a_data['P95_avg'].values[0]]],
                  capsize=3, label='Subgroup A' if i == 0 else '')

        if len(b_data) > 0:
            ax.bar(i + width/2, b_data['P95_avg'].values[0], width,
                  color=colors['B'], alpha=0.8,
                  yerr=[[b_data['P95_avg'].values[0] - b_data['P95_ci_lo'].values[0]],
                        [b_data['P95_ci_hi'].values[0] - b_data['P95_avg'].values[0]]],
                  capsize=3, label='Subgroup B' if i == 0 else '')

    ax.set_xlabel('Scenario')
    ax.set_ylabel('P95 Wait Time (days)')
    ax.set_title('95th Percentile Wait Times at 120% Utilization\n(with 95% Bootstrap CI)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([SCENARIO_LABELS.get(s, s) for s in SCENARIOS])
    ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'p95_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()

def plot_utilization_impact(df):
    """Plot how utilization affects wait times."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for idx, subgroup in enumerate(['A', 'B']):
        ax = axes[idx]
        subset = df[df['subgroup'] == subgroup]

        for scenario in SCENARIOS:
            scenario_data = subset[subset['scenario'] == scenario].sort_values('utilization')
            if len(scenario_data) > 0:
                ax.plot(scenario_data['utilization'] * 100, scenario_data['mean_wait_avg'],
                       marker='o', linewidth=2, markersize=8, label=SCENARIO_LABELS.get(scenario, scenario).replace('\n', ' '))
                ax.fill_between(scenario_data['utilization'] * 100,
                               scenario_data['mean_wait_ci_lo'],
                               scenario_data['mean_wait_ci_hi'],
                               alpha=0.2)

        ax.set_xlabel('Capacity Utilization (%)')
        ax.set_ylabel('Mean Wait Time (days)')
        ax.set_title(f'Subgroup {subgroup}', fontsize=11, fontweight='bold')
        ax.legend(loc='upper left', fontsize=8)
        ax.set_xticks([100, 110, 120])

    plt.suptitle('Impact of Capacity Utilization on Wait Times', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'utilization_impact.png', dpi=150, bbox_inches='tight')
    plt.close()

def plot_scenario_summary(df):
    """Create summary heatmap of key metrics."""
    # Prepare data for heatmap
    metrics_data = []

    for scenario in SCENARIOS:
        for util in [1.0, 1.1, 1.2]:
            subset = df[(df['scenario'] == scenario) & (df['utilization'] == util)]
            a_data = subset[subset['subgroup'] == 'A']
            b_data = subset[subset['subgroup'] == 'B']

            if len(a_data) > 0 and len(b_data) > 0:
                avg_wait = (a_data['mean_wait_avg'].values[0] + b_data['mean_wait_avg'].values[0]) / 2
                gap = a_data['mean_wait_avg'].values[0] - b_data['mean_wait_avg'].values[0]

                metrics_data.append({
                    'Scenario': SCENARIO_LABELS.get(scenario, scenario).replace('\n', ' '),
                    'Utilization': f'{util*100:.0f}%',
                    'Avg Wait': avg_wait,
                    'Gap (A-B)': gap
                })

    metrics_df = pd.DataFrame(metrics_data)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Average Wait Heatmap
    pivot_wait = metrics_df.pivot(index='Scenario', columns='Utilization', values='Avg Wait')
    pivot_wait = pivot_wait[['100%', '110%', '120%']]
    sns.heatmap(pivot_wait, annot=True, fmt='.3f', cmap='YlOrRd', ax=axes[0], cbar_kws={'label': 'Days'})
    axes[0].set_title('Average Wait Time (days)', fontsize=11, fontweight='bold')

    # Gap Heatmap
    pivot_gap = metrics_df.pivot(index='Scenario', columns='Utilization', values='Gap (A-B)')
    pivot_gap = pivot_gap[['100%', '110%', '120%']]
    sns.heatmap(pivot_gap, annot=True, fmt='.3f', cmap='RdYlGn_r', center=0, ax=axes[1], cbar_kws={'label': 'Days'})
    axes[1].set_title('Equity Gap: A - B (days)', fontsize=11, fontweight='bold')

    plt.suptitle('Scenario Performance Summary', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'scenario_summary_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close()

def generate_statistics_table(df):
    """Generate detailed statistics table."""
    stats = []

    for scenario in SCENARIOS:
        for util in [1.0, 1.1, 1.2]:
            subset = df[(df['scenario'] == scenario) & (df['utilization'] == util)]
            a_data = subset[subset['subgroup'] == 'A']
            b_data = subset[subset['subgroup'] == 'B']

            if len(a_data) > 0 and len(b_data) > 0:
                stats.append({
                    'Scenario': scenario,
                    'Utilization': f'{util*100:.0f}%',
                    'A: Mean Wait': f"{a_data['mean_wait_avg'].values[0]:.4f}",
                    'A: P95': f"{a_data['P95_avg'].values[0]:.3f}",
                    'B: Mean Wait': f"{b_data['mean_wait_avg'].values[0]:.4f}",
                    'B: P95': f"{b_data['P95_avg'].values[0]:.3f}",
                    'Gap (A-B)': f"{a_data['mean_wait_avg'].values[0] - b_data['mean_wait_avg'].values[0]:.4f}"
                })

    return pd.DataFrame(stats)

if __name__ == "__main__":
    print("Loading aggregate data...")
    df = load_aggregate_data()

    if df.empty:
        print("No data found!")
        exit(1)

    print(f"Loaded {len(df)} rows from {df['scenario'].nunique()} scenarios")

    print("Generating visualizations...")
    plot_wait_times_comparison(df)
    print("  - wait_times_comparison.png")

    plot_equity_gaps(df)
    print("  - equity_gaps.png")

    plot_p95_comparison(df)
    print("  - p95_comparison.png")

    plot_utilization_impact(df)
    print("  - utilization_impact.png")

    plot_scenario_summary(df)
    print("  - scenario_summary_heatmap.png")

    print("\nGenerating statistics table...")
    stats_df = generate_statistics_table(df)
    stats_df.to_csv(FIGURES_DIR / 'statistics_table.csv', index=False)
    print("  - statistics_table.csv")

    print(f"\nAll outputs saved to: {FIGURES_DIR.absolute()}")
    print("\n" + "="*60)
    print("STATISTICS SUMMARY")
    print("="*60)
    print(stats_df.to_string(index=False))
