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

    The Supabase connection is created lazily on the **first prediction call**,
    not at decoration/import time. This means SUPABASE_URL and SUPABASE_KEY only
    need to be set in the environment before the decorated function is first called,
    not before the module is imported.

    Expected wrapper call signature:
      predict(X, *args, y_true=None, patient_ids=None, **kwargs)
    """
    # Lazy holder — populated on first call.
    _state: dict = {"logger": None}

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

            # Initialise logger lazily so env vars are read at call time.
            if _state["logger"] is None:
                _state["logger"] = PredictionLogger()

            # Persist the full model input row (not only protected columns) so
            # downstream dimensions like Feature Drift can evaluate numeric shifts.
            attrs_df = X.copy()
            _state["logger"].log_predictions(
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
