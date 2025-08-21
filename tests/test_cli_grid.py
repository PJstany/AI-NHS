from click.testing import CliRunner
from src.cli import app
import glob, os

def test_run_grid_smoke(tmp_path):
    out_dir = tmp_path / "outs"
    out_dir.mkdir(parents=True, exist_ok=True)
    runner = CliRunner()
    res = runner.invoke(app, [
        "run_grid", "params.yaml",
        "--scenario", "hybrid",
        "--util_list", "1.2",
        "--seeds", "1-2",
        "--days", "2",
        "--n_jobs", "1",
        "--out_dir", str(out_dir)
    ], catch_exceptions=False)
    assert res.exit_code == 0
    matches = glob.glob(os.path.join(str(out_dir), "run_seed_*_hash_*"))
    assert len(matches) >= 2

