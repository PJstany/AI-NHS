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
        """
        Run the full simulation over all days.

        Returns:
            DataFrame with all patient events and outcomes
        """
        days = self.cfg.sim.days
        sessions_per_day = self.cfg.sim.sessions_per_day

        # Daily loop with carry-over backlog
        for day in range(days):
            self._process_daily_arrivals(day)
            self._update_backlog_with_reneging(day)

            for session in range(sessions_per_day):
                self._schedule_session(day, session, sessions_per_day)

        return self._finalize_results()

    def _process_daily_arrivals(self, day: int) -> None:
        """Add new patient arrivals to the backlog."""
        new_arrivals = self.new_arrivals(day)
        self.backlog.extend(new_arrivals)

    def _update_backlog_with_reneging(self, day: int) -> None:
        """
        Remove patients who have exceeded their patience threshold.
        Update wait times for remaining patients.
        """
        # Remove patients who renege (patience expired)
        self.backlog = [
            p for p in self.backlog
            if (day - p.arrival_day) <= p.patience_days
        ]

        # Update wait times
        for p in self.backlog:
            p.wait_days = max(0.0, day - p.arrival_day)

    def _schedule_session(self, day: int, session: int, total_sessions: int) -> None:
        """
        Schedule patients for a single session.

        Args:
            day: Current simulation day
            session: Session number within the day
            total_sessions: Total sessions per day (for time-of-day calculation)
        """
        # Calculate session parameters
        time_of_day = (session / max(1, total_sessions - 1)) - 0.5  # in [-0.5, +0.5]
        capacity = max(0, math.floor(
            self.cfg.sim.slots_per_session / self.cfg.sim.utilization
        ))

        # Fill all available slots
        for _ in range(capacity):
            if not self.backlog:
                break

            candidate = self._select_patient_for_slot(day, session, time_of_day)
            if candidate:
                self._handle_appointment(candidate, day)

    def _select_patient_for_slot(
        self,
        day: int,
        session: int,
        time_of_day: float
    ) -> Optional[Patient]:
        """
        Select next patient for scheduling, applying clinical override logic if applicable.

        Args:
            day: Current simulation day
            session: Session number
            time_of_day: Normalized time of day factor [-0.5, +0.5]

        Returns:
            Selected patient, or None if backlog is empty
        """
        if not self.backlog:
            return None

        # Sort by AI priority (higher pred_risk first, urgent before routine)
        self.backlog.sort(
            key=lambda p: (p.pred_risk, p.pclass == "urgent"),
            reverse=True
        )

        candidate = self.backlog[0]
        overridden = False

        # Apply clinical override logic for hybrid scenario
        if self.cfg.sim.scenario == "hybrid":
            candidate, overridden = self._apply_clinical_override(
                candidate, day, session, time_of_day
            )

        return candidate

    def _apply_clinical_override(
        self,
        ai_recommendation: Patient,
        day: int,
        session: int,
        time_of_day: float
    ) -> Tuple[Patient, bool]:
        """
        Determine if clinician overrides AI recommendation and select alternative.

        Args:
            ai_recommendation: Patient recommended by AI (top of sorted backlog)
            day: Current simulation day
            session: Session number
            time_of_day: Normalized time of day factor

        Returns:
            Tuple of (selected_patient, was_overridden)
        """
        uncertainty = 1.0 - ai_recommendation.confidence
        q_signal = math.log1p(len(self.backlog))  # backlog pressure
        clinician_re = float(
            self.rng.normal(0, self.cfg.overrides.sd_clinician_random_effect)
        )

        # Calculate override probability
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

        # Decide whether to override
        overridden = self.rng.random() < prob
        if overridden:
            # Pick alternative: next in line or FCFS
            alt_idx = 1 if len(self.backlog) > 1 else 0
            selected = self.backlog[alt_idx]
        else:
            selected = ai_recommendation

        # Log the decision
        self.override_log.append({
            "day": day,
            "session": session,
            "queue_len": len(self.backlog),
            "pid": selected.pid,
            "uncertainty": float(uncertainty),
            "time_of_day": float(time_of_day),
            "overridden": overridden,
            "prob": float(prob)
        })

        return selected, overridden

    def _handle_appointment(self, patient: Patient, day: int) -> None:
        """
        Process patient appointment: schedule, check for no-show, handle outcome.

        Args:
            patient: Patient to schedule
            day: Current simulation day
        """
        # Remove from backlog
        self.backlog.remove(patient)
        patient.scheduled_day = day

        # Determine if patient shows up
        no_show_p = self.cfg.no_show.probability
        patient.no_show = bool(self.rng.random() < no_show_p)

        if patient.no_show:
            # Handle no-show based on reschedule rule
            if self.cfg.no_show.reschedule_rule == "backlog":
                # Re-enter backlog (maintains original arrival_day)
                self.backlog.append(patient)
            else:
                # Drop from system
                patient.attended = False
                self.patients.append(patient)
        else:
            # Patient attended
            patient.attended = True
            self.patients.append(patient)

    def _finalize_results(self) -> pd.DataFrame:
        """
        Convert simulation results to DataFrame and compute breach flags.

        Returns:
            Complete results DataFrame
        """
        # Combine attended patients and remaining backlog
        all_patients = self.patients + self.backlog

        df = pd.DataFrame([p.__dict__ for p in all_patients])
        df["wait_days"] = df["wait_days"].fillna(0.0)

        # Compute breach flags
        df["breach_same_day"] = df["wait_days"] > self.cfg.thresholds_days.same_day
        df["breach_3d"] = df["wait_days"] > self.cfg.thresholds_days.within_3d
        df["breach_14d"] = df["wait_days"] > self.cfg.thresholds_days.within_14d

        # Ensure pred_risk exists
        if "pred_risk" not in df.columns:
            df["pred_risk"] = 0.5

        return df
