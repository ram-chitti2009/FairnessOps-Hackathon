from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from SDK.workers.compute.common import representation_status
from SDK.workers.config import WorkerConfig


def compute_representation_outputs(df: pd.DataFrame, cfg: WorkerConfig) -> pd.DataFrame:
    work = df.copy()
    if work.empty:
        return pd.DataFrame(columns=["attribute", "group", "n", "positive_rate", "n_eff", "status"])

    work["y_true"] = pd.to_numeric(work["y_true"], errors="coerce")
    work = work.dropna(subset=["y_true"])
    if work.empty:
        return pd.DataFrame(columns=["attribute", "group", "n", "positive_rate", "n_eff", "status"])
    work["y_true"] = work["y_true"].astype(int)
    for c in cfg.protected_attrs:
        if c in work.columns:
            work[c] = work[c].astype("object").fillna("Unknown")

    rows: List[Dict[str, Any]] = []
    for attr in cfg.protected_attrs:
        if attr not in work.columns:
            continue
        for group, sub in work.groupby(attr):
            n = len(sub)
            p_pos = float(sub["y_true"].mean())
            n_eff = float(n * 2 * min(p_pos, 1 - p_pos))
            rows.append(
                {
                    "attribute": attr,
                    "group": group,
                    "n": int(n),
                    "positive_rate": p_pos,
                    "n_eff": n_eff,
                    "status": representation_status(n_eff, cfg),
                }
            )
    return pd.DataFrame(rows).sort_values(["attribute", "n"], ascending=[True, False])
