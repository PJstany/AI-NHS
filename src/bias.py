from __future__ import annotations
import numpy as np
from typing import Tuple, Dict

def generate_true_risk(rng: np.random.Generator, size: int) -> np.ndarray:
    # Latent true risk in [0,1], heavy in the middle
    base = rng.beta(2.0, 2.0, size=size)
    return np.clip(base, 0.0, 1.0)

def apply_miscalibration(true_risk: np.ndarray,
                         subgroup: np.ndarray,
                         slope: Dict[str, float],
                         intercept: Dict[str, float],
                         noise_sd: Dict[str, float],
                         score_inflation: float,
                         rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
    preds = np.empty_like(true_risk)
    conf = np.empty_like(true_risk)
    for g in ("A", "B"):
        idx = (subgroup == g)
        s = slope[g]; b = intercept[g]; sd = noise_sd[g]
        noisy = s * true_risk[idx] + b + rng.normal(0, sd, size=idx.sum())
        noisy = np.clip(noisy + score_inflation, 0.0, 1.0)
        preds[idx] = noisy
        # proxy confidence: higher where noise is smaller and risk extreme
        conf[idx] = 1.0 - np.minimum(1.0, sd + 0.2 * (1 - np.abs(noisy - 0.5)))
    return preds, np.clip(conf, 0.0, 1.0)

