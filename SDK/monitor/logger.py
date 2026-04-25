from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from .supabase_client import SupabaseEventClient


class PredictionLogger:
    """Converts model outputs + demographics into Supabase event rows."""

    def __init__(self, client: Optional[SupabaseEventClient] = None) -> None:
        self.client = client or SupabaseEventClient()

    def log_predictions(
        self,
        *,
        model_name: str,
        y_pred_proba: Iterable[float],
        attrs_df: pd.DataFrame,
        y_true: Optional[Iterable[int]] = None,
        patient_ids: Optional[Iterable[object]] = None,
        source: str = "sdk_decorator",
    ) -> int:
        probs = np.asarray(list(y_pred_proba), dtype=float).reshape(-1)
        n = len(probs)

        if len(attrs_df) != n:
            raise ValueError("attrs_df row count must match prediction count.")
        if (probs < 0).any() or (probs > 1).any():
            raise ValueError("All prediction probabilities must be in [0, 1].")

        y_true_list = [None] * n if y_true is None else list(y_true)
        if len(y_true_list) != n:
            raise ValueError("y_true length must match prediction count.")

        patient_list = [None] * n if patient_ids is None else list(patient_ids)
        if len(patient_list) != n:
            raise ValueError("patient_ids length must match prediction count.")

        ts = datetime.now(timezone.utc).isoformat()
        rows = []
        for i in range(n):
            attrs = attrs_df.iloc[i].to_dict()
            rows.append(
                {
                    "created_at": ts,
                    "model_name": model_name,
                    "y_pred_proba": float(probs[i]),
                    "y_true": None if y_true_list[i] is None else int(y_true_list[i]),
                    "patient_id": None if patient_list[i] is None else str(patient_list[i]),
                    "attrs": attrs,
                    "source": source,
                }
            )

        self.client.insert_prediction_events(rows)
        return n
