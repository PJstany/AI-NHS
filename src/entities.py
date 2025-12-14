from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Patient:
    pid: int
    subgroup: str         # "A" or "B"
    pclass: str           # "urgent" or "routine"
    true_risk: float
    pred_risk: float
    confidence: float
    arrival_day: int
    wait_days: float = 0.0
    scheduled_day: Optional[int] = None
    attended: Optional[bool] = None
    no_show: Optional[bool] = None
    overridden: Optional[bool] = None
    breach_same_day: Optional[bool] = None
    breach_3d: Optional[bool] = None
    breach_14d: Optional[bool] = None
    patience_days: float = field(default=7.0)
    reneged: bool = False          # True if patient abandoned queue (exceeded patience)
    reneged_day: Optional[int] = None  # Day when patient reneged

