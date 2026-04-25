from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from SDK.workers.compute.common import fairness_severity, prepare_scored_frame
from SDK.workers.config import WorkerConfig


def compute_demographic_outputs(df: pd.DataFrame, cfg: WorkerConfig) -> pd.DataFrame:
    work = prepare_scored_frame(df, cfg)
    if work.empty or work["y_true"].nunique() < 2:
        return pd.DataFrame(columns=["attribute", "overall_auc", "max_auc_gap", "severity"])

    overall_auc = float(roc_auc_score(work["y_true"], work["y_pred_proba"]))
    rows: List[Dict[str, Any]] = []
    for attr in cfg.protected_attrs:
        if attr not in work.columns:
            rows.append(
                {
                    "attribute": attr,
                    "overall_auc": overall_auc,
                    "max_auc_gap": np.nan,
                    "severity": "INSUFFICIENT_DATA",
                }
            )
            continue
        aucs: List[float] = []
        for _, sub in work.groupby(attr):
            if len(sub) >= cfg.min_group_n_auc and sub["y_true"].nunique() >= 2:
                aucs.append(float(roc_auc_score(sub["y_true"], sub["y_pred_proba"])))
        gap = (max(aucs) - min(aucs)) if len(aucs) >= 2 else np.nan
        rows.append(
            {
                "attribute": attr,
                "overall_auc": overall_auc,
                "max_auc_gap": float(gap) if pd.notna(gap) else np.nan,
                "severity": fairness_severity(gap, cfg),
            }
        )
    return pd.DataFrame(rows)
