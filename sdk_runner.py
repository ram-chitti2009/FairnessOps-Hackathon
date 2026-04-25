from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from SDK import AuditConfig, run_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run FairnessOps SDK audit from a predictions CSV."
    )
    parser.add_argument(
        "--input-csv",
        type=str,
        required=True,
        help="Path to CSV with y_true, y_pred_proba, and protected attributes.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="runs/sdk_outputs",
        help="Directory where run artifacts are written.",
    )
    parser.add_argument(
        "--label-col",
        type=str,
        default="y_true",
        help="Ground-truth label column (binary 0/1).",
    )
    parser.add_argument(
        "--score-col",
        type=str,
        default="y_pred_proba",
        help="Prediction score/probability column in [0,1].",
    )
    parser.add_argument(
        "--id-col",
        type=str,
        default="patientunitstayid",
        help="Optional ID column name.",
    )
    parser.add_argument(
        "--protected-attrs",
        type=str,
        nargs="+",
        default=["ethnicity", "gender", "age_group", "region"],
        help="Protected attribute columns to audit.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_csv = Path(args.input_csv)
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    df = pd.read_csv(input_csv)

    cfg = AuditConfig(
        protected_attributes=args.protected_attrs,
        label_col=args.label_col,
        score_col=args.score_col,
        id_col=args.id_col,
        output_root=args.output_root,
    )
    result = run_audit(df, cfg)

    print("FairnessOps SDK audit complete.")
    print(f"Run ID:         {result.run_id}")
    print(f"Overall status: {result.overall_status}")
    print(f"Output folder:  {result.output_dir}")
    if result.top_alerts:
        print("Top alerts:")
        for a in result.top_alerts:
            print(f" - {a}")
    else:
        print("Top alerts: none")


if __name__ == "__main__":
    main()
