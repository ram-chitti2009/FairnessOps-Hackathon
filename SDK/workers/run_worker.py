from __future__ import annotations

# ── Ensure project root is on sys.path before any SDK imports ─────────────────
# This makes `python -m SDK.workers.run_worker` work from any working directory.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ─────────────────────────────────────────────────────────────────────────────

import argparse
import json
from typing import Any, Dict, Optional

import pandas as pd
from supabase import create_client  # type: ignore

from SDK.monitor.supabase_client import SupabaseConfig
from SDK.workers.compute import (
    compute_algorithmic_drift_outputs,
    compute_calibration_gap_outputs,
    compute_demographic_outputs,
    compute_feature_drift_outputs,
    compute_fairness_drift_outputs,
    compute_fnr_gap_outputs,
    compute_intersectionality_outputs,
    compute_representation_outputs,
    compute_threshold_parity_outputs,
)
from SDK.workers.config import WorkerConfig
from SDK.workers.data_access import fetch_rolling_events, insert_audit_run
from SDK.workers.persist import persist_all_dimensions



def compute_dimension_outputs(df: pd.DataFrame, cfg: WorkerConfig) -> Dict[str, pd.DataFrame]:
    demographic = compute_demographic_outputs(df, cfg)
    representation = compute_representation_outputs(df, cfg)
    inter_all, inter_top = compute_intersectionality_outputs(df, cfg)
    drift, drift_summary = compute_fairness_drift_outputs(df, cfg)
    algo_windows, algo_summary = compute_algorithmic_drift_outputs(df, cfg)
    threshold_parity = compute_threshold_parity_outputs(df, cfg)
    fnr_gap = compute_fnr_gap_outputs(df, cfg)
    calibration_gap = compute_calibration_gap_outputs(df, cfg)
    feature_drift = compute_feature_drift_outputs(df, cfg)
    return {
        "demographic": demographic,
        "representation": representation,
        "intersectionality_all": inter_all,
        "intersectionality_top": inter_top,
        "fairness_drift": drift,
        "fairness_drift_summary": drift_summary,
        "algorithmic_drift_windows": algo_windows,
        "algorithmic_drift_summary": algo_summary,
        "threshold_parity": threshold_parity,
        "fnr_gap": fnr_gap,
        "calibration_gap": calibration_gap,
        "feature_drift": feature_drift,
    }


def run_once(cfg: WorkerConfig) -> None:
    s_cfg = SupabaseConfig.from_env()
    client = create_client(s_cfg.url, s_cfg.key)
    df = fetch_rolling_events(client, s_cfg, cfg)
    if df.empty:
        print(f"No prediction events found for model_name={cfg.model_name}.")
        return

    outputs = compute_dimension_outputs(df, cfg)
    run_id = insert_audit_run(client, s_cfg, cfg, df)
    persist_all_dimensions(client, s_cfg, run_id, outputs, cfg)

    print("[PASS] worker run")
    print(f"run_id={run_id}")
    print(f"model_name={cfg.model_name}")
    print(f"window_rows={len(df)}")
    for name, out_df in outputs.items():
        print(f"{name}_rows={len(out_df)}")
    if not outputs["demographic"].empty:
        print(outputs["demographic"].to_string(index=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run one 9-dimension fairness worker pass.")
    p.add_argument("--model-name", required=True, type=str)
    p.add_argument(
        "--protected-attrs",
        nargs="+",
        default=["ethnicity", "gender", "age_group"],
        type=str,
    )
    p.add_argument("--window-n", default=5000, type=int)
    p.add_argument(
        "--clinical-context",
        default=None,
        type=str,
        metavar="JSON",
        help=(
            "JSON string with clinical metadata for the dashboard. "
            'Example: \'{"useCase":"Sepsis Screening","outcome":"flagged for intervention",'
            '"population":"Adult ICU","department":"Critical Care",'
            '"patientsPerMonth":840,"complianceNote":"CMS AI Transparency Rule (2025)"}\''
        ),
    )
    return p


def _parse_clinical_context(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("clinical-context must be a JSON object")
        return parsed
    except (json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"[ERROR] --clinical-context is not valid JSON: {exc}") from exc


def main() -> None:
    args = build_parser().parse_args()
    clinical = _parse_clinical_context(args.clinical_context)
    cfg = WorkerConfig(
        model_name=args.model_name,
        protected_attrs=args.protected_attrs,
        window_n=args.window_n,
        **({"clinical_context": clinical} if clinical else {}),
    )
    run_once(cfg)


if __name__ == "__main__":
    main()
