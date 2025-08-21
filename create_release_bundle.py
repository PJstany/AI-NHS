#!/usr/bin/env python3
"""
Create release bundle for dissertation
"""
import os, glob, json, shutil, pandas as pd
import csv
import sys

def create_release_bundle(out_dir=None):
    # Determine output directory
    if out_dir is None:
        out = os.path.join("outputs", "release_v1.2.0")
    else:
        out = out_dir
    if not os.path.exists(out):
        os.makedirs(out)
    print("Created directory: {}".format(out))

    # Collect per-run essentials
    rows = []
    run_dirs = sorted(glob.glob("outputs/run_seed_*_hash_*"))
    print("Found {} run directories".format(len(run_dirs)))

    for d in run_dirs:
        m = os.path.join(d, "manifest.json")
        o = os.path.join(d, "overall.csv")
        g = os.path.join(d, "gaps.csv")
        ov = os.path.join(d, "overrides.csv")

        files_exist = all(os.path.exists(f) for f in [m, o, g, ov])
        print("  {}: files exist = {}".format(os.path.basename(d), files_exist))

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
            print("    Added: scenario={}, util={}".format(man.get('scenario'), utilization))
        except Exception as e:
            print("    Error reading manifest: {}".format(e))

    print("Collected {} valid runs".format(len(rows)))

    # Write run_manifest.csv
    manifest_file = os.path.join(out, "run_manifest.csv")
    with open(manifest_file, "w") as f:
        w = csv.DictWriter(f, fieldnames=["run", "scenario", "utilization", "config_hash", "seed"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in w.fieldnames})
    print("Wrote run_manifest.csv with {} runs".format(len(rows)))

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
                print("Error loading {}: {}".format(r['run'], e))

        if all_dfs:
            all_overall = pd.concat([df for df in all_dfs if df is not None and not df.empty], ignore_index=True)

            # Define columns to keep (filter to what's actually available)
            desired_cols = ["scenario", "utilization", "subgroup", "mean_wait", "P90", "P95",
                          "same_day_rate", "within_3d_rate", "within_14d_rate",
                          "high_risk_same_day_share", "override_rate", "run"]
            available_cols = [col for col in desired_cols if col in all_overall.columns]
            print("Available columns: {}".format(available_cols))

            # Sort and save
            result_df = all_overall[available_cols].sort_values(["scenario", "utilization", "subgroup"])
            result_df.to_csv(os.path.join(out, "main_table.csv"), index=False)
            print("Wrote main_table.csv with {} rows".format(len(result_df)))
        else:
            print("No valid overall data found")

    # Copy equity figure if present
    plot = os.path.join("outputs", "plots", "main_equity_vs_util.png")
    if os.path.exists(plot):
        shutil.copy(plot, os.path.join(out, os.path.basename(plot)))
        print("Copied equity figure")
    else:
        print("No equity figure found at outputs/plots/main_equity_vs_util.png")

    print("Release bundle written to: {}".format(out))
    return out

if __name__ == "__main__":
    # Allow output directory as optional argument
    out_dir = sys.argv[1] if len(sys.argv) > 1 else None
    create_release_bundle(out_dir)
