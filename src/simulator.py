from __future__ import annotations
import os, math
from typing import List, Dict, Tuple
import numpy as np
import pandas as pd
import simpy

from .config import RootCfg
from .entities import Patient
from .bias import generate_true_risk, apply_miscalibration
from .overrides import override_probability, calibrate_intercept_with_means

class Simulation:
    def __init__(self, cfg: RootCfg, seed: int):
        self.cfg = cfg
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.env = simpy.Environment()
        self.patients: List[Patient] = []
        self.backlog: List[Patient] = []
        self.override_log: List[Dict] = []
        # Assume typical means; queue mean in log-scale is ~3–4 under load, time-of-day mean ~0
        mu_uncert, mu_queue, mu_tod = 0.5, 2.5, 0.0  # further reduced mu_queue from 3.0 to 2.5
        self.override_intercept = calibrate_intercept_with_means(
            self.cfg.overrides.target_rate, mu_uncert, mu_queue, mu_tod,
            self.cfg.overrides.beta_uncertainty, self.cfg.overrides.beta_queue, self.cfg.overrides.beta_time_of_day
        )
        self.pid_counter = 0

    def daily_capacity(self) -> int:
        return self.cfg.sim.sessions_per_day * self.cfg.sim.slots_per_session

    # --- generators -------------------------------------------------
    def service_time(self) -> float:
        mix = self.cfg.service_mixtures
        if self.rng.random() < mix.long_weight:
            return float(self.rng.normal(mix.long_mean, mix.long_mean * 0.2))
        return float(self.rng.normal(mix.short_mean, mix.short_mean * 0.2))

    def new_arrivals(self, day: int) -> List[Patient]:
        # Expected counts modulated by digital access gap
        arr = self.cfg.arrivals
        urgent_n = self.rng.poisson(arr.urgent_rate_per_day)
        routine_n = self.rng.poisson(arr.routine_rate_per_day)

        # Assign subgroups with access gap applied to B
        def assign(n, pclass):
            # A: probability proportional to digital_access_gap[A], B: digital_access_gap[B]
            weights = np.array([
                self.cfg.arrivals.digital_access_gap.get("A", 1.0),
                self.cfg.arrivals.digital_access_gap.get("B", 1.0)
            ], dtype=float)
            probs = weights / weights.sum()
            sub = self.rng.choice(["A", "B"], size=n, p=probs)
            true = generate_true_risk(self.rng, n)
            preds, conf = apply_miscalibration(
                true, sub,
                self.cfg.bias_calibration.slope,
                self.cfg.bias_calibration.intercept,
                self.cfg.bias_calibration.noise_sd,
                self.cfg.bias_calibration.score_inflation,
                self.rng
            )
            patience_mean = (self.cfg.patience_days.urgent_mean if pclass=="urgent"
                             else self.cfg.patience_days.routine_mean)
            patience = self.rng.exponential(patience_mean, size=n)
            out = []
            for i in range(n):
                self.pid_counter += 1
                out.append(Patient(
                    pid=self.pid_counter,
                    subgroup=sub[i],
                    pclass=pclass,
                    true_risk=float(true[i]),
                    pred_risk=float(preds[i]),
                    confidence=float(conf[i]),
                    arrival_day=day,
                    patience_days=float(patience[i])
                ))
            return out

        return assign(urgent_n, "urgent") + assign(routine_n, "routine")

    # --- core loop --------------------------------------------------
    def run(self) -> pd.DataFrame:
        sessions = self.cfg.sim.sessions_per_day
        slots = self.cfg.sim.slots_per_session
        days = self.cfg.sim.days
        no_show_p = self.cfg.no_show.probability

        # daily loop with carry-over backlog
        for day in range(days):
            # 1) arrivals
            todays_new = self.new_arrivals(day)
            self.backlog.extend(todays_new)

            # remove patients who renege (patience expired)
            self.backlog = [p for p in self.backlog if (day - p.arrival_day) <= p.patience_days]
            for p in self.backlog:
                p.wait_days = max(0.0, day - p.arrival_day)

            # 2) sessions
            for s in range(sessions):
                time_of_day = (s / max(1, sessions - 1)) - 0.5  # now in [-0.5, +0.5]
                # available slots may be stressed by utilization factor
                capacity = max(0, math.floor(self.cfg.sim.slots_per_session / self.cfg.sim.utilization))

                for k in range(capacity):
                    if not self.backlog:
                        break
                    # sort by AI priority (higher pred_risk first, urgent before routine)
                    self.backlog.sort(key=lambda p: (p.pred_risk, p.pclass=="urgent"), reverse=True)
                    candidate = self.backlog[0]

                    # In hybrid, decide whether to override AI recommendation
                    overridden = False
                    if self.cfg.sim.scenario == "hybrid":
                        uncertainty = 1.0 - candidate.confidence
                        q_signal = math.log1p(len(self.backlog))  # scale backlog pressure
                        clinician_re = float(self.rng.normal(0, self.cfg.overrides.sd_clinician_random_effect))
                        prob = override_probability(
                            uncertainty=uncertainty,
                            queue_len=q_signal,
                            time_of_day_factor=time_of_day,
                            beta_uncertainty=self.cfg.overrides.beta_uncertainty,
                            beta_queue=self.cfg.overrides.beta_queue,
                            beta_time_of_day=self.cfg.overrides.beta_time_of_day,
                            intercept=self.override_intercept,
                            clinician_re=clinician_re
                        )
                        if self.rng.random() < prob:
                            overridden = True
                            # pick next best urgent or FCFS as a simple override behavior
                            alt_idx = 1 if len(self.backlog) > 1 else 0
                            candidate = self.backlog[alt_idx]

                        self.override_log.append({
                            "day": day, "session": s, "queue_len": len(self.backlog),
                            "pid": candidate.pid, "uncertainty": float(uncertainty),
                            "time_of_day": float(time_of_day), "overridden": overridden, "prob": float(prob)
                        })

                    # schedule candidate
                    self.backlog.remove(candidate)
                    candidate.scheduled_day = day
                    # no-show
                    candidate.no_show = bool(self.rng.random() < no_show_p)
                    if candidate.no_show:
                        if self.cfg.no_show.reschedule_rule == "backlog":
                            # re-enter backlog with the same arrival_day (continue wait)
                            self.backlog.append(candidate)
                        else:
                            candidate.attended = False
                    else:
                        candidate.attended = True
                        self.patients.append(candidate)

            # end of day loop continues with remaining backlog

        # finalize dataframe
        df = pd.DataFrame([p.__dict__ for p in (self.patients + self.backlog)])
        df["wait_days"] = df["wait_days"].fillna(0.0)
        df["breach_same_day"] = df["wait_days"] > self.cfg.thresholds_days.same_day
        df["breach_3d"] = df["wait_days"] > self.cfg.thresholds_days.within_3d
        df["breach_14d"] = df["wait_days"] > self.cfg.thresholds_days.within_14d
        if "pred_risk" not in df.columns:
            df["pred_risk"] = 0.5
        return df
