import os, json, glob
from click.testing import CliRunner
from src.cli import app

def test_bias_preset_manifest(tmp_path):
    out_dir = tmp_path / "outs"
    out_dir.mkdir(parents=True, exist_ok=True)

    runner = CliRunner()
    # Use tiny horizon & 1 seed for speed
    res = runner.invoke(app, [
        "run", "params.yaml",
        "--scenario", "hybrid",
        "--utilization", "1.1",
        "--days", "2",
        "--seeds", "1",
        "--bias-preset", "lowB",
        "--out_dir", str(out_dir)
    ], catch_exceptions=False)
    assert res.exit_code == 0

    # Find the run folder
    matches = sorted(glob.glob(os.path.join(str(out_dir), "run_seed_*_hash_*")))
    assert matches, "No run output directory found"
    man_path = os.path.join(matches[-1], "manifest.json")
    assert os.path.exists(man_path), "manifest.json missing"
    man = json.load(open(man_path))

    assert man.get("bias_preset") == "lowB"
    eff = man.get("bias_calibration_effective", {})
    # Check subgroup B values reflect the preset
    assert eff["slope"]["B"] == 0.8
    assert eff["intercept"]["B"] == 0.2
    assert eff["noise_sd"]["B"] == 0.10

