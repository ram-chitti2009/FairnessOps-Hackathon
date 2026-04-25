from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from SDK.workers.compute.common import prepare_scored_frame
from SDK.workers.config import WorkerConfig


def compute_intersectionality_outputs(df: pd.DataFrame, cfg: WorkerConfig) -> Tuple[pd.DataFrame, pd.DataFrame]:
    work = prepare_scored_frame(df, cfg)
    columns = [
        "attr1",
        "group1",
        "attr2",
        "group2",
        "n",
        "n_eff",
        "auc_subgroup",
        "auc_overall",
        "gap_vs_overall",
        "score",
    ]
    if work.empty or work["y_true"].nunique() < 2:
        empty = pd.DataFrame(columns=columns)
        return empty, empty

    overall_auc = float(roc_auc_score(work["y_true"], work["y_pred_proba"]))
    rows: List[Dict[str, Any]] = []
    for a1, a2 in combinations(cfg.protected_attrs, 2):
        if a1 not in work.columns or a2 not in work.columns:
            continue
        for (g1, g2), sub in work.groupby([a1, a2]):
            n = len(sub)
            if n < cfg.inter_min_group_n or sub["y_true"].nunique() < 2:
                continue
            auc_sub = float(roc_auc_score(sub["y_true"], sub["y_pred_proba"]))
            gap = overall_auc - auc_sub
            p_pos = float(sub["y_true"].mean())
            n_eff = float(n * 2 * min(p_pos, 1 - p_pos))
            score = float(gap * np.sqrt(max(n_eff, 1)))
            rows.append(
                {
                    "attr1": a1,
                    "group1": g1,
                    "attr2": a2,
                    "group2": g2,
                    "n": int(n),
                    "n_eff": n_eff,
                    "auc_subgroup": auc_sub,
                    "auc_overall": overall_auc,
                    "gap_vs_overall": float(gap),
                    "score": score,
                }
            )
    all_df = pd.DataFrame(rows, columns=columns)
    if not all_df.empty:
        all_df = all_df.sort_values("score", ascending=False)
    top_df = all_df.head(cfg.inter_top_k).copy() if not all_df.empty else all_df.copy()
    return all_df, top_df
