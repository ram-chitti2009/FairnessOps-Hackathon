from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SMOKE_DIR = ROOT / "runs" / "sdk_test_outputs" / "smoke"


EXPECTED_SCHEMA = {
    "fairness_by_attribute.csv": {"attribute", "overall_auc", "max_auc_gap", "severity"},
    "fairness_by_group.csv": {"attribute", "group", "n", "auc"},
    "representation.csv": {"attribute", "group", "n", "positive_rate", "n_eff", "status"},
    "intersectionality_all.csv": {
        "attr1",
        "group1",
        "attr2",
        "group2",
        "n",
        "n_eff",
        "auc_subgroup",
        "auc_overall",
        "gap_vs_overall",
        "score",
    },
    "intersectionality_top.csv": {
        "attr1",
        "group1",
        "attr2",
        "group2",
        "n",
        "n_eff",
        "auc_subgroup",
        "auc_overall",
        "gap_vs_overall",
        "score",
    },
    "fairness_drift.csv": {"attribute", "window_id", "gap"},
    "fairness_drift_summary.csv": {"attribute", "gap_trend_slope", "drift_alert"},
    "dimension_summary.csv": {"dimension", "key_output_file", "headline_signal"},
}

VALID_SEVERITY = {"GREEN", "YELLOW", "RED", "INSUFFICIENT_DATA"}
VALID_REP_STATUS = {"reliable", "low_confidence", "suppressed"}


def latest_run_dir() -> Path:
    candidates = sorted(SMOKE_DIR.glob("audit_run_*"))
    if not candidates:
        raise FileNotFoundError("No smoke test run folder found. Run test_sdk_smoke.py first.")
    return candidates[-1]


def assert_columns(path: Path, expected: set[str]) -> None:
    df = pd.read_csv(path)
    missing = expected - set(df.columns)
    if missing:
        raise AssertionError(f"{path.name} missing columns: {sorted(missing)}")


def main() -> None:
    run_dir = latest_run_dir()

    for file_name, cols in EXPECTED_SCHEMA.items():
        path = run_dir / file_name
        if not path.exists():
            raise AssertionError(f"Missing required file: {path}")
        assert_columns(path, cols)

    fba = pd.read_csv(run_dir / "fairness_by_attribute.csv")
    bad_severity = sorted(set(fba["severity"].dropna().astype(str)) - VALID_SEVERITY)
    if bad_severity:
        raise AssertionError(f"Invalid fairness severity labels: {bad_severity}")

    rep = pd.read_csv(run_dir / "representation.csv")
    bad_rep = sorted(set(rep["status"].dropna().astype(str)) - VALID_REP_STATUS)
    if bad_rep:
        raise AssertionError(f"Invalid representation status labels: {bad_rep}")

    drift = pd.read_csv(run_dir / "fairness_drift_summary.csv")
    bad_drift = sorted(set(drift["drift_alert"].dropna().astype(str)) - VALID_SEVERITY)
    if bad_drift:
        raise AssertionError(f"Invalid drift alert labels: {bad_drift}")

    meta_path = run_dir / "run_metadata.json"
    if not meta_path.exists():
        raise AssertionError("Missing run_metadata.json")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    required_meta = {
        "run_id",
        "run_timestamp_utc",
        "audit_schema_version",
        "pipeline_version",
        "n_rows",
        "protected_attributes",
        "thresholds",
    }
    missing_meta = required_meta - set(metadata.keys())
    if missing_meta:
        raise AssertionError(f"Metadata missing keys: {sorted(missing_meta)}")

    print("[PASS] SDK output contract test")
    print(f"Checked run: {run_dir}")


if __name__ == "__main__":
    main()
