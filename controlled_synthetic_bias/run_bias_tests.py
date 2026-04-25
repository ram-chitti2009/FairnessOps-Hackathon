from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

"""Controlled synthetic bias experiment for FairnessOps MVP.

This script:
1) Loads canonical patient-stay dataset.
2) Trains a logistic regression baseline and creates holdout predictions.
3) Injects controlled score perturbations for specific protected groups.
4) Recomputes all four fairness dimensions for each scenario.
5) Exports per-scenario outputs plus a scenario-level comparison table.

The goal is *validation by intervention*: when known bias is injected, fairness
metrics should change in the expected direction.
"""


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SRC = ROOT / "runs" / "canonical_dataset.csv"
WORKDIR = ROOT / "controlled_synthetic_bias"
CANONICAL_COPY = WORKDIR / "canonical_dataset.csv"
OUTDIR = WORKDIR / "results"

FEATURE_COLS = [
    "lab_creatinine",
    "lab_sodium",
    "lab_glucose",
    "lab_potassium",
    "vital_heartrate",
    "vital_sao2",
    "vital_respiration",
    "apachescore",
]
ATTRS = ["ethnicity", "gender", "age_group", "region"]


def ensure_paths() -> None:
    """Prepare experiment directories and copy canonical input locally."""
    WORKDIR.mkdir(parents=True, exist_ok=True)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if not CANONICAL_SRC.exists():
        raise FileNotFoundError(f"Canonical dataset not found: {CANONICAL_SRC}")

    # Keep an explicit local copy for this experiment workspace.
    df = pd.read_csv(CANONICAL_SRC)
    df.to_csv(CANONICAL_COPY, index=False)


