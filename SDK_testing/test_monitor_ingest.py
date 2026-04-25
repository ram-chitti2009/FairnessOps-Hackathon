from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from SDK import monitor
from SDK.monitor.supabase_client import SupabaseConfig




def main() -> None:
    model_name = f"monitor_ingest_smoke_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    batch_size = 10

    # Minimal prediction input with protected attributes + one feature.
    X = pd.DataFrame(
        {
            "ethnicity": ["African American", "Caucasian"] * 5,
            "gender": ["Female", "Male"] * 5,
            "age_group": ["over_65", "18-45", "46-65", "over_65", "18-45"] * 2,
            "feature_score": np.linspace(-1.5, 1.5, batch_size),
        }
    )
    y_true = [0, 1] * 5
    patient_ids = [f"pt_{i}" for i in range(batch_size)]

    @monitor(
        protected_attrs=["ethnicity", "gender", "age_group"],
        model_name=model_name,
        source="sdk_testing",
    )
    def predict(df: pd.DataFrame) -> np.ndarray:
        # Deterministic pseudo-probabilities in [0, 1].
        return 1.0 / (1.0 + np.exp(-df["feature_score"].to_numpy()))

    preds = predict(X, y_true=y_true, patient_ids=patient_ids)
    if len(preds) != batch_size:
        raise AssertionError(f"Expected {batch_size} predictions, got {len(preds)}")

    # Query back rows for this model_name as end-to-end ingestion verification.
    cfg = SupabaseConfig.from_env()
    from supabase import create_client  # type: ignore

    client = create_client(cfg.url, cfg.key)
    result = (
        client.schema(cfg.schema)
        .table(cfg.prediction_table)
        .select("event_id, model_name, y_pred_proba, y_true, attrs, source")
        .eq("model_name", model_name)
        .order("event_id", desc=True)
        .limit(batch_size)
        .execute()
    )
    rows = list(result.data or [])
    if len(rows) < batch_size:
        raise AssertionError(
            f"Ingestion check failed: expected at least {batch_size} rows for {model_name}, got {len(rows)}"
        )

    print("[PASS] monitor ingestion smoke test")
    print(f"Model name: {model_name}")
    print(f"Predictions returned: {len(preds)}")
    print(f"Rows verified in Supabase: {len(rows)}")


if __name__ == "__main__":
    main()
