from __future__ import annotations

from typing import Iterable

import pandas as pd

from .config import AuditConfig


def _require_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def validate_input(df: pd.DataFrame, config: AuditConfig) -> None:
    """Validate minimal input contract for SDK pipeline."""
    required = [config.label_col, config.score_col] + config.protected_attributes
    if config.id_col in df.columns:
        required.append(config.id_col)
    _require_columns(df, required)

    y = df[config.label_col]
    if y.isna().any():
        raise ValueError(f"`{config.label_col}` contains null values.")
    allowed = set(pd.Series(y).dropna().unique().tolist())
    if not allowed.issubset({0, 1}):
        raise ValueError(f"`{config.label_col}` must be binary (0/1). Found: {sorted(allowed)}")

    s = pd.to_numeric(df[config.score_col], errors="coerce")
    if s.isna().any():
        raise ValueError(f"`{config.score_col}` contains non-numeric or null values.")
    if (s < 0).any() or (s > 1).any():
        raise ValueError(f"`{config.score_col}` must be in [0, 1].")
