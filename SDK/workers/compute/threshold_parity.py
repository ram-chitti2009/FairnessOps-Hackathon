from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from SDK.workers.compute.common import prepare_scored_frame
from SDK.workers.config import WorkerConfig


def _parity_severity(gap: float, cfg: WorkerConfig) -> str:
    if pd.isna(gap):
        return "INSUFFICIENT_DATA"
    if gap >= cfg.threshold_parity_red_gap:
        return "RED"
    if gap >= cfg.threshold_parity_yellow_gap:
        return "YELLOW"
    return "GREEN"


def compute_threshold_parity_outputs(df: pd.DataFrame, cfg: WorkerConfig) -> pd.DataFrame:
    """Compute threshold parity per protected attribute.

    Output includes:
      - one row per subgroup with its positive_rate_at_threshold
      - one summary row per attribute with parity_gap + severity
    """
    work = prepare_scored_frame(df, cfg)
    cols = [
        "attribute",
        "subgroup",
        "positive_rate_at_threshold",
        "parity_gap",
        "severity",
        "row_kind",
    ]
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
                    "positive_rate_at_threshold": np.nan,
                    "parity_gap": np.nan,
                    "severity": "INSUFFICIENT_DATA",
                    "row_kind": "summary",
                }
            )
            continue

        rates: List[float] = []
        for group, sub in work.groupby(attr):
            rate = float(sub["y_hat"].mean()) if len(sub) > 0 else np.nan
            rates.append(rate)
            rows.append(
                {
                    "attribute": attr,
                    "subgroup": str(group),
                    "positive_rate_at_threshold": rate,
                    "parity_gap": np.nan,
                    "severity": "",
                    "row_kind": "group",
                }
            )

        gap = (max(rates) - min(rates)) if len(rates) >= 2 else np.nan
        rows.append(
            {
                "attribute": attr,
                "subgroup": None,
                "positive_rate_at_threshold": np.nan,
                "parity_gap": float(gap) if pd.notna(gap) else np.nan,
                "severity": _parity_severity(gap, cfg),
                "row_kind": "summary",
            }
        )

    return pd.DataFrame(rows, columns=cols)

