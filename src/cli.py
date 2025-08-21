import os, json, copy
from typing import Optional, List
import typer
import pandas as pd
from joblib import Parallel, delayed

from .config import load_config, cfg_hash
from .simulator import Simulation
from .aggregate import summarize, save_summary
from .utils import write_manifest

app = typer.Typer(add_completion=False, help="GP access simulation CLI")

def _parse_seeds(spec: str) -> List[int]:
    spec = spec.strip()
    out: List[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(list(range(int(a), int(b) + 1)))
        else:
            out.append(int(part))
    return out

def _parse_float_list(s: str) -> List[float]:
    return [float(x.strip()) for x in s.split(",") if x.strip()]

def _write_one_run(cfg, out_dir: str, seed: int) -> str:
    os.makedirs(out_dir, exist_ok=True)
    h = cfg_hash(cfg)
    sim = Simulation(cfg, seed=seed)
    df = sim.run()

    run_dir = os.path.join(out_dir, "run_seed_{:d}_hash_{:s}".format(seed, h[:8]))
    os.makedirs(run_dir, exist_ok=True)

    # events
    df.to_csv(os.path.join(run_dir, "events.csv"), index=False)

    # overrides.csv (always, when enabled)
    if cfg.output.write_overrides_log:
        ovr_path = os.path.join(run_dir, "overrides.csv")
        ovr = pd.DataFrame(sim.override_log)
        if ovr.empty:
            ovr = pd.DataFrame(columns=["day","session","queue_len","pid","uncertainty","time_of_day","overridden","prob"])
        ovr.to_csv(ovr_path, index=False)

    # summaries
    thr = {
        "same_day": cfg.thresholds_days.same_day,
        "within_3d": cfg.thresholds_days.within_3d,
        "within_14d": cfg.thresholds_days.within_14d,
    }
    summ = summarize(df, thr)
    save_summary(run_dir, summ)

    # manifest (provenance)
    manifest = {
        "sim_version": "1.0.0",
        "params_hash": h,
        "seed": seed,
        "config_path": os.path.abspath("params.yaml"),
        "scenario": cfg.sim.scenario,
        "utilization": float(cfg.sim.utilization),
        "days": int(cfg.sim.days),
    }
    for k in ("beta_queue","beta_uncertainty","beta_time_of_day"):
        try:
            manifest[k] = float(getattr(cfg.overrides, k))
        except Exception:
            pass
    write_manifest(run_dir, manifest)

    # brief stdout like before
    overall = pd.read_csv(os.path.join(run_dir, "overall.csv"))
    gaps = pd.read_csv(os.path.join(run_dir, "gaps.csv"))
    print(overall.to_string(index=False))
    print(gaps.to_string(index=False))

    return run_dir

@app.command()
def run(
    config: str = typer.Argument("params.yaml"),
    seed: Optional[int] = typer.Option(None, help="Single seed; default uses cfg.sim.seeds"),
    out_dir: Optional[str] = typer.Option(None, help="Override output dir"),
    scenario: Optional[str] = typer.Option(None, help="Override scenario [baseline|ai_only|imperfect_ai|hybrid]"),
    utilization: Optional[float] = typer.Option(None, help="Override utilization multiplier, e.g. 1.1"),
    days: Optional[int] = typer.Option(None, help="Override simulation days"),
):
    cfg = load_config(config)
    if scenario: cfg.sim.scenario = scenario
    if utilization is not None: cfg.sim.utilization = float(utilization)
    if days is not None: cfg.sim.days = int(days)

    out_dir = out_dir or cfg.output.out_dir
    seeds = [seed] if seed is not None else list(cfg.sim.seeds)
    for s in seeds:
        print("[run] seed={}".format(s))
        _write_one_run(cfg, out_dir, s)
    typer.echo("Completed {} run(s). Outputs: {}".format(len(seeds), out_dir))

@app.command()
def run_grid(
    config: str = typer.Argument("params.yaml"),
    scenario: Optional[str] = typer.Option(None, help="Override scenario"),
    util_list: str = typer.Option("1.0,1.1,1.2", help='Comma list, e.g. "1.0,1.1,1.2"'),
    seeds: str = typer.Option("301-330", help='Range/list, e.g. "301-330" or "101,105"'),
    days: Optional[int] = typer.Option(None, help="Override simulation days"),
    n_jobs: int = typer.Option(-1, help="Parallel jobs (-1 = all cores)"),
    out_dir: Optional[str] = typer.Option(None, help="Override output dir"),
    bias_preset: Optional[str] = typer.Option(None, help="(reserved)"),
):
    cfg = load_config(config)
    if scenario: cfg.sim.scenario = scenario
    if days is not None: cfg.sim.days = int(days)
    out_dir = out_dir or cfg.output.out_dir

    utils = _parse_float_list(util_list)
    seed_list = _parse_seeds(seeds)
    tasks = [(u, s) for u in utils for s in seed_list]

    def _job(u, s):
        c = copy.deepcopy(cfg)
        c.sim.utilization = float(u)
        return _write_one_run(c, out_dir, s)

    Parallel(n_jobs=n_jobs)(delayed(_job)(u, s) for (u, s) in tasks)
    typer.echo("Grid complete. Utils={} Seeds={} Outputs: {}".format(utils, seed_list, out_dir))

@app.command()
def sweep_overrides(
    config: str = typer.Argument("params.yaml"),
    param: str = typer.Option(..., help="cfg.overrides field to vary, e.g. beta_queue"),
    values: str = typer.Option(..., help='Comma list, e.g. "0.02,0.05,0.1,0.2"'),
    scenario: Optional[str] = typer.Option(None, help="Override scenario (e.g., hybrid)"),
    utilization: Optional[float] = typer.Option(None, help="Override utilization, e.g., 1.20"),
    seeds: str = typer.Option("301-330", help='Range/list, e.g. "301-330"'),
    days: Optional[int] = typer.Option(None, help="Override simulation days"),
    n_jobs: int = typer.Option(-1, help="Parallel jobs (-1 = all cores)"),
    out_dir: Optional[str] = typer.Option(None, help="Override output dir"),
):
    cfg0 = load_config(config)
    if scenario: cfg0.sim.scenario = scenario
    if utilization is not None: cfg0.sim.utilization = float(utilization)
    if days is not None: cfg0.sim.days = int(days)
    out_dir = out_dir or cfg0.output.out_dir

    vals = _parse_float_list(values)
    seed_list = _parse_seeds(seeds)

    def _job(val, seed):
        c = copy.deepcopy(cfg0)
        if not hasattr(c.overrides, param):
            raise SystemExit("cfg.overrides has no attribute '{}'".format(param))
        setattr(c.overrides, param, float(val))
        run_dir = _write_one_run(c, out_dir, seed)
        rate = float("nan")
        ovr_path = os.path.join(run_dir, "overrides.csv")
        if os.path.exists(ovr_path) and os.path.getsize(ovr_path) > 0:
            df = pd.read_csv(ovr_path)
            if "overridden" in df.columns and len(df):
                rate = float(df["overridden"].mean())
        return {"param": param, "value": float(val), "seed": int(seed),
                "override_rate": rate, "run": os.path.basename(run_dir)}

    rows = Parallel(n_jobs=n_jobs)(delayed(_job)(v, s) for v in vals for s in seed_list)
    out_csv = os.path.join("outputs", "override_coeff_sweep.csv")
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    typer.echo("Wrote {}".format(out_csv))

@app.command()
def aggregate(out_dir: str = typer.Argument("outputs")):
    import glob
    frames = []
    for d in glob.glob(os.path.join(out_dir, "run_seed_*_hash_*")):
        f = os.path.join(d, "overall.csv")
        if os.path.exists(f):
            df = pd.read_csv(f)
            df["run"] = os.path.basename(d)
            frames.append(df)
    if not frames:
        typer.echo("No runs found.")
        raise typer.Exit(code=0)
    all_overall = pd.concat(frames, ignore_index=True)
    out = os.path.join(out_dir, "aggregate_overall.csv")
    all_overall.to_csv(out, index=False)
    typer.echo("Wrote {}".format(out))

@app.command()
def version():
    typer.echo("sim version 1.0.0")
