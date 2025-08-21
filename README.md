# README

## Overview

This document provides instructions for running the hybrid model simulations using the provided Python scripts. The simulations can be run for different scenarios, utilizations, and seeds. Additionally, options for parallel processing and long-horizon robustness checks are available.

## Parallel grid (uses all cores)

Run hybrid across utilisations and 30 seeds in parallel:

```bash
python main.py run_grid params_v1.2.0.yaml --scenario hybrid --util_list "1.0,1.1,1.2" --seeds "301-330" --days 30 --n_jobs -1
```

### Bias presets
Run hybrid with subgroup-B miscalibration presets (no YAML edits):
```bash
# Low bias against B (slope=0.8, intercept=+0.2, noise=0.10)
python main.py run_grid params_v1.2.0.yaml \
  --scenario hybrid --util_list "1.0,1.2" --seeds "301-330" \
  --bias-preset lowB --days 30 --n_jobs -1
```

Long-horizon robustness (single scenario)

```bash
python main.py run params_v1.2.0.yaml --scenario hybrid --utilization 1.20 --days 365 --seeds "301-330"
```

Warm-up filter

Set `analysis.warmup_days` in YAML (e.g., 14). Metrics ignore arrivals before that day during summarization.

## Override coefficient sweep (parallel on all cores)
Run a sweep over `beta_queue` at u=1.20 across 30 seeds, then plot:

```bash
python main.py sweep_overrides params_v1.2.0.yaml \
  --param beta_queue --values "0.02,0.05,0.1,0.2" \
  --scenario hybrid --utilization 1.20 --seeds "301-330" --days 30 --n_jobs -1

python scripts/plot_override_sweep.py
```

**Rationale:** Documents how to run multi-core grids and long horizons reproducibly.

## Quick Recipes

### Grid (all cores)
```bash
python main.py run_grid params_v1.2.0.yaml \
  --scenario hybrid --util_list "1.0,1.1,1.2" \
  --seeds "301-330" --days 30 --n_jobs -1
```

Override coefficient sweep + plot
```bash
python main.py sweep_overrides params_v1.2.0.yaml \
  --param beta_queue --values "0.02,0.05,0.1,0.2" \
  --scenario hybrid --utilization 1.20 --seeds "301-330" --days 30 --n_jobs -1

python scripts/plot_override_sweep.py
```

## Reproducibility

To fully reproduce results:

- Python version: Run `python -V` to confirm the exact version used for this release.
- All package versions are frozen in `requirements-lock.txt` (see this file for exact wheels).
- To recreate the environment:
  ```bash
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements-lock.txt
  ```
- All code and results are tagged (e.g., `v1.2.0-final`).

### Regenerating the release bundle

To regenerate the release bundle from tag `v1.2.0-final`:

```bash
# Clone and checkout the frozen tag
 git clone <repo-url>
 cd <repo>
 git checkout v1.2.0-final

# Create and activate a fresh environment
 python -m venv venv
 source venv/bin/activate
 pip install -r requirements-lock.txt

# Run the release sweep (frozen params, seeds, utilization)
 python main.py run_grid params_v1.2.0.yaml --scenario hybrid --util_list "1.0,1.1,1.2" --seeds "301-330" --days 30 --n_jobs -1
```
