from __future__ import annotations

from itertools import combinations
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .config import AuditConfig
from .exporter import build_run_metadata, write_outputs
from .schemas import AuditResult
from .validator import validate_input


def _fairness_severity(gap: float, config: AuditConfig) -> str:
    if pd.isna(gap):
        return "INSUFFICIENT_DATA"
    if gap > config.fairness_red_gap:
        return "RED"
    if gap > config.fairness_yellow_gap:
        return "YELLOW"
    return "GREEN"


def _representation_status(n_eff: float, config: AuditConfig) -> str:
    if n_eff >= config.rep_reliable_neff:
        return "reliable"
    if n_eff >= config.rep_low_conf_neff:
        return "low_confidence"
    return "suppressed"


def _drift_alert(slope: float, config: AuditConfig) -> str:
    if pd.isna(slope):
        return "INSUFFICIENT_DATA"
    if slope > config.drift_red_slope:
        return "RED"
    if slope > config.drift_yellow_slope:
        return "YELLOW"
    return "GREEN"


def _compute_outputs(df: pd.DataFrame, config: AuditConfig) -> Dict[str, pd.DataFrame]:
    attrs = config.protected_attributes
    y_col = config.label_col
    s_col = config.score_col

    overall_auc = roc_auc_score(df[y_col], df[s_col])

    # 1) Demographic fairness
    grp_rows: List[Dict] = []
    attr_rows: List[Dict] = []
    for attr in attrs:
        auc_map: Dict[str, float] = {}
        for group, sub in df.groupby(attr):
            n = len(sub)
            if n >= config.min_group_n_auc and len(sub[y_col].unique()) >= 2:
                auc_g = roc_auc_score(sub[y_col], sub[s_col])
                auc_map[group] = float(auc_g)
                grp_rows.append(
                    {"attribute": attr, "group": group, "n": int(n), "auc": float(auc_g)}
                )
            else:
                grp_rows.append({"attribute": attr, "group": group, "n": int(n), "auc": np.nan})

        vals = [v for v in auc_map.values() if pd.notna(v)]
        gap = (max(vals) - min(vals)) if len(vals) >= 2 else np.nan
        attr_rows.append(
            {
                "attribute": attr,
                "overall_auc": float(overall_auc),
                "max_auc_gap": float(gap) if pd.notna(gap) else np.nan,
                "severity": _fairness_severity(gap, config),
            }
        )

    fairness_by_group = pd.DataFrame(grp_rows).sort_values(["attribute", "group"])
    fairness_by_attribute = pd.DataFrame(attr_rows).sort_values("max_auc_gap", ascending=False)

    # 2) Representation
    rep_rows: List[Dict] = []
    for attr in attrs:
        for group, sub in df.groupby(attr):
            n = len(sub)
            p_pos = sub[y_col].mean()
            n_eff = n * 2 * min(p_pos, 1 - p_pos)
            rep_rows.append(
                {
                    "attribute": attr,
                    "group": group,
                    "n": int(n),
                    "positive_rate": float(p_pos),
                    "n_eff": float(n_eff),
                    "status": _representation_status(n_eff, config),
                }
            )
    representation = pd.DataFrame(rep_rows).sort_values(["attribute", "n"], ascending=[True, False])

    # 3) Intersectionality (2-way)
    inter_rows: List[Dict] = []
    for a1, a2 in combinations(attrs, 2):
        for (g1, g2), sub in df.groupby([a1, a2]):
            n = len(sub)
            if n < config.inter_min_group_n or len(sub[y_col].unique()) < 2:
                continue
            auc_sub = roc_auc_score(sub[y_col], sub[s_col])
            gap = overall_auc - auc_sub
            p_pos = sub[y_col].mean()
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
    intersectionality_all = pd.DataFrame(inter_rows).sort_values("score", ascending=False)
    intersectionality_top = intersectionality_all.head(config.inter_top_k).copy()

    # 4) Fairness drift (simulated windows)
    tmp = df.sample(frac=1, random_state=config.random_state).reset_index(drop=True)
    tmp["window_id"] = pd.cut(
        tmp.index, bins=config.drift_windows, labels=False, include_lowest=True
    )
    drift_rows: List[Dict] = []
    for attr in attrs:
        for w, subw in tmp.groupby("window_id"):
            aucs = []
            for _, subg in subw.groupby(attr):
                if len(subg) < config.inter_min_group_n or len(subg[y_col].unique()) < 2:
                    continue
                aucs.append(roc_auc_score(subg[y_col], subg[s_col]))
            gap_w = (max(aucs) - min(aucs)) if len(aucs) >= 2 else np.nan
            drift_rows.append({"attribute": attr, "window_id": int(w), "gap": gap_w})
    fairness_drift = pd.DataFrame(drift_rows)

    drift_sum_rows: List[Dict] = []
    for attr, sub in fairness_drift.groupby("attribute"):
        s = sub.dropna(subset=["gap"]).sort_values("window_id")
        slope = np.polyfit(s["window_id"], s["gap"], 1)[0] if len(s) >= 2 else np.nan
        drift_sum_rows.append(
            {
                "attribute": attr,
                "gap_trend_slope": float(slope) if pd.notna(slope) else np.nan,
                "drift_alert": _drift_alert(slope, config),
            }
        )
    fairness_drift_summary = pd.DataFrame(drift_sum_rows)

    # Dimension summary for at-a-glance dashboard/API cards.
    dim_rows = [
        {
            "dimension": "Demographic Fairness",
            "key_output_file": "fairness_by_attribute.csv",
            "headline_signal": f"Max attribute gap: {fairness_by_attribute['max_auc_gap'].max():.3f}",
        },
        {
            "dimension": "Representation",
            "key_output_file": "representation.csv",
            "headline_signal": f"Suppressed groups: {(representation['status'] == 'suppressed').sum()}",
        },
        {
            "dimension": "Intersectionality (2-way)",
            "key_output_file": "intersectionality_top.csv",
            "headline_signal": f"Top intersectional rows: {len(intersectionality_top)}",
        },
        {
            "dimension": "Fairness Drift",
            "key_output_file": "fairness_drift_summary.csv",
            "headline_signal": (
                "Drift alerts: "
                + ", ".join(
                    sorted(
                        fairness_drift_summary["drift_alert"].dropna().astype(str).unique().tolist()
                    )
                )
            ),
        },
    ]
    dimension_summary = pd.DataFrame(dim_rows)

    return {
        "fairness_by_attribute": fairness_by_attribute,
        "fairness_by_group": fairness_by_group,
        "representation": representation,
        "intersectionality_all": intersectionality_all,
        "intersectionality_top": intersectionality_top,
        "fairness_drift": fairness_drift,
        "fairness_drift_summary": fairness_drift_summary,
        "dimension_summary": dimension_summary,
    }


