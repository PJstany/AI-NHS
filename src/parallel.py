from __future__ import annotations
from joblib import Parallel, delayed
from typing import List, Dict
from .simulator import Simulation
from .config import RootCfg

def run_parallel(cfg: RootCfg, seeds: List[int]):
    def _one(s):
        sim = Simulation(cfg, seed=s)
        return s, sim.run()
    results = Parallel(n_jobs=-1)(delayed(_one)(s) for s in seeds)
    return dict(results)

