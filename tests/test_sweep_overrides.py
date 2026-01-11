from typer.testing import CliRunner
from src.cli import app
import os

def test_sweep_overrides_csv(tmp_path):
    out_dir = tmp_path / "outs"
    out_dir.mkdir(parents=True, exist_ok=True)
    runner = CliRunner()
    res = runner.invoke(app, [
        "sweep-overrides", "params.yaml",
        "--param", "beta_queue",
        "--values", "0.1,0.2",
        "--scenario", "hybrid",
        "--utilization", "1.2",
        "--seeds", "1-2",
        "--days", "2",
        "--n-jobs", "1",
        "--out-dir", str(out_dir)
    ], catch_exceptions=False)
    assert res.exit_code == 0
    out_csv = os.path.join("outputs", "override_coeff_sweep.csv")
    assert os.path.exists(out_csv)

