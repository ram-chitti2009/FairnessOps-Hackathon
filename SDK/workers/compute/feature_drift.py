from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp  # type: ignore

from SDK.workers.config import WorkerConfig


def _psi(reference: pd.Series, current: pd.Series, bins: int = 10, eps: float = 1e-6) -> float:
    """Population Stability Index between two numeric vectors."""
    # Quantile edges from reference; fallback to equally-spaced bins if degenerate.
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(reference, quantiles))
    if len(edges) < 3:
        lo = float(min(reference.min(), current.min()))
        hi = float(max(reference.max(), current.max()))
        if np.isclose(lo, hi):
            return 0.0
        edges = np.linspace(lo, hi, bins + 1)

    ref_hist, _ = np.histogram(reference, bins=edges)
    cur_hist, _ = np.histogram(current, bins=edges)
    p = ref_hist / max(ref_hist.sum(), 1)
    q = cur_hist / max(cur_hist.sum(), 1)
    p = np.clip(p.astype(float), eps, None)
    q = np.clip(q.astype(float), eps, None)
    return float(np.sum((q - p) * np.log(q / p)))


def _feature_drift_severity(ks_stat: float, ks_pvalue: float, psi: float) -> str:
    """Conservative severity combining KS and PSI signals."""
    if (ks_stat > 0.20 and ks_pvalue < 0.01) or psi >= 0.25:
        return "RED"
    if (ks_stat > 0.10 and ks_pvalue < 0.05) or psi >= 0.10:
        return "YELLOW"
    return "GREEN"


def compute_feature_drift_outputs(df: pd.DataFrame, cfg: WorkerConfig) -> pd.DataFrame:
    """Compute feature drift (KS + PSI) between reference and current windows.

    Reference window: earliest half of records
    Current window:   latest half of records
    """
    cols = ["attribute", "ks_stat", "ks_pvalue", "psi", "severity"]
    if df.empty:
        return pd.DataFrame(columns=cols)

    work = df.copy()
    # Choose numeric candidate features; exclude non-feature columns.
    excluded = {"event_id", "run_id", "y_true", "y_pred_proba", "created_at", "model_name"}
    numeric_features = [c for c in work.columns if c not in excluded and pd.api.types.is_numeric_dtype(work[c])]
    if not numeric_features:
        return pd.DataFrame(columns=cols)

    # Time order proxy by event_id if present, else original index.
    if "event_id" in work.columns:
        work = work.sort_values("event_id").reset_index(drop=True)
    else:
        work = work.reset_index(drop=True)

    n = len(work)
    if n < 20:
        return pd.DataFrame(columns=cols)
    split = n // 2
    ref = work.iloc[:split]
    cur = work.iloc[split:]

    rows: List[Dict[str, Any]] = []
    for feat in numeric_features:
        ref_vals = pd.to_numeric(ref[feat], errors="coerce").dropna()
        cur_vals = pd.to_numeric(cur[feat], errors="coerce").dropna()
        if len(ref_vals) < 10 or len(cur_vals) < 10:
            continue

        ks_stat, ks_p = ks_2samp(ref_vals.values, cur_vals.values)
        psi_val = _psi(ref_vals, cur_vals)
        rows.append(
            {
                "attribute": feat,
                "ks_stat": float(ks_stat),
                "ks_pvalue": float(ks_p),
                "psi": float(psi_val),
                "severity": _feature_drift_severity(float(ks_stat), float(ks_p), float(psi_val)),
            }
        )

    return pd.DataFrame(rows, columns=cols)

