# AI-NHS: Simulating AI-Assisted Patient Prioritisation in NHS GP Clinics

A discrete-event simulation framework for evaluating how AI-assisted patient prioritisation affects appointment wait times, equity across demographic subgroups, and service access in NHS General Practice clinics.

## Motivation

As NHS trusts explore AI tools to manage growing demand, a key question arises: **does AI-assisted scheduling improve efficiency without widening health inequalities?** This project provides a reproducible simulation environment to test that question under realistic NHS operating conditions, including demographic-specific AI calibration bias and clinician override behaviour.

## What It Simulates

The simulation models an NHS GP clinic (2 sessions/day, 100 daily slots) under four scheduling scenarios:

| Scenario | Description |
|----------|-------------|
| **Baseline** | First-come, first-served with urgent triage only |
| **AI Only** | AI risk predictions determine appointment order |
| **Imperfect AI** | AI with miscalibration bias against demographic subgroups |
| **Hybrid** | AI prioritisation with clinical override capability |

Key modelled factors:
- **Digital access gaps** between demographic subgroups (Subgroup B has 25% lower digital access)
- **AI calibration bias** (e.g., Subgroup B under-predicted by 15%)
- **Clinical overrides** (~22% override rate in hybrid scenario)
- **Stress testing** at 100%--120% utilisation with 30 seeds per scenario

## Key Findings

- Hybrid AI + clinician override performs best: **6.3% wait time reduction** vs baseline
- All scenarios maintain **>94% same-day appointment rates**
- Equity gaps persist but are manageable (0.03--0.06 days)
- System remains stable at 120% utilisation

See [`REALISTIC_SIMULATION_REPORT.md`](REALISTIC_SIMULATION_REPORT.md) for the full analysis.

## Installation

```bash
git clone https://github.com/PJstany/AI-NHS.git
cd AI-NHS
python -m venv venv
source venv/bin/activate
pip install -r requirements-lock.txt
```

Requires Python 3.9+.

## Usage

### Single run

```bash
python main.py run params_v1.2.0.yaml --scenario hybrid --utilization 1.20 --days 30
```

### Parallel grid (all cores)

```bash
python main.py run_grid params_v1.2.0.yaml \
  --scenario hybrid --util_list "1.0,1.1,1.2" \
  --seeds "301-330" --days 30 --n_jobs -1
```

### Bias presets

```bash
python main.py run_grid params_v1.2.0.yaml \
  --scenario hybrid --util_list "1.0,1.2" --seeds "301-330" \
  --bias-preset lowB --days 30 --n_jobs -1
```

### Override coefficient sweep

```bash
python main.py sweep_overrides params_v1.2.0.yaml \
  --param beta_queue --values "0.02,0.05,0.1,0.2" \
  --scenario hybrid --utilization 1.20 --seeds "301-330" --days 30 --n_jobs -1

python scripts/plot_override_sweep.py
```

## Project Structure

```
src/
  simulator.py    # Discrete-event simulation engine (SimPy)
  config.py       # Pydantic configuration models
  bias.py         # AI miscalibration functions per subgroup
  cli.py          # Typer CLI interface
  metrics.py      # Outcome measurement
  overrides.py    # Clinical override logic
  aggregate.py    # Result aggregation
scripts/          # Plotting and report generation
tests/            # Pytest suite (config, CLI, bias, equity, etc.)
params*.yaml      # Parameter configurations for each version
```

## Reproducibility

All package versions are frozen in `requirements-lock.txt`. Results are tagged by release (e.g., `v1.2.0-final`). See the [Reproducibility](#installation) section above and parameter files for full details.

## Tests

```bash
pytest
```

## License

[Apache License 2.0](LICENSE)
