from src.config import load_config, cfg_hash
from src.simulator import Simulation

def test_golden_run_regression():
    cfg = load_config("params.yaml")
    cfg.sim.days = 2
    cfg.sim.seeds = [42]
    sim = Simulation(cfg, seed=42)
    df = sim.run()
    # Golden assertion: core invariants rather than exact numeric equality
    assert set(df.columns) >= {"pid","subgroup","pclass","pred_risk","wait_days"}
    assert (df["attended"].isin([True, False, None])).all()

