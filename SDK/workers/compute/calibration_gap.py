from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from SDK.workers.compute.common import prepare_scored_frame
from SDK.workers.config import WorkerConfig


def _calibration_severity(gap: float, cfg: WorkerConfig) -> str:
    if pd.isna(gap):
        return "INSUFFICIENT_DATA"
    if gap >= cfg.calibration_red_gap:
        return "RED"
    if gap >= cfg.calibration_yellow_gap:
        return "YELLOW"
    return "GREEN"


def compute_calibration_gap_outputs(df: pd.DataFrame, cfg: WorkerConfig) -> pd.DataFrame:
    """Compute subgroup calibration error and attribute-level calibration gap.

    Calibration error per subgroup is absolute difference between:
      - average predicted risk
      - observed event rate
    """
    work = prepare_scored_frame(df, cfg)
    cols = [
        "attribute",
        "subgroup",
        "mean_pred",
        "observed_rate",
        "calibration_error",
        "calibration_gap",
        "severity",
        "row_kind",
    ]
    if work.empty:
        return pd.DataFrame(columns=cols)

    rows: List[Dict[str, Any]] = []
    for attr in cfg.protected_attrs:
        if attr not in work.columns:
            rows.append(
                {
                    "attribute": attr,
                    "subgroup": None,
                    "mean_pred": np.nan,
                    "observed_rate": np.nan,
                    "calibration_error": np.nan,
                    "calibration_gap": np.nan,
                    "severity": "INSUFFICIENT_DATA",
                    "row_kind": "summary",
                }
            )
            continue

        errors: List[float] = []
        for group, sub in work.groupby(attr):
            mean_pred = float(sub["y_pred_proba"].mean()) if len(sub) > 0 else np.nan
            obs_rate = float(sub["y_true"].mean()) if len(sub) > 0 else np.nan
            cal_err = abs(mean_pred - obs_rate) if pd.notna(mean_pred) and pd.notna(obs_rate) else np.nan
            if pd.notna(cal_err):
                errors.append(float(cal_err))

            rows.append(
                {
                    "attribute": attr,
                    "subgroup": str(group),
                    "mean_pred": mean_pred,
                    "observed_rate": obs_rate,
                    "calibration_error": float(cal_err) if pd.notna(cal_err) else np.nan,
                    "calibration_gap": np.nan,
                    "severity": "",
                    "row_kind": "group",
                }
            )

        gap = (max(errors) - min(errors)) if len(errors) >= 2 else np.nan
        rows.append(
            {
                "attribute": attr,
                "subgroup": None,
                "mean_pred": np.nan,
                "observed_rate": np.nan,
                "calibration_error": np.nan,
                "calibration_gap": float(gap) if pd.notna(gap) else np.nan,
                "severity": _calibration_severity(gap, cfg),
                "row_kind": "summary",
            }
        )

    return pd.DataFrame(rows, columns=cols)