def build_prediction_frame(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Train baseline model and return holdout predictions + performance metrics."""
    for c in ATTRS:
        df[c] = df[c].astype("object").fillna("Unknown")
    df["y_true"] = df["y_true"].astype(int)

    X = df[FEATURE_COLS].copy()
    y = df["y_true"].copy()

    X_tr, X_te, y_tr, y_te, idx_tr, idx_te = train_test_split(
        X, y, df.index, test_size=0.25, random_state=42, stratify=y
    )

    pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    solver="liblinear",
                    random_state=42,
                ),
            ),
        ]
    )
    pipe.fit(X_tr, y_tr)
    proba_te = pipe.predict_proba(X_te)[:, 1]

    pred_df = df.loc[idx_te, ["patientunitstayid", "y_true"] + ATTRS].copy()
    pred_df["y_pred_proba"] = proba_te.astype(float)

    metrics = {
        "overall_auc": float(roc_auc_score(y_te, proba_te)),
        "overall_pr_auc": float(average_precision_score(y_te, proba_te)),
        "n_test": int(len(pred_df)),
    }
    return pred_df.reset_index(drop=True), metrics


def compute_fairness_outputs(pred_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Compute the 4 MVP fairness dimensions from prediction frame."""
    overall_auc = roc_auc_score(pred_df["y_true"], pred_df["y_pred_proba"])

    # 1) Demographic fairness
    grp_rows = []
    attr_rows = []
    for attr in ATTRS:
        auc_map = {}
        for group, sub in pred_df.groupby(attr):
            n = len(sub)
            if n >= 30 and len(sub["y_true"].unique()) >= 2:
                auc_g = roc_auc_score(sub["y_true"], sub["y_pred_proba"])
                auc_map[group] = auc_g
                grp_rows.append(
                    {"attribute": attr, "group": group, "n": n, "auc": float(auc_g)}
                )
            else:
                grp_rows.append(
                    {"attribute": attr, "group": group, "n": n, "auc": np.nan}
                )
        vals = [v for v in auc_map.values() if pd.notna(v)]
        gap = (max(vals) - min(vals)) if len(vals) >= 2 else np.nan
        sev = (
            "RED"
            if pd.notna(gap) and gap > 0.20
            else "YELLOW"
            if pd.notna(gap) and gap > 0.10
            else "GREEN"
            if pd.notna(gap)
            else "INSUFFICIENT_DATA"
        )
        attr_rows.append(
            {
                "attribute": attr,
                "overall_auc": float(overall_auc),
                "max_auc_gap": float(gap) if pd.notna(gap) else np.nan,
                "severity": sev,
            }
        )

    fairness_by_group = pd.DataFrame(grp_rows).sort_values(["attribute", "group"])
    fairness_by_attribute = pd.DataFrame(attr_rows).sort_values(
        "max_auc_gap", ascending=False
    )

    # 2) Representation
    rep_rows = []
    for attr in ATTRS:
        for group, sub in pred_df.groupby(attr):
            n = len(sub)
            p_pos = sub["y_true"].mean()
            n_eff = n * 2 * min(p_pos, 1 - p_pos)
            status = (
                "reliable"
                if n_eff >= 30
                else "low_confidence"
                if n_eff >= 10
                else "suppressed"
            )
            rep_rows.append(
                {
                    "attribute": attr,
                    "group": group,
                    "n": int(n),
                    "positive_rate": float(p_pos),
                    "n_eff": float(n_eff),
                    "status": status,
                }
            )
    representation = pd.DataFrame(rep_rows).sort_values(
        ["attribute", "n"], ascending=[True, False]
    )

    # 3) Intersectionality 2-way
    inter_rows = []
    for a1, a2 in combinations(ATTRS, 2):
        for (g1, g2), sub in pred_df.groupby([a1, a2]):
            n = len(sub)
            if n < 20 or len(sub["y_true"].unique()) < 2:
                continue
            auc_sub = roc_auc_score(sub["y_true"], sub["y_pred_proba"])
            gap = overall_auc - auc_sub
            p_pos = sub["y_true"].mean()
            n_eff = n * 2 * min(p_pos, 1 - p_pos)
            score = gap * np.sqrt(max(n_eff, 1))
            inter_rows.append(
                {
                    "attr1": a1,
                    "group1": g1,
                    "attr2": a2,
                    "group2": g2,
                    "n": int(n),
                    "n_eff": float(n_eff),
                    "auc_subgroup": float(auc_sub),
                    "auc_overall": float(overall_auc),
                    "gap_vs_overall": float(gap),
                    "score": float(score),
                }
            )
    intersectionality_all = pd.DataFrame(inter_rows).sort_values(
        "score", ascending=False
    )
    intersectionality_top = intersectionality_all.head(25)

    # 4) Fairness drift (simulated windows)
    tmp = pred_df.sample(frac=1, random_state=42).reset_index(drop=True)
    tmp["window_id"] = pd.cut(tmp.index, bins=6, labels=False, include_lowest=True)
    drift_rows = []
    for attr in ATTRS:
        for w, subw in tmp.groupby("window_id"):
            aucs = []
            for _, subg in subw.groupby(attr):
                if len(subg) < 20 or len(subg["y_true"].unique()) < 2:
                    continue
                aucs.append(roc_auc_score(subg["y_true"], subg["y_pred_proba"]))
            gap_w = (max(aucs) - min(aucs)) if len(aucs) >= 2 else np.nan
            drift_rows.append({"attribute": attr, "window_id": int(w), "gap": gap_w})
    fairness_drift = pd.DataFrame(drift_rows)

    drift_sum_rows = []
    for attr, sub in fairness_drift.groupby("attribute"):
        s = sub.dropna(subset=["gap"]).sort_values("window_id")
        slope = np.polyfit(s["window_id"], s["gap"], 1)[0] if len(s) >= 2 else np.nan
        alert = (
            "RED"
            if pd.notna(slope) and slope > 0.02
            else "YELLOW"
            if pd.notna(slope) and slope > 0.005
            else "GREEN"
            if pd.notna(slope)
            else "INSUFFICIENT_DATA"
        )
        drift_sum_rows.append(
            {"attribute": attr, "gap_trend_slope": float(slope) if pd.notna(slope) else np.nan, "drift_alert": alert}
        )
    fairness_drift_summary = pd.DataFrame(drift_sum_rows)

    return {
        "fairness_by_attribute": fairness_by_attribute,
        "fairness_by_group": fairness_by_group,
        "representation": representation,
        "intersectionality_all": intersectionality_all,
        "intersectionality_top": intersectionality_top,
        "fairness_drift": fairness_drift,
        "fairness_drift_summary": fairness_drift_summary,
    }


def inject_bias(pred_df: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """Inject controlled synthetic bias into prediction probabilities.

    Scenarios intentionally perturb `y_pred_proba` for selected groups while
    keeping true labels unchanged. This isolates fairness metric sensitivity to
    model score behavior.
    """
    out = pred_df.copy()
    if scenario == "baseline":
        return out

    if scenario == "ethnicity_downweight":
        m = out["ethnicity"] == "African American"
        out.loc[m, "y_pred_proba"] = np.clip(out.loc[m, "y_pred_proba"] - 0.15, 0, 1)
        return out

    if scenario == "female_over65_downweight":
        m = (out["gender"] == "Female") & (out["age_group"] == "over_65")
        out.loc[m, "y_pred_proba"] = np.clip(out.loc[m, "y_pred_proba"] - 0.20, 0, 1)
        return out

    if scenario == "region_drift_like":
        # Simulate temporal degradation by applying a stronger penalty to the
        # final third of rows for a region to emulate worsening over windows.
        out = out.reset_index(drop=True)
        cut = int(len(out) * 0.67)
        m = (out.index >= cut) & (out["region"] == "South")
        out.loc[m, "y_pred_proba"] = np.clip(out.loc[m, "y_pred_proba"] - 0.25, 0, 1)
        return out

    raise ValueError(f"Unknown scenario: {scenario}")


def export_scenario(scenario: str, pred_df: pd.DataFrame, base_metrics: Dict[str, float]) -> pd.DataFrame:
    """Run one scenario end-to-end and export all outputs."""
    out_dir = OUTDIR / scenario
    out_dir.mkdir(parents=True, exist_ok=True)

    biased = inject_bias(pred_df, scenario)
    metrics = base_metrics.copy()
    metrics["scenario"] = scenario
    metrics["post_bias_auc"] = float(roc_auc_score(biased["y_true"], biased["y_pred_proba"]))
    metrics["post_bias_pr_auc"] = float(
        average_precision_score(biased["y_true"], biased["y_pred_proba"])
    )

    outputs = compute_fairness_outputs(biased)
    for name, df in outputs.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)
    biased.to_csv(out_dir / "predictions.csv", index=False)

    summary = pd.DataFrame([metrics])
    summary.to_csv(out_dir / "scenario_metrics.csv", index=False)
    return summary


def main() -> None:
    """Execute full synthetic bias experiment across all scenarios."""
    ensure_paths()
    canonical = pd.read_csv(CANONICAL_COPY)
    pred_df, base_metrics = build_prediction_frame(canonical)

    scenario_summaries = []
    for scenario in [
        "baseline",
        "ethnicity_downweight",
        "female_over65_downweight",
        "region_drift_like",
    ]:
        scenario_summaries.append(export_scenario(scenario, pred_df, base_metrics))

    combined = pd.concat(scenario_summaries, ignore_index=True)
    combined.to_csv(OUTDIR / "scenario_comparison.csv", index=False)

    print("Completed synthetic bias experiment.")
    print(f"Canonical copy: {CANONICAL_COPY}")
    print(f"Results root:   {OUTDIR}")
    print("\nScenario comparison:")
    print(combined.to_string(index=False))


if __name__ == "__main__":
    main()
