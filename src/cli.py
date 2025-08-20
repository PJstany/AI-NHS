from __future__ import annotations
import os, sys, time, json
from pathlib import Path
from typing import Optional, List
import typer
import pandas as pd
from rich import print as rprint

from .config import load_config, cfg_hash, ensure_out_dir
from .simulator import Simulation
from .aggregate import summarize, save_summary
from .utils import write_manifest

app = typer.Typer(add_completion=False, help="GP access simulation CLI")

@app.command()
def run(
    config: str = typer.Argument("params.yaml"),
    seed: Optional[int] = typer.Option(None, help="override single seed"),
    out_dir: Optional[str] = typer.Option(None, help="override output directory"),
    # NEW:
    scenario: Optional[str] = typer.Option(
        None,
        help="override scenario: baseline | ai_only | imperfect_ai | hybrid",
    ),
    utilization: Optional[float] = typer.Option(
        None,
        help="override utilization multiplier (e.g., 1.1)",
    ),
):
    cfg = load_config(config)
    # NEW: apply overrides if provided
    if scenario is not None:
        if scenario not in {"baseline", "ai_only", "imperfect_ai", "hybrid"}:
            raise typer.BadParameter("scenario must be baseline|ai_only|imperfect_ai|hybrid")
        cfg.sim.scenario = scenario
    if utilization is not None:
        cfg.sim.utilization = utilization
    # Fix: ensure out_dir is a string, not OptionInfo
    if not isinstance(out_dir, str) or not out_dir:
        out_dir = cfg.output.out_dir
    # Fix: ensure seed is None or int, not OptionInfo
    if not (isinstance(seed, int) or seed is None):
        seed = None
    ensure_out_dir(out_dir)
    h = cfg_hash(cfg)

    seeds = [seed] if seed is not None else cfg.sim.seeds
    for s in seeds:
        rprint(f"[bold cyan]Running seed {s}[/bold cyan]")
        sim = Simulation(cfg, seed=s)
        df = sim.run()
        run_name = f"run_seed_{s}_hash_{h[:8]}"
        run_dir = os.path.join(out_dir, run_name)
        os.makedirs(run_dir, exist_ok=True)
        df.to_csv(os.path.join(run_dir, "events.csv"), index=False)
        # always write overrides.csv when enabled (even if empty)
        if cfg.output.write_overrides_log:
            ov_path = os.path.join(run_dir, "overrides.csv")
            if len(sim.override_log):
                pd.DataFrame(sim.override_log).to_csv(ov_path, index=False)
            else:
                pd.DataFrame(columns=[
                    "day","session","queue_len","pid","uncertainty","time_of_day","overridden","prob"
                ]).to_csv(ov_path, index=False)
        summ = summarize(df, {
            "same_day": cfg.thresholds_days.same_day,
            "within_3d": cfg.thresholds_days.within_3d,
            "within_14d": cfg.thresholds_days.within_14d
        })
        save_summary(run_dir, summ)
        write_manifest(run_dir, {
            "sim_version": "1.0.0",
            "params_hash": h,
            "seed": s,
            "scenario": cfg.sim.scenario,   # <— add this
            "config_path": str(Path(config).resolve()),
        })
        overall_path = os.path.join(run_dir, "overall.csv")
        gaps_path = os.path.join(run_dir, "gaps.csv")
        print(pd.read_csv(overall_path).to_string(index=False))
        print(pd.read_csv(gaps_path).to_string(index=False))
    typer.echo(f"Completed {len(seeds)} run(s). Outputs: {out_dir}")

@app.command()
def sweep(configs: List[str] = typer.Argument(...),
          parallel: bool = typer.Option(True, help="Use joblib Parallel")):
    from joblib import Parallel, delayed
    def _one(conf: str):
        # Call the function directly with a string path
        run(config=conf)

    if parallel:
        Parallel(n_jobs=-1)(delayed(_one)(c) for c in configs)
    else:
        for c in configs:
            _one(c)

@app.command()
def aggregate(out_dir: str = typer.Argument("outputs")):
    # Combine overall.csv across run folders
    paths = [p for p in Path(out_dir).glob("run_seed_*_hash_*") if p.is_dir()]
    frames = []
    for p in paths:
        f = p / "overall.csv"
        if f.exists():
            df = pd.read_csv(f)
            df["run"] = p.name
            frames.append(df)
    if not frames:
        typer.echo("No runs found.")
        raise typer.Exit(code=0)
    all_overall = pd.concat(frames, ignore_index=True)
    out = Path(out_dir) / "aggregate_overall.csv"
    all_overall.to_csv(out, index=False)
    typer.echo(f"Wrote {out}")

@app.command()
def version():
    typer.echo("sim version 1.0.0")

if __name__ == "__main__":
    app()
