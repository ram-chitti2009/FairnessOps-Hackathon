from __future__ import annotations

from functools import wraps
from typing import Callable, Iterable, Optional

import numpy as np
import pandas as pd

from .logger import PredictionLogger


def monitor(
    *,
    protected_attrs: list[str],
    model_name: str = "default_model",
    source: str = "sdk_decorator",
) -> Callable:
    """Decorator that intercepts predictions and logs them to Supabase.

    Expected wrapper call signature:
      predict(X, *args, y_true=None, patient_ids=None, **kwargs)
    """
    logger = PredictionLogger()

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapped(
            X: pd.DataFrame,
            *args,
            y_true: Optional[Iterable[int]] = None,
            patient_ids: Optional[Iterable[object]] = None,
            **kwargs,
        ):
            if not isinstance(X, pd.DataFrame):
                raise ValueError("monitor decorator expects X as a pandas DataFrame.")

            missing = [c for c in protected_attrs if c not in X.columns]
            if missing:
                raise ValueError(f"Missing protected attribute columns in X: {missing}")

            raw_pred = fn(X, *args, **kwargs)
            y_pred = np.asarray(raw_pred, dtype=float).reshape(-1)
            if len(y_pred) != len(X):
                raise ValueError(
                    f"Prediction length ({len(y_pred)}) must match X row count ({len(X)})."
                )

            attrs_df = X[protected_attrs].copy()
            logger.log_predictions(
                model_name=model_name,
                y_pred_proba=y_pred,
                attrs_df=attrs_df,
                y_true=y_true,
                patient_ids=patient_ids,
                source=source,
            )
            return raw_pred

        return wrapped

    return decorator
