from src.config import load_config
from src.simulator import Simulation

def test_backlog_carries_over(tmp_path):
    cfg = load_config("params.yaml")
    cfg.sim.days = 2
    cfg.sim.seeds = [123]
    cfg.arrivals.urgent_rate_per_day = 200  # overwhelm capacity
    sim = Simulation(cfg, seed=123)
    df = sim.run()
    # Expect some patients still unscheduled by end of day 1 -> backlog exists
    assert (df["scheduled_day"].isna()).sum() >= 1

def test_no_show_logic(tmp_path):
    cfg = load_config("params.yaml")
    cfg.no_show.probability = 1.0
    cfg.sim.days = 1
    cfg.sim.seeds = [1]
    sim = Simulation(cfg, seed=1)
    df = sim.run()
    # With 100% no-show, nobody attends
    assert (df["attended"] == True).sum() == 0

