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
def run(config: str = typer.Argument("params.yaml"),
        seed: Optional[int] = typer.Option(None),
        out_dir: Optional[str] = typer.Option(None)):
    cfg = load_config(config)
    out_dir = out_dir or cfg.output.out_dir
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
        if cfg.output.write_overrides_log and len(sim.override_log):
            pd.DataFrame(sim.override_log).to_csv(os.path.join(run_dir, "overrides.csv"), index=False)
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
    def _one(conf):
        try:
            run([conf])  # reuse command
        except SystemExit:
            pass

    if parallel:
        Parallel(n_jobs=-1)(delayed(_one)(c) for c in configs)
    else:
        for c in configs: _one(c)

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
