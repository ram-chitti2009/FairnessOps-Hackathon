from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


def _default_clinical_context() -> Dict[str, Any]:
    """Baseline clinical context written to audit_runs.metadata when no custom context is set.

    Override any or all keys when constructing WorkerConfig so the dashboard
    shows accurate information instead of these generic defaults.
    Keys mirror the ModelContext interface in dashboard-next/lib/registry.ts.
    """
    return {
        "useCase": "Clinical Risk Model",
        "outcome": "flagged as high risk",
        "population": "General Inpatient",
        "department": "Clinical AI Programme",
        "patientsPerMonth": 1000,
        "complianceNote": "CMS AI Transparency & Bias Rule (2025)",
    }


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
    operating_threshold: float = 0.40
    threshold_parity_red_gap: float = 0.20
    threshold_parity_yellow_gap: float = 0.10
    fnr_red_gap: float = 0.20
    fnr_yellow_gap: float = 0.10
    calibration_red_gap: float = 0.10
    calibration_yellow_gap: float = 0.05
    algo_drift_red_drop: float = 0.10
    algo_drift_yellow_drop: float = 0.05
    algo_pelt_pen: float = 1.0
    rep_reliable_neff: float = 30.0
    rep_low_conf_neff: float = 10.0
    fairness_red_gap: float = 0.20
    fairness_yellow_gap: float = 0.10
    audit_schema_version: str = "1.0.0"
    pipeline_version: str = "0.1.0"
    random_state: int = 42
    # Clinical context written to audit_runs.metadata so the dashboard can display
    # human-readable model information. Defaults to generic labels — always override
    # with your model's actual use-case, outcome, and patient population.
    # Keys: useCase, outcome, population, department, patientsPerMonth, complianceNote
    clinical_context: Dict[str, Any] = field(default_factory=_default_clinical_context)
