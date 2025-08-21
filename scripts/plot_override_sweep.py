#!/usr/bin/env python3
import os, sys
import pandas as pd
import matplotlib.pyplot as plt

IN = "outputs/override_coeff_sweep.csv"
OUT = "outputs/plots/sweep_plot_override_rate.png"

def main():
    if not os.path.exists(IN):
        print(f"No sweep CSV found at {IN}")
        sys.exit(0)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    df = pd.read_csv(IN)
    # per-value mean and 95% CI via normal approx (seeds are many; OK for quick viz)
    grp = df.groupby("value")["override_rate"].agg(["mean", "count", "std"]).reset_index()
    grp["se"] = grp["std"] / (grp["count"] ** 0.5)
    grp["lo"] = grp["mean"] - 1.96 * grp["se"]
    grp["hi"] = grp["mean"] + 1.96 * grp["se"]

    plt.figure()
    plt.errorbar(grp["value"], grp["mean"], yerr=[grp["mean"]-grp["lo"], grp["hi"]-grp["mean"]], fmt="o-")
    plt.axhline(0.25, linestyle="--")
    plt.xlabel("Coefficient value")
    plt.ylabel("Override rate")
    plt.title("Override rate vs coefficient")
    plt.tight_layout()
    plt.savefig(OUT, dpi=150)
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()