def _top_alerts(outputs: Dict[str, pd.DataFrame]) -> List[str]:
    alerts: List[str] = []
    attr_df = outputs["fairness_by_attribute"]
    red = attr_df[attr_df["severity"] == "RED"]
    for _, r in red.head(3).iterrows():
        alerts.append(f"{r['attribute']} max_auc_gap={r['max_auc_gap']:.3f} (RED)")

    drift_df = outputs["fairness_drift_summary"]
    drift_red = drift_df[drift_df["drift_alert"] == "RED"]
    for _, r in drift_red.head(2).iterrows():
        alerts.append(f"{r['attribute']} drift slope={r['gap_trend_slope']:.4f} (RED)")
    return alerts


def run_audit(df: pd.DataFrame, config: AuditConfig | None = None) -> AuditResult:
    """Run the frozen 4-dimension fairness audit and export standard artifacts."""
    cfg = config or AuditConfig()
    validate_input(df, cfg)

    work = df.copy()
    for c in cfg.protected_attributes:
        work[c] = work[c].astype("object").fillna("Unknown")
    work[cfg.label_col] = work[cfg.label_col].astype(int)
    work[cfg.score_col] = pd.to_numeric(work[cfg.score_col], errors="coerce")

    outputs = _compute_outputs(work, cfg)
    metadata = build_run_metadata(n_rows=len(work), config=cfg)
    output_dir = write_outputs(outputs=outputs, metadata=metadata, config=cfg)

    top_alerts = _top_alerts(outputs)
    overall_status = "RED" if top_alerts else "GREEN"
    return AuditResult(
        run_id=metadata.run_id,
        output_dir=output_dir,
        overall_status=overall_status,
        top_alerts=top_alerts,
        metadata=metadata,
        outputs=outputs,
    )
