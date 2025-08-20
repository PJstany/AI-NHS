from __future__ import annotations
import numpy as np
from typing import Dict

def logistic(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))

def override_probability(uncertainty: float,
                         queue_len: int,
                         time_of_day_factor: float,
                         beta_uncertainty: float,
                         beta_queue: float,
                         beta_time_of_day: float,
                         intercept: float,
                         clinician_re: float) -> float:
    x = (beta_uncertainty * uncertainty +
         beta_queue * queue_len +
         beta_time_of_day * time_of_day_factor +
         intercept + clinician_re)
    return float(logistic(np.array([x]))[0])

def calibrate_intercept(target_rate: float, guess: float = -1.0) -> float:
    # Cheap heuristic to initialize intercept to hit target average rate
    # (fine-tune by empirical calibration during warmup if desired)
    # logistic(guess) ~ target => guess = logit(target)
    eps = 1e-6
    t = np.clip(target_rate, eps, 1 - eps)
    return float(np.log(t / (1 - t)))

def calibrate_intercept_with_means(target_rate: float, mu_uncert: float, mu_queue: float, mu_tod: float,
                                   beta_uncertainty: float, beta_queue: float, beta_time_of_day: float) -> float:
    # Solve logit(target) = intercept + βu*mu_uncert + βq*mu_queue + βt*mu_tod
    import numpy as np
    eps = 1e-6
    t = np.clip(target_rate, eps, 1 - eps)
    base = np.log(t / (1 - t))
    return float(base - (beta_uncertainty*mu_uncert + beta_queue*mu_queue + beta_time_of_day*mu_tod))
