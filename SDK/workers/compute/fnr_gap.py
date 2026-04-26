from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from SDK.workers.compute.common import prepare_scored_frame
from SDK.workers.config import WorkerConfig


def _fnr_severity(gap: float, cfg: WorkerConfig) -> str:
    if pd.isna(gap):
        return "INSUFFICIENT_DATA"
    if gap >= cfg.fnr_red_gap:
        return "RED"
    if gap >= cfg.fnr_yellow_gap:
        return "YELLOW"
    return "GREEN"


def compute_fnr_gap_outputs(df: pd.DataFrame, cfg: WorkerConfig) -> pd.DataFrame:
    """Compute subgroup false-negative-rate and attribute-level FNR gap.

    Output includes:
      - one row per subgroup with fnr
      - one summary row per attribute with fnr_gap + severity
    """
    work = prepare_scored_frame(df, cfg)
    cols = ["attribute", "subgroup", "fnr", "fnr_gap", "n_pos", "severity", "row_kind"]
    if work.empty:
        return pd.DataFrame(columns=cols)

    threshold = float(cfg.operating_threshold)
    work["y_hat"] = (work["y_pred_proba"] >= threshold).astype(int)

    rows: List[Dict[str, Any]] = []
    for attr in cfg.protected_attrs:
        if attr not in work.columns:
            rows.append(
                {
                    "attribute": attr,
                    "subgroup": None,
                    "fnr": np.nan,
                    "fnr_gap": np.nan,
                    "n_pos": 0,
                    "severity": "INSUFFICIENT_DATA",
                    "row_kind": "summary",
                }
            )
            continue

        fnrs: List[float] = []
        for group, sub in work.groupby(attr):
            pos = sub[sub["y_true"] == 1]
            n_pos = int(len(pos))
            if n_pos == 0:
                fnr = np.nan
            else:
                fn = int(((pos["y_hat"] == 0)).sum())
                fnr = float(fn / n_pos)

            if pd.notna(fnr):
                fnrs.append(float(fnr))

            rows.append(
                {
                    "attribute": attr,
                    "subgroup": str(group),
                    "fnr": float(fnr) if pd.notna(fnr) else np.nan,
                    "fnr_gap": np.nan,
                    "n_pos": n_pos,
                    "severity": "",
                    "row_kind": "group",
                }
            )

        gap = (max(fnrs) - min(fnrs)) if len(fnrs) >= 2 else np.nan
        rows.append(
            {
                "attribute": attr,
                "subgroup": None,
                "fnr": np.nan,
                "fnr_gap": float(gap) if pd.notna(gap) else np.nan,
                "n_pos": int(work[work["y_true"] == 1].shape[0]),
                "severity": _fnr_severity(gap, cfg),
                "row_kind": "summary",
            }
        )

    return pd.DataFrame(rows, columns=cols)

