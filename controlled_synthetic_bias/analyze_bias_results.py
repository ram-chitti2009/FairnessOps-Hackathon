from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "controlled_synthetic_bias" / "results"


def df_to_markdown(df: pd.DataFrame) -> str:
    """Convert DataFrame to a simple markdown table without optional deps."""
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for _, row in df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if pd.isna(v):
                vals.append("")
            elif isinstance(v, float):
                vals.append(f"{v:.6f}")
            else:
                vals.append(str(v))
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep] + rows)


def load_attr_gap(scenario: str) -> pd.DataFrame:
    p = RESULTS / scenario / "fairness_by_attribute.csv"
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    df = pd.read_csv(p)
    return df[["attribute", "max_auc_gap", "severity"]].copy()


def load_representation(scenario: str) -> pd.DataFrame:
    p = RESULTS / scenario / "representation.csv"
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return pd.read_csv(p)


def load_drift(scenario: str) -> pd.DataFrame:
    p = RESULTS / scenario / "fairness_drift_summary.csv"
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return pd.read_csv(p)


def expected_behavior_checks() -> Dict[str, str]:
    """Return pass/fail checks for synthetic bias validation."""
    checks: Dict[str, str] = {}

    baseline = load_attr_gap("baseline").set_index("attribute")
    eth = load_attr_gap("ethnicity_downweight").set_index("attribute")
    female65 = load_attr_gap("female_over65_downweight").set_index("attribute")
    region = load_attr_gap("region_drift_like").set_index("attribute")

    # Check 1: Ethnicity-targeted bias should increase ethnicity fairness gap.
    checks["ethnicity_gap_increases_under_ethnicity_downweight"] = (
        "PASS"
        if eth.loc["ethnicity", "max_auc_gap"] > baseline.loc["ethnicity", "max_auc_gap"]
        else "FAIL"
    )

    # Check 2: Female+over_65 targeted bias should increase at least one of gender/age_group gaps.
    gender_up = female65.loc["gender", "max_auc_gap"] > baseline.loc["gender", "max_auc_gap"]
    age_up = female65.loc["age_group", "max_auc_gap"] > baseline.loc["age_group", "max_auc_gap"]
    checks["female_over65_bias_increases_gender_or_age_gap"] = (
        "PASS" if (gender_up or age_up) else "FAIL"
    )

    # Check 3: Region-targeted drift-like bias should not reduce region gap.
    checks["region_gap_non_decreasing_under_region_drift_like"] = (
        "PASS"
        if region.loc["region", "max_auc_gap"] >= baseline.loc["region", "max_auc_gap"]
        else "FAIL"
    )

    # Check 4: Representation status counts should remain mostly stable (bias changes score, not sample composition).
    base_rep = load_representation("baseline")["status"].value_counts().to_dict()
    eth_rep = load_representation("ethnicity_downweight")["status"].value_counts().to_dict()
    checks["representation_status_stable_after_score_only_bias"] = (
        "PASS" if base_rep == eth_rep else "WARN"
    )

    # Check 5: Region drift-like scenario should produce non-green region drift more often.
    base_drift = load_drift("baseline").set_index("attribute")
    reg_drift = load_drift("region_drift_like").set_index("attribute")
    base_alert = str(base_drift.loc["region", "drift_alert"])
    reg_alert = str(reg_drift.loc["region", "drift_alert"])
    checks["region_drift_alert_not_weaker_in_region_drift_like"] = (
        "PASS"
        if (base_alert == reg_alert or (base_alert == "GREEN" and reg_alert in {"YELLOW", "RED"}))
        else "WARN"
    )

    return checks


def build_report() -> str:
    scenario_cmp = pd.read_csv(RESULTS / "scenario_comparison.csv")

    scenarios = [
        "baseline",
        "ethnicity_downweight",
        "female_over65_downweight",
        "region_drift_like",
    ]

    section_lines = []
    for s in scenarios:
        attr = load_attr_gap(s).sort_values("max_auc_gap", ascending=False)
        top = attr.head(2).copy()
        rep = load_representation(s)
        rep_counts = rep["status"].value_counts().to_dict()
        drift = load_drift(s)
        section_lines.append(f"### {s}")
        section_lines.append(df_to_markdown(top))
        section_lines.append(f"- Representation status counts: `{rep_counts}`")
        section_lines.append(f"- Drift alerts: `{drift[['attribute','drift_alert']].to_dict(orient='records')}`")
        section_lines.append("")

    checks = expected_behavior_checks()
    checks_md = df_to_markdown(
        pd.DataFrame([{"check": k, "result": v} for k, v in checks.items()])
    )

    scenario_md = df_to_markdown(scenario_cmp)

    report = f"""# Controlled Synthetic Bias Validation Report

## Purpose
This report validates that the fairness pipeline reacts in the expected direction when we inject controlled synthetic biases into model prediction scores.

## Scenarios
- `baseline`
- `ethnicity_downweight` (subtract 0.15 probability for African American group)
- `female_over65_downweight` (subtract 0.20 probability for Female + over_65 intersection)
- `region_drift_like` (late-window subtraction for South region to emulate temporal degradation)

## Model Performance Summary
{scenario_md}

## Fairness Snapshot by Scenario
{chr(10).join(section_lines)}

## Validation Checks
{checks_md}

## Interpretation
- PASS checks indicate the pipeline is directionally sensitive to injected harms.
- WARN checks indicate either weak signal or thresholding behavior that should be reviewed, not necessarily pipeline failure.
- Because drift is window-simulated (not true timestamps), drift checks validate implementation behavior, not real-world temporal causality.
"""
    return report


def main() -> None:
    report = build_report()
    out_path = RESULTS / "VALIDATION_REPORT.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
