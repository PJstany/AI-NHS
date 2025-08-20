from src.config import load_config

def test_config_loads():
    cfg = load_config("params.yaml")
    assert cfg.sim.days >= 1
    assert cfg.thresholds_days.within_14d >= cfg.thresholds_days.within_3d

