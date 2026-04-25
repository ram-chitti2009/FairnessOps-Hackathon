from __future__ import annotations

import pandas as pd

from SDK.workers.config import WorkerConfig


def prepare_scored_frame(df: pd.DataFrame, cfg: WorkerConfig) -> pd.DataFrame:
    work = df.dropna(subset=["y_true", "y_pred_proba"]).copy()
    if work.empty:
        return work
    work["y_true"] = work["y_true"].astype(int)
    work["y_pred_proba"] = pd.to_numeric(work["y_pred_proba"], errors="coerce")
    work = work.dropna(subset=["y_pred_proba"])
    for c in cfg.protected_attrs:
        if c in work.columns:
            work[c] = work[c].astype("object").fillna("Unknown")
    return work


def fairness_severity(gap: float, cfg: WorkerConfig) -> str:
    if pd.isna(gap):
        return "INSUFFICIENT_DATA"
    if gap > cfg.fairness_red_gap:
        return "RED"
    if gap > cfg.fairness_yellow_gap:
        return "YELLOW"
    return "GREEN"


def representation_status(n_eff: float, cfg: WorkerConfig) -> str:
    if n_eff >= cfg.rep_reliable_neff:
        return "reliable"
    if n_eff >= cfg.rep_low_conf_neff:
        return "low_confidence"
    return "suppressed"


def drift_alert(slope: float, cfg: WorkerConfig) -> str:
    if pd.isna(slope):
        return "INSUFFICIENT_DATA"
    if slope > cfg.drift_red_slope:
        return "RED"
    if slope > cfg.drift_yellow_slope:
        return "YELLOW"
    return "GREEN"
