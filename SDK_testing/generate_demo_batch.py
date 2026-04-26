from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from SDK.monitor.supabase_client import SupabaseEventClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate synthetic prediction events for dashboard demos.")
    parser.add_argument("--model-name", required=True, type=str, help="Model name to write rows under.")
    parser.add_argument("--rows", default=1500, type=int, help="Number of synthetic rows to insert.")
    parser.add_argument("--source", default="demo_polish", type=str, help="Source field for inserted rows.")
    parser.add_argument("--seed", default=42, type=int, help="Random seed for deterministic generation.")
    return parser


def _sample_attrs(rng: np.random.Generator) -> Dict[str, str]:
    ethnicity = rng.choice(
        ["African American", "Caucasian", "Hispanic", "Asian"],
        p=[0.24, 0.48, 0.18, 0.10],
    )
    gender = rng.choice(["Female", "Male"], p=[0.52, 0.48])
    age_group = rng.choice(["18-45", "46-65", "over_65"], p=[0.30, 0.40, 0.30])
    region = rng.choice(["North", "South", "East", "West"], p=[0.30, 0.25, 0.20, 0.25])
    return {
        "ethnicity": str(ethnicity),
        "gender": str(gender),
        "age_group": str(age_group),
        "region": str(region),
    }


def _biased_probability(attrs: Dict[str, str], base_signal: float) -> float:
    bias = 0.0
    if attrs["age_group"] == "over_65":
        bias -= 0.14
    if attrs["ethnicity"] == "African American":
        bias -= 0.09
    if attrs["gender"] == "Female" and attrs["age_group"] == "over_65":
        bias -= 0.08
    if attrs["region"] == "South":
        bias -= 0.03
    z = base_signal + bias
    return float(1.0 / (1.0 + np.exp(-z)))


def build_rows(model_name: str, rows: int, source: str, seed: int) -> List[Dict[str, object]]:
    rng = np.random.default_rng(seed)
    now_iso = datetime.now(timezone.utc).isoformat()
    payload: List[Dict[str, object]] = []
    for idx in range(rows):
        attrs = _sample_attrs(rng)
        base_signal = float(rng.normal(loc=0.2, scale=1.1))
        pred = _biased_probability(attrs, base_signal)
        true_logit = base_signal + float(rng.normal(loc=0.0, scale=0.7))
        y_true = int((1.0 / (1.0 + np.exp(-true_logit))) > 0.55)
        payload.append(
            {
                "created_at": now_iso,
                "model_name": model_name,
                "y_pred_proba": round(pred, 6),
                "y_true": y_true,
                "attrs": attrs,
                "source": source,
                "patient_id": f"demo_{seed}_{idx}",
            }
        )
    return payload


def main() -> None:
    args = build_parser().parse_args()
    if args.rows <= 0:
        raise ValueError("--rows must be > 0")

    client = SupabaseEventClient()
    rows = build_rows(args.model_name, args.rows, args.source, args.seed)
    inserted = client.insert_prediction_events(rows)

    print("[PASS] synthetic demo batch inserted")
    print(f"model_name={args.model_name}")
    print(f"rows_requested={len(rows)}")
    print(f"rows_inserted={len(inserted)}")


if __name__ == "__main__":
    main()
