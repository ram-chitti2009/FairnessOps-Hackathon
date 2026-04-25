from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from SDK import AuditConfig, run_audit


SCENARIO_ROOT = ROOT / "controlled_synthetic_bias" / "results"
OUT_ROOT = ROOT / "runs" / "sdk_test_outputs" / "scenarios"

SCENARIOS = [
    "baseline",
    "ethnicity_downweight",
    "female_over65_downweight",
    "region_drift_like",
]


def run_one(scenario: str) -> dict:
    src = SCENARIO_ROOT / scenario / "predictions.csv"
    if not src.exists():
        raise FileNotFoundError(f"Missing scenario predictions: {src}")

    df = pd.read_csv(src)
    cfg = AuditConfig(output_root=str(OUT_ROOT), run_prefix=f"sdk_{scenario}")
    result = run_audit(df, cfg)

    fba = result.outputs["fairness_by_attribute"]
    max_gap = float(fba["max_auc_gap"].max())
    red_count = int((fba["severity"] == "RED").sum())
    return {
        "scenario": scenario,
        "run_id": result.run_id,
        "overall_status": result.overall_status,
        "max_auc_gap": round(max_gap, 6),
        "red_attr_count": red_count,
        "n_top_alerts": len(result.top_alerts),
        "output_dir": str(result.output_dir),
    }


def main() -> None:
    rows = [run_one(s) for s in SCENARIOS]
    summary = pd.DataFrame(rows)
    out_path = OUT_ROOT / "scenario_test_summary.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_path, index=False)

    print("[PASS] SDK scenario regression test")
    print(f"Summary: {out_path}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
