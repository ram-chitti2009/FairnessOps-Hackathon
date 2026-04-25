from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from SDK.workers.compute.common import drift_alert, prepare_scored_frame
from SDK.workers.config import WorkerConfig


def compute_fairness_drift_outputs(df: pd.DataFrame, cfg: WorkerConfig) -> Tuple[pd.DataFrame, pd.DataFrame]:
    work = prepare_scored_frame(df, cfg)
    if work.empty or work["y_true"].nunique() < 2:
        return (
            pd.DataFrame(columns=["attribute", "window_id", "gap"]),
            pd.DataFrame(columns=["attribute", "gap_trend_slope", "drift_alert"]),
        )

    tmp = work.sample(frac=1, random_state=cfg.random_state).reset_index(drop=True)
    tmp["window_id"] = pd.cut(tmp.index, bins=cfg.drift_windows, labels=False, include_lowest=True)

    drift_rows: List[Dict[str, Any]] = []
    for attr in cfg.protected_attrs:
        if attr not in tmp.columns:
            continue
        for w, subw in tmp.groupby("window_id"):
            aucs = []
            for _, subg in subw.groupby(attr):
                if len(subg) < cfg.inter_min_group_n or subg["y_true"].nunique() < 2:
                    continue
                aucs.append(float(roc_auc_score(subg["y_true"], subg["y_pred_proba"])))
            gap_w = (max(aucs) - min(aucs)) if len(aucs) >= 2 else np.nan
            drift_rows.append({"attribute": attr, "window_id": int(w), "gap": gap_w})
    fairness_drift = pd.DataFrame(drift_rows)

    summary_rows: List[Dict[str, Any]] = []
    if not fairness_drift.empty:
        for attr, sub in fairness_drift.groupby("attribute"):
            s = sub.dropna(subset=["gap"]).sort_values("window_id")
            slope = np.polyfit(s["window_id"], s["gap"], 1)[0] if len(s) >= 2 else np.nan
            summary_rows.append(
                {
                    "attribute": attr,
                    "gap_trend_slope": float(slope) if pd.notna(slope) else np.nan,
                    "drift_alert": drift_alert(slope, cfg),
                }
            )
    return fairness_drift, pd.DataFrame(summary_rows)
