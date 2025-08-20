#!/usr/bin/env python3
"""
Create release bundle for dissertation
"""
import os, glob, json, shutil, pandas as pd, pathlib
import csv

def create_release_bundle():
    # Create output directory
    out = pathlib.Path("outputs/release_v1.2.0")
    out.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {out}")

    # Collect per-run essentials
    rows = []
    run_dirs = sorted(glob.glob("outputs/run_seed_*_hash_*"))
    print(f"Found {len(run_dirs)} run directories")

    for d in run_dirs:
        m = os.path.join(d, "manifest.json")
        o = os.path.join(d, "overall.csv")
        g = os.path.join(d, "gaps.csv")
        ov = os.path.join(d, "overrides.csv")

        files_exist = all(os.path.exists(f) for f in [m, o, g, ov])
        print(f"  {os.path.basename(d)}: files exist = {files_exist}")

        if not files_exist:
            continue

        try:
            with open(m) as f:
                man = json.load(f)

            # Extract utilization from config if not in manifest
            utilization = man.get("utilization")
            if utilization is None:
                # Try to infer from run name or set default
                utilization = "unknown"

            rows.append({
                "run": os.path.basename(d),
                "scenario": man.get("scenario", "unknown"),
                "utilization": utilization,
                "config_hash": man.get("params_hash"),
                "seed": man.get("seed"),
                "paths": {"dir": d}
            })
            print(f"    Added: scenario={man.get('scenario')}, util={utilization}")
        except Exception as e:
            print(f"    Error reading manifest: {e}")

    print(f"Collected {len(rows)} valid runs")

    # Write run_manifest.csv
    manifest_file = out / "run_manifest.csv"
    with open(manifest_file, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["run", "scenario", "utilization", "config_hash", "seed"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in w.fieldnames})
    print(f"Wrote run_manifest.csv with {len(rows)} runs")

    # Build consolidated results table
    def load_overall(row):
        df = pd.read_csv(os.path.join(row["paths"]["dir"], "overall.csv"))
        df["run"] = row["run"]
        df["scenario"] = row["scenario"]
        df["utilization"] = row["utilization"]

        try:
            ov = pd.read_csv(os.path.join(row["paths"]["dir"], "overrides.csv"))
            if "overridden" in ov.columns and len(ov) > 0:
                df["override_rate"] = ov["overridden"].mean()
            else:
                df["override_rate"] = None
        except Exception:
            df["override_rate"] = None
        return df

    if rows:
        all_dfs = []
        for r in rows:
            try:
                df = load_overall(r)
                all_dfs.append(df)
            except Exception as e:
                print(f"Error loading {r['run']}: {e}")

        if all_dfs:
            all_overall = pd.concat(all_dfs, ignore_index=True)

            # Define columns to keep (filter to what's actually available)
            desired_cols = ["scenario", "utilization", "subgroup", "mean_wait", "P90", "P95",
                          "same_day_rate", "within_3d_rate", "within_14d_rate",
                          "high_risk_same_day_share", "override_rate", "run"]
            available_cols = [col for col in desired_cols if col in all_overall.columns]
            print(f"Available columns: {available_cols}")

            # Sort and save
            result_df = all_overall[available_cols].sort_values(["scenario", "utilization", "subgroup"])
            result_df.to_csv(out / "main_table.csv", index=False)
            print(f"Wrote main_table.csv with {len(result_df)} rows")
        else:
            print("No valid overall data found")

    # Copy equity figure if present
    plot = pathlib.Path("outputs/plots/main_equity_vs_util.png")
    if plot.exists():
        shutil.copy(plot, out / plot.name)
        print("Copied equity figure")
    else:
        print("No equity figure found at outputs/plots/main_equity_vs_util.png")

    print(f"Release bundle written to: {out}")
    return out

if __name__ == "__main__":
    create_release_bundle()
