#!/usr/bin/env python3
"""
Quality checks for final results
"""
import os, glob, json, pandas as pd

def check_override_rates():
    """Check override rates for hybrid runs (should be ~0.25-0.35)"""
    print("=== 1. Override rates for hybrid runs ===")
    runs = sorted(glob.glob("outputs/run_seed_*_hash_*"))
    rows = []
    for d in runs:
        m = os.path.join(d, "manifest.json")
        ovp = os.path.join(d, "overrides.csv")
        if os.path.exists(m) and os.path.exists(ovp):
            man = json.load(open(m))
            if man.get("scenario") == "hybrid":
                ov = pd.read_csv(ovp)
                rate = ov["overridden"].mean() if "overridden" in ov and len(ov) else float("nan")
                rows.append({
                    "run": os.path.basename(d),
                    "utilization": man.get("utilization", "unknown"),
                    "override_rate": rate
                })
    df = pd.DataFrame(rows).sort_values(["utilization", "run"])
    if not df.empty:
        print(df.to_string(index=False))
        print(f"\nOverride rates range: {df['override_rate'].min():.3f} - {df['override_rate'].max():.3f}")
        print(f"Mean override rate: {df['override_rate'].mean():.3f}")
    else:
        print("No hybrid runs with overrides.csv found.")
    print()

def check_stress_tails():
    """Confirm tails are >0 under stress (utilization >= 1.1)"""
    print("=== 2. Tail metrics under stress (utilization >= 1.1) ===")
    rows = []
    for d in glob.glob("outputs/run_seed_*_hash_*"):
        m = os.path.join(d, "manifest.json")
        o = os.path.join(d, "overall.csv")
        if os.path.exists(m) and os.path.exists(o):
            man = json.load(open(m))
            util = man.get("utilization")
            try:
                util_float = float(util) if util is not None else None
            except:
                util_float = None

            if man.get("scenario") == "hybrid" and util_float and util_float >= 1.1:
                over = pd.read_csv(o)
                available_cols = ["subgroup", "P90", "P95"]
                # Add urgent_breach_rate if it exists
                if "urgent_breach_rate" in over.columns:
                    available_cols.append("urgent_breach_rate")

                for _, row in over[available_cols].iterrows():
                    row_dict = {
                        "run": os.path.basename(d),
                        "utilization": util,
                    }
                    row_dict.update(row.to_dict())
                    rows.append(row_dict)

    df = pd.DataFrame(rows).sort_values(["utilization", "subgroup"]) if rows else pd.DataFrame()
    if not df.empty:
        print(df.to_string(index=False))
        print(f"\nStress conditions found in {len(df)} subgroup-run combinations")
    else:
        print("No stress conditions (util >= 1.1) found.")
    print()

def check_equity_signals():
    """Confirm equity signals move (P95 gap B−A) with congestion"""
    print("=== 3. Equity signals (P95 gap B-A) movement with congestion ===")
    rows = []
    for d in glob.glob("outputs/run_seed_*_hash_*"):
        m = os.path.join(d, "manifest.json")
        g = os.path.join(d, "gaps.csv")
        if os.path.exists(m) and os.path.exists(g):
            man = json.load(open(m))
            if man.get("scenario") == "hybrid":
                gaps = pd.read_csv(g).set_index("metric")["value"].to_dict()
                rows.append({
                    "run": os.path.basename(d),
                    "utilization": man.get("utilization", None),
                    "P95_gap_B_minus_A": gaps.get("P95_gap_B_minus_A")
                })
    df = pd.DataFrame(rows).dropna().sort_values("utilization") if rows else pd.DataFrame()
    if not df.empty:
        print(df.to_string(index=False))
    else:
        print("No hybrid gaps with utilization recorded.")
    print()

def check_scenario_coverage():
    """Check we have all expected scenarios"""
    print("=== 4. Scenario coverage ===")
    runs = glob.glob("outputs/run_seed_*_hash_*")
    scenarios = set()
    for d in runs:
        m = os.path.join(d, "manifest.json")
        if os.path.exists(m):
            man = json.load(open(m))
            scenarios.add(man.get("scenario", "unknown"))

    expected = {"baseline", "ai_only", "imperfect_ai", "hybrid"}
    print(f"Found scenarios: {sorted(scenarios)}")
    print(f"Expected scenarios: {sorted(expected)}")
    missing = expected - scenarios
    if missing:
        print(f"⚠️  Missing scenarios: {missing}")
    else:
        print("✅ All expected scenarios present")
    print()

def comprehensive_results_table():
    """Generate comprehensive results table"""
    print("=== 5. Comprehensive Results Table ===")
    rows = []
    for d in glob.glob("outputs/run_seed_*_hash_*"):
        m = os.path.join(d, "manifest.json")
        o = os.path.join(d, "overall.csv")
        ovp = os.path.join(d, "overrides.csv")
        if not (os.path.exists(m) and os.path.exists(o)):
            continue
        man = json.load(open(m))
        util = man.get("utilization", None)
        scen = man.get("scenario", "?")
        over = pd.read_csv(o).assign(run=os.path.basename(d), scenario=scen, utilization=util)
        # optional: attach override rate (if file present)
        ov_rate = None
        if os.path.exists(ovp):
            try:
                ov = pd.read_csv(ovp)
                if "overridden" in ov:
                    ov_rate = float(ov["overridden"].mean())
            except Exception:
                pass
        over["override_rate"] = ov_rate
        rows.append(over)

    if not rows:
        print("No overall.csv found in outputs.")
        return

    all_data = pd.concat(rows, ignore_index=True)
    keep = ["scenario", "utilization", "subgroup", "mean_wait", "P90", "P95",
            "same_day_rate", "within_3d_rate", "within_14d_rate",
            "high_risk_same_day_share", "override_rate", "run"]
    # prefer only runs that have utilization recorded for figure/table consistency
    newer = all_data[all_data["utilization"].notna()] if all_data["utilization"].notna().any() else all_data
    tbl = newer[keep].sort_values(["scenario", "utilization", "subgroup"])
    print(tbl.to_string(index=False))

def main():
    """Run all quality checks"""
    print("Quality Check Report")
    print("=" * 50)
    check_override_rates()
    check_stress_tails()
    check_equity_signals()
    check_scenario_coverage()
    comprehensive_results_table()
    print("Quality check complete!")

if __name__ == "__main__":
    main()
