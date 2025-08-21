from __future__ import annotations
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Dict, List
import yaml, hashlib, json, os
from dataclasses import asdict

class SimCfg(BaseModel):
    days: int = Field(ge=1)
    sessions_per_day: int = Field(ge=1)
    slots_per_session: int = Field(ge=1)
    seeds: List[int]
    scenario: str
    utilization: float = Field(gt=0)

    @field_validator("scenario")
    @classmethod
    def scenario_ok(cls, v: str) -> str:
        if v not in {"baseline", "ai_only", "imperfect_ai", "hybrid"}:
            raise ValueError("scenario must be one of baseline|ai_only|imperfect_ai|hybrid")
        return v

class ArrivalsCfg(BaseModel):
    urgent_rate_per_day: float = Field(ge=0)
    routine_rate_per_day: float = Field(ge=0)
    digital_access_gap: Dict[str, float]

class PatienceCfg(BaseModel):
    urgent_mean: float = Field(gt=0)
    routine_mean: float = Field(gt=0)

class ServiceMixturesCfg(BaseModel):
    short_mean: float = Field(gt=0)
    long_mean: float = Field(gt=0)
    long_weight: float = Field(ge=0, le=1)

class NoShowCfg(BaseModel):
    probability: float = Field(ge=0, le=1)
    reschedule_rule: str

    @field_validator("reschedule_rule")
    @classmethod
    def rule_ok(cls, v: str) -> str:
        if v not in {"backlog", "drop"}:
            raise ValueError("reschedule_rule must be backlog|drop")
        return v

class BiasCalibCfg(BaseModel):
    slope: Dict[str, float]
    intercept: Dict[str, float]
    noise_sd: Dict[str, float]
    score_inflation: float = 0.0

class OverridesCfg(BaseModel):
    target_rate: float = Field(ge=0, le=1)
    beta_uncertainty: float
    beta_queue: float
    beta_time_of_day: float
    sd_clinician_random_effect: float

class ThresholdsCfg(BaseModel):
    same_day: int
    within_3d: int
    within_14d: int

class OutputCfg(BaseModel):
    out_dir: str
    write_overrides_log: bool = False

class AnalysisCfg(BaseModel):
    warmup_days: int = Field(ge=0, default=0)

class RootCfg(BaseModel):
    sim: SimCfg
    arrivals: ArrivalsCfg
    patience_days: PatienceCfg
    service_mixtures: ServiceMixturesCfg
    no_show: NoShowCfg
    bias_calibration: BiasCalibCfg
    overrides: OverridesCfg
    thresholds_days: ThresholdsCfg
    output: OutputCfg
    analysis: AnalysisCfg = AnalysisCfg()

def load_config(path: str) -> RootCfg:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)
    try:
        cfg = RootCfg(**raw)
    except ValidationError as e:
        raise SystemExit(f"Configuration validation failed:\n{e}") from e
    return cfg

def cfg_hash(cfg: RootCfg) -> str:
    # Generate a stable hash of the resolved config
    canonical = json.dumps(cfg.model_dump(), sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

def ensure_out_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
