from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from SDK.workers.compute.common import prepare_scored_frame
from SDK.workers.config import WorkerConfig


def _algo_drift_severity(auc_drop: float, cfg: WorkerConfig) -> str:
    if pd.isna(auc_drop):
        return "INSUFFICIENT_DATA"
    if auc_drop >= cfg.algo_drift_red_drop:
        return "RED"
    if auc_drop >= cfg.algo_drift_yellow_drop:
        return "YELLOW"
    return "GREEN"


def _detect_pelt_changepoints(series: np.ndarray, pen: float) -> List[int]:
    """Detect changepoints using PELT; returns 0-based indices."""
    if len(series) < 4:
        return []
    try:
        import ruptures as rpt  # type: ignore
    except Exception:
        return []

    algo = rpt.Pelt(model="rbf").fit(series.reshape(-1, 1))
    # ruptures returns 1-based end indices with final n included
    cps = algo.predict(pen=pen)
    return [int(i - 1) for i in cps if int(i) < len(series)]


def compute_algorithmic_drift_outputs(
    df: pd.DataFrame, cfg: WorkerConfig
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute overall model drift in AUC across rolling windows + PELT changepoints.

    Returns:
      - windows_df: per-window overall AUC and changepoint flag
      - summary_df: baseline/current auc, drop magnitude, changepoints, severity
    """
    work = prepare_scored_frame(df, cfg)
    if work.empty or work["y_true"].nunique() < 2:
        return (
            pd.DataFrame(columns=["window_id", "overall_auc", "is_changepoint"]),
            pd.DataFrame(
                columns=[
                    "baseline_auc",
                    "current_auc",
                    "auc_drop",
                    "n_windows",
                    "n_changepoints",
                    "changepoints",
                    "severity",
                ]
            ),
        )

    tmp = work.sample(frac=1, random_state=cfg.random_state).reset_index(drop=True)
    tmp["window_id"] = pd.cut(tmp.index, bins=cfg.drift_windows, labels=False, include_lowest=True)

    rows: List[Dict[str, Any]] = []
    for w, sub in tmp.groupby("window_id"):
        if sub["y_true"].nunique() < 2:
            auc = np.nan
        else:
            auc = float(roc_auc_score(sub["y_true"], sub["y_pred_proba"]))
        rows.append({"window_id": int(w), "overall_auc": auc})

    windows_df = pd.DataFrame(rows).sort_values("window_id").reset_index(drop=True)
    valid = windows_df.dropna(subset=["overall_auc"]).copy()
    if len(valid) < 2:
        windows_df["is_changepoint"] = False
        summary = pd.DataFrame(
            [
                {
                    "baseline_auc": np.nan,
                    "current_auc": np.nan,
                    "auc_drop": np.nan,
                    "n_windows": int(len(windows_df)),
                    "n_changepoints": 0,
                    "changepoints": "",
                    "severity": "INSUFFICIENT_DATA",
                }
            ]
        )
        return windows_df, summary

    auc_series = valid["overall_auc"].values.astype(float)
    cps = _detect_pelt_changepoints(auc_series, pen=cfg.algo_pelt_pen)

    baseline_auc = float(np.mean(auc_series[: max(1, len(auc_series) // 2)]))
    current_auc = float(auc_series[-1])
    auc_drop = float(max(0.0, baseline_auc - current_auc))
    severity = _algo_drift_severity(auc_drop, cfg)

    valid["is_changepoint"] = False
    for cp in cps:
        if 0 <= cp < len(valid):
            # cp is a 0-based positional index into auc_series / valid rows.
            # valid.index may have non-contiguous labels if any windows had NaN AUC
            # and were dropped, so use iloc (positional) not loc (label-based).
            valid.iloc[cp, valid.columns.get_loc("is_changepoint")] = True

    windows_df = windows_df.merge(
        valid[["window_id", "is_changepoint"]],
        on="window_id",
        how="left",
    )
    windows_df["is_changepoint"] = windows_df["is_changepoint"].fillna(False).astype(bool)

    summary = pd.DataFrame(
        [
            {
                "baseline_auc": baseline_auc,
                "current_auc": current_auc,
                "auc_drop": auc_drop,
                "n_windows": int(len(valid)),
                "n_changepoints": int(len(cps)),
                "changepoints": ",".join(str(i) for i in cps),
                "severity": severity,
            }
        ]
    )
    return windows_df, summary

