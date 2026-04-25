from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from SDK import AuditConfig, run_audit


INPUT_CSV = ROOT / "controlled_synthetic_bias" / "results" / "baseline" / "predictions.csv"
OUT_ROOT = ROOT / "runs" / "sdk_test_outputs" / "smoke"

REQUIRED_FILES = [
    "fairness_by_attribute.csv",
    "fairness_by_group.csv",
    "representation.csv",
    "intersectionality_all.csv",
    "intersectionality_top.csv",
    "fairness_drift.csv",
    "fairness_drift_summary.csv",
    "dimension_summary.csv",
    "run_metadata.json",
]


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    cfg = AuditConfig(output_root=str(OUT_ROOT))
    result = run_audit(df, cfg)

    out_dir = Path(result.output_dir)
    missing = [name for name in REQUIRED_FILES if not (out_dir / name).exists()]
    if missing:
        raise AssertionError(f"Smoke test failed. Missing artifacts: {missing}")

    print("[PASS] SDK smoke test")
    print(f"Run ID: {result.run_id}")
    print(f"Status: {result.overall_status}")
    print(f"Artifacts: {out_dir}")


if __name__ == "__main__":
    main()
