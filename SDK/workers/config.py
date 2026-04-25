from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class WorkerConfig:
    model_name: str
    protected_attrs: List[str]
    window_n: int = 5000
    min_group_n_auc: int = 30
    inter_min_group_n: int = 20
    inter_top_k: int = 25
    drift_windows: int = 6
    drift_red_slope: float = 0.02
    drift_yellow_slope: float = 0.005
    rep_reliable_neff: float = 30.0
    rep_low_conf_neff: float = 10.0
    fairness_red_gap: float = 0.20
    fairness_yellow_gap: float = 0.10
    audit_schema_version: str = "1.0.0"
    pipeline_version: str = "0.1.0"
    random_state: int = 42
