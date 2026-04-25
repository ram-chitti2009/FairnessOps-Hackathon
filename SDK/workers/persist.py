from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from SDK.monitor.supabase_client import SupabaseConfig
from SDK.workers.config import WorkerConfig
from SDK.workers.data_access import insert_many


def _to_severity_from_rep_status(status: str) -> str:
    return "GREEN" if status == "reliable" else "YELLOW" if status == "low_confidence" else "RED"


def _to_severity_from_intersection_score(score: float) -> str:
    return "RED" if score > 0.50 else "YELLOW" if score > 0.20 else "GREEN"


def build_metric_and_alert_rows(
    run_id: str,
    outputs: Dict[str, pd.DataFrame],
    cfg: WorkerConfig,
) -> Dict[str, List[Dict[str, Any]]]:
    metric_rows: List[Dict[str, Any]] = []
    alert_rows: List[Dict[str, Any]] = []

    demographic_df = outputs["demographic"]
    for _, r in demographic_df.iterrows():
        gap = None if pd.isna(r["max_auc_gap"]) else float(r["max_auc_gap"])
        overall = None if pd.isna(r["overall_auc"]) else float(r["overall_auc"])
        attr = str(r["attribute"])
        sev = str(r["severity"])
        metric_rows.extend(
            [
                {
                    "run_id": run_id,
                    "dimension": "Demographic Fairness",
                    "attribute": attr,
                    "subgroup": None,
                    "metric_name": "max_auc_gap",
                    "metric_value": gap,
                    "metadata": {"overall_auc": overall},
                },
                {
                    "run_id": run_id,
                    "dimension": "Demographic Fairness",
                    "attribute": attr,
                    "subgroup": None,
                    "metric_name": "overall_auc",
                    "metric_value": overall,
                    "metadata": {"source": "attribute_view"},
                },
            ]
        )
        alert_rows.append(
            {
                "run_id": run_id,
                "dimension": "Demographic Fairness",
                "attribute": attr,
                "subgroup": None,
                "severity": sev,
                "message": f"{attr} max_auc_gap={gap}",
                "signal_value": gap,
                "threshold_config": {"red": cfg.fairness_red_gap, "yellow": cfg.fairness_yellow_gap},
            }
        )

    representation_df = outputs["representation"]
    for _, r in representation_df.iterrows():
        attr = str(r["attribute"])
        group = str(r["group"])
        n_eff = None if pd.isna(r["n_eff"]) else float(r["n_eff"])
        status = str(r["status"])
        metric_rows.extend(
            [
                {
                    "run_id": run_id,
                    "dimension": "Representation",
                    "attribute": attr,
                    "subgroup": group,
                    "metric_name": "n",
                    "metric_value": float(r["n"]),
                    "metadata": {},
                },
                {
                    "run_id": run_id,
                    "dimension": "Representation",
                    "attribute": attr,
                    "subgroup": group,
                    "metric_name": "positive_rate",
                    "metric_value": float(r["positive_rate"]),
                    "metadata": {},
                },
                {
                    "run_id": run_id,
                    "dimension": "Representation",
                    "attribute": attr,
                    "subgroup": group,
                    "metric_name": "n_eff",
                    "metric_value": n_eff,
                    "metadata": {"status": status},
                },
            ]
        )
        alert_rows.append(
            {
                "run_id": run_id,
                "dimension": "Representation",
                "attribute": attr,
                "subgroup": group,
                "severity": _to_severity_from_rep_status(status),
                "message": f"{attr}:{group} n_eff={n_eff} status={status}",
                "signal_value": n_eff,
                "threshold_config": {
                    "reliable": cfg.rep_reliable_neff,
                    "low_confidence": cfg.rep_low_conf_neff,
                },
            }
        )

    inter_all_df = outputs["intersectionality_all"]
    inter_top_df = outputs["intersectionality_top"]
    for _, r in inter_all_df.iterrows():
        subgroup = f"{r['attr1']}={r['group1']}|{r['attr2']}={r['group2']}"
        metric_rows.extend(
            [
                {
                    "run_id": run_id,
                    "dimension": "Intersectionality (2-way)",
                    "attribute": f"{r['attr1']}|{r['attr2']}",
                    "subgroup": subgroup,
                    "metric_name": "auc_subgroup",
                    "metric_value": float(r["auc_subgroup"]),
                    "metadata": {"n": int(r["n"]), "n_eff": float(r["n_eff"])},
                },
                {
                    "run_id": run_id,
                    "dimension": "Intersectionality (2-way)",
                    "attribute": f"{r['attr1']}|{r['attr2']}",
                    "subgroup": subgroup,
                    "metric_name": "gap_vs_overall",
                    "metric_value": float(r["gap_vs_overall"]),
                    "metadata": {"auc_overall": float(r["auc_overall"])},
                },
                {
                    "run_id": run_id,
                    "dimension": "Intersectionality (2-way)",
                    "attribute": f"{r['attr1']}|{r['attr2']}",
                    "subgroup": subgroup,
                    "metric_name": "score",
                    "metric_value": float(r["score"]),
                    "metadata": {"rank_context": "all"},
                },
            ]
        )
    for _, r in inter_top_df.iterrows():
        subgroup = f"{r['attr1']}={r['group1']}|{r['attr2']}={r['group2']}"
        score = float(r["score"])
        alert_rows.append(
            {
                "run_id": run_id,
                "dimension": "Intersectionality (2-way)",
                "attribute": f"{r['attr1']}|{r['attr2']}",
                "subgroup": subgroup,
                "severity": _to_severity_from_intersection_score(score),
                "message": f"intersection score={score:.4f}",
                "signal_value": score,
                "threshold_config": {"red": 0.50, "yellow": 0.20},
            }
        )

    drift_df = outputs["fairness_drift"]
    drift_summary_df = outputs["fairness_drift_summary"]
    for _, r in drift_df.iterrows():
        metric_rows.append(
            {
                "run_id": run_id,
                "dimension": "Fairness Drift",
                "attribute": str(r["attribute"]),
                "subgroup": f"window_{int(r['window_id'])}",
                "metric_name": "window_gap",
                "metric_value": None if pd.isna(r["gap"]) else float(r["gap"]),
                "metadata": {"window_id": int(r["window_id"])},
            }
        )
    for _, r in drift_summary_df.iterrows():
        slope = None if pd.isna(r["gap_trend_slope"]) else float(r["gap_trend_slope"])
        sev = str(r["drift_alert"])
        attr = str(r["attribute"])
        metric_rows.append(
            {
                "run_id": run_id,
                "dimension": "Fairness Drift",
                "attribute": attr,
                "subgroup": None,
                "metric_name": "gap_trend_slope",
                "metric_value": slope,
                "metadata": {},
            }
        )
        alert_rows.append(
            {
                "run_id": run_id,
                "dimension": "Fairness Drift",
                "attribute": attr,
                "subgroup": None,
                "severity": sev,
                "message": f"{attr} drift slope={slope}",
                "signal_value": slope,
                "threshold_config": {"red": cfg.drift_red_slope, "yellow": cfg.drift_yellow_slope},
            }
        )

    return {"metrics": metric_rows, "alerts": alert_rows}


def persist_all_dimensions(
    client: Any,
    s_cfg: SupabaseConfig,
    run_id: str,
    outputs: Dict[str, pd.DataFrame],
    cfg: WorkerConfig,
) -> None:
    rows = build_metric_and_alert_rows(run_id, outputs, cfg)
    insert_many(client, s_cfg, "fairness_metrics", rows["metrics"])
    insert_many(client, s_cfg, "metric_alerts", rows["alerts"])
