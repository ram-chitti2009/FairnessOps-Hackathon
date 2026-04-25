from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AuditConfig:
    """Runtime config for fairness audit pipeline."""

    protected_attributes: List[str] = field(
        default_factory=lambda: ["ethnicity", "gender", "age_group", "region"]
    )
    label_col: str = "y_true"
    score_col: str = "y_pred_proba"
    id_col: str = "patientunitstayid"

    # Demographic fairness thresholds on max AUC gap.
    fairness_red_gap: float = 0.20
    fairness_yellow_gap: float = 0.10
    min_group_n_auc: int = 30

    # Representation thresholds on effective sample size.
    rep_reliable_neff: float = 30.0
    rep_low_conf_neff: float = 10.0

    # Intersectionality guardrails.
    inter_min_group_n: int = 20
    inter_top_k: int = 25

    # Drift thresholds on slope.
    drift_windows: int = 6
    drift_red_slope: float = 0.02
    drift_yellow_slope: float = 0.005

    # Export/runtime metadata.
    output_root: str = "runs/sdk_outputs"
    run_prefix: str = "audit_run"
    audit_schema_version: str = "1.0.0"
    pipeline_version: str = "0.1.0"
    random_state: int = 42

    def threshold_snapshot(self) -> Dict[str, float]:
        return {
            "fairness_red_gap": self.fairness_red_gap,
            "fairness_yellow_gap": self.fairness_yellow_gap,
            "rep_reliable_neff": self.rep_reliable_neff,
            "rep_low_conf_neff": self.rep_low_conf_neff,
            "drift_red_slope": self.drift_red_slope,
            "drift_yellow_slope": self.drift_yellow_slope,
        }
