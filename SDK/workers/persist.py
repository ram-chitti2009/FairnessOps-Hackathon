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


def _add_demographic(
    run_id: str, df: pd.DataFrame, cfg: WorkerConfig, metrics: List[Dict[str, Any]], alerts: List[Dict[str, Any]]
) -> None:
    for _, r in df.iterrows():
        gap = None if pd.isna(r["max_auc_gap"]) else float(r["max_auc_gap"])
        overall = None if pd.isna(r["overall_auc"]) else float(r["overall_auc"])
        attr = str(r["attribute"])
        sev = str(r["severity"])
        metrics.extend(
            [
                {"run_id": run_id, "dimension": "Demographic Fairness", "attribute": attr, "subgroup": None, "metric_name": "max_auc_gap", "metric_value": gap, "metadata": {"overall_auc": overall}},
                {"run_id": run_id, "dimension": "Demographic Fairness", "attribute": attr, "subgroup": None, "metric_name": "overall_auc", "metric_value": overall, "metadata": {"source": "attribute_view"}},
            ]
        )
        alerts.append(
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


def _add_representation(
    run_id: str, df: pd.DataFrame, cfg: WorkerConfig, metrics: List[Dict[str, Any]], alerts: List[Dict[str, Any]]
) -> None:
    for _, r in df.iterrows():
        attr = str(r["attribute"])
        group = str(r["group"])
        n_eff = None if pd.isna(r["n_eff"]) else float(r["n_eff"])
        status = str(r["status"])
        metrics.extend(
            [
                {"run_id": run_id, "dimension": "Representation", "attribute": attr, "subgroup": group, "metric_name": "n", "metric_value": float(r["n"]), "metadata": {}},
                {"run_id": run_id, "dimension": "Representation", "attribute": attr, "subgroup": group, "metric_name": "positive_rate", "metric_value": float(r["positive_rate"]), "metadata": {}},
                {"run_id": run_id, "dimension": "Representation", "attribute": attr, "subgroup": group, "metric_name": "n_eff", "metric_value": n_eff, "metadata": {"status": status}},
            ]
        )
        alerts.append(
            {
                "run_id": run_id,
                "dimension": "Representation",
                "attribute": attr,
                "subgroup": group,
                "severity": _to_severity_from_rep_status(status),
                "message": f"{attr}:{group} n_eff={n_eff} status={status}",
                "signal_value": n_eff,
                "threshold_config": {"reliable": cfg.rep_reliable_neff, "low_confidence": cfg.rep_low_conf_neff},
            }
        )


def _add_intersectionality(
    run_id: str, all_df: pd.DataFrame, top_df: pd.DataFrame, metrics: List[Dict[str, Any]], alerts: List[Dict[str, Any]]
) -> None:
    for _, r in all_df.iterrows():
        subgroup = f"{r['attr1']}={r['group1']}|{r['attr2']}={r['group2']}"
        metrics.extend(
            [
                {"run_id": run_id, "dimension": "Intersectionality (2-way)", "attribute": f"{r['attr1']}|{r['attr2']}", "subgroup": subgroup, "metric_name": "auc_subgroup", "metric_value": float(r["auc_subgroup"]), "metadata": {"n": int(r["n"]), "n_eff": float(r["n_eff"])}},
                {"run_id": run_id, "dimension": "Intersectionality (2-way)", "attribute": f"{r['attr1']}|{r['attr2']}", "subgroup": subgroup, "metric_name": "gap_vs_overall", "metric_value": float(r["gap_vs_overall"]), "metadata": {"auc_overall": float(r["auc_overall"])}},
                {"run_id": run_id, "dimension": "Intersectionality (2-way)", "attribute": f"{r['attr1']}|{r['attr2']}", "subgroup": subgroup, "metric_name": "score", "metric_value": float(r["score"]), "metadata": {"rank_context": "all"}},
            ]
        )
    for _, r in top_df.iterrows():
        subgroup = f"{r['attr1']}={r['group1']}|{r['attr2']}={r['group2']}"
        score = float(r["score"])
        alerts.append(
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


def _add_fairness_drift(
    run_id: str, drift_df: pd.DataFrame, summary_df: pd.DataFrame, cfg: WorkerConfig, metrics: List[Dict[str, Any]], alerts: List[Dict[str, Any]]
) -> None:
    for _, r in drift_df.iterrows():
        metrics.append(
            {"run_id": run_id, "dimension": "Fairness Drift", "attribute": str(r["attribute"]), "subgroup": f"window_{int(r['window_id'])}", "metric_name": "window_gap", "metric_value": None if pd.isna(r["gap"]) else float(r["gap"]), "metadata": {"window_id": int(r["window_id"])}}
        )
    for _, r in summary_df.iterrows():
        slope = None if pd.isna(r["gap_trend_slope"]) else float(r["gap_trend_slope"])
        attr = str(r["attribute"])
        sev = str(r["drift_alert"])
        metrics.append(
            {"run_id": run_id, "dimension": "Fairness Drift", "attribute": attr, "subgroup": None, "metric_name": "gap_trend_slope", "metric_value": slope, "metadata": {}}
        )
        alerts.append(
            {"run_id": run_id, "dimension": "Fairness Drift", "attribute": attr, "subgroup": None, "severity": sev, "message": f"{attr} drift slope={slope}", "signal_value": slope, "threshold_config": {"red": cfg.drift_red_slope, "yellow": cfg.drift_yellow_slope}}
        )


def _add_threshold_parity(
    run_id: str, df: pd.DataFrame, cfg: WorkerConfig, metrics: List[Dict[str, Any]], alerts: List[Dict[str, Any]]
) -> None:
    for _, r in df.iterrows():
        attr = str(r.get("attribute"))
        subgroup = r.get("subgroup")
        kind = str(r.get("row_kind", "group"))
        pos_rate = None if pd.isna(r.get("positive_rate_at_threshold")) else float(r.get("positive_rate_at_threshold"))
        parity_gap = None if pd.isna(r.get("parity_gap")) else float(r.get("parity_gap"))
        sev = str(r.get("severity", "INSUFFICIENT_DATA"))
        if kind == "group":
            metrics.append(
                {"run_id": run_id, "dimension": "Threshold Parity", "attribute": attr, "subgroup": None if subgroup is None else str(subgroup), "metric_name": "positive_rate_at_threshold", "metric_value": pos_rate, "metadata": {"threshold": cfg.operating_threshold}}
            )
        else:
            metrics.append(
                {"run_id": run_id, "dimension": "Threshold Parity", "attribute": attr, "subgroup": None, "metric_name": "parity_gap", "metric_value": parity_gap, "metadata": {"threshold": cfg.operating_threshold}}
            )
            alerts.append(
                {"run_id": run_id, "dimension": "Threshold Parity", "attribute": attr, "subgroup": None, "severity": sev, "message": f"{attr} threshold parity gap={parity_gap}", "signal_value": parity_gap, "threshold_config": {"red": cfg.threshold_parity_red_gap, "yellow": cfg.threshold_parity_yellow_gap, "threshold": cfg.operating_threshold}}
            )


def _add_fnr_gap(
    run_id: str, df: pd.DataFrame, cfg: WorkerConfig, metrics: List[Dict[str, Any]], alerts: List[Dict[str, Any]]
) -> None:
    for _, r in df.iterrows():
        attr = str(r.get("attribute"))
        subgroup = r.get("subgroup")
        kind = str(r.get("row_kind", "group"))
        fnr = None if pd.isna(r.get("fnr")) else float(r.get("fnr"))
        fnr_gap = None if pd.isna(r.get("fnr_gap")) else float(r.get("fnr_gap"))
        n_pos = int(r.get("n_pos", 0))
        sev = str(r.get("severity", "INSUFFICIENT_DATA"))
        if kind == "group":
            metrics.append(
                {"run_id": run_id, "dimension": "False Negative Gap", "attribute": attr, "subgroup": None if subgroup is None else str(subgroup), "metric_name": "fnr", "metric_value": fnr, "metadata": {"n_pos": n_pos, "threshold": cfg.operating_threshold}}
            )
        else:
            metrics.append(
                {"run_id": run_id, "dimension": "False Negative Gap", "attribute": attr, "subgroup": None, "metric_name": "fnr_gap", "metric_value": fnr_gap, "metadata": {"threshold": cfg.operating_threshold}}
            )
            alerts.append(
                {"run_id": run_id, "dimension": "False Negative Gap", "attribute": attr, "subgroup": None, "severity": sev, "message": f"{attr} fnr gap={fnr_gap}", "signal_value": fnr_gap, "threshold_config": {"red": cfg.fnr_red_gap, "yellow": cfg.fnr_yellow_gap, "threshold": cfg.operating_threshold}}
            )


def _add_calibration(
    run_id: str, df: pd.DataFrame, cfg: WorkerConfig, metrics: List[Dict[str, Any]], alerts: List[Dict[str, Any]]
) -> None:
    for _, r in df.iterrows():
        attr = str(r.get("attribute"))
        subgroup = r.get("subgroup")
        kind = str(r.get("row_kind", "group"))
        mean_pred = None if pd.isna(r.get("mean_pred")) else float(r.get("mean_pred"))
        obs_rate = None if pd.isna(r.get("observed_rate")) else float(r.get("observed_rate"))
        cal_err = None if pd.isna(r.get("calibration_error")) else float(r.get("calibration_error"))
        cal_gap = None if pd.isna(r.get("calibration_gap")) else float(r.get("calibration_gap"))
        sev = str(r.get("severity", "INSUFFICIENT_DATA"))
        if kind == "group":
            metrics.append(
                {"run_id": run_id, "dimension": "Calibration Fairness", "attribute": attr, "subgroup": None if subgroup is None else str(subgroup), "metric_name": "calibration_error", "metric_value": cal_err, "metadata": {"mean_pred": mean_pred, "observed_rate": obs_rate}}
            )
        else:
            metrics.append(
                {"run_id": run_id, "dimension": "Calibration Fairness", "attribute": attr, "subgroup": None, "metric_name": "calibration_gap", "metric_value": cal_gap, "metadata": {}}
            )
            alerts.append(
                {"run_id": run_id, "dimension": "Calibration Fairness", "attribute": attr, "subgroup": None, "severity": sev, "message": f"{attr} calibration gap={cal_gap}", "signal_value": cal_gap, "threshold_config": {"red": cfg.calibration_red_gap, "yellow": cfg.calibration_yellow_gap}}
            )


def _add_feature_drift(
    run_id: str, df: pd.DataFrame, metrics: List[Dict[str, Any]], alerts: List[Dict[str, Any]]
) -> None:
    for _, r in df.iterrows():
        attr = str(r.get("attribute"))
        ks_stat = None if pd.isna(r.get("ks_stat")) else float(r.get("ks_stat"))
        ks_p = None if pd.isna(r.get("ks_pvalue")) else float(r.get("ks_pvalue"))
        psi = None if pd.isna(r.get("psi")) else float(r.get("psi"))
        sev = str(r.get("severity", "INSUFFICIENT_DATA"))
        metrics.extend(
            [
                {"run_id": run_id, "dimension": "Feature Drift", "attribute": attr, "subgroup": None, "metric_name": "ks_stat", "metric_value": ks_stat, "metadata": {}},
                {"run_id": run_id, "dimension": "Feature Drift", "attribute": attr, "subgroup": None, "metric_name": "ks_pvalue", "metric_value": ks_p, "metadata": {}},
                {"run_id": run_id, "dimension": "Feature Drift", "attribute": attr, "subgroup": None, "metric_name": "psi", "metric_value": psi, "metadata": {}},
            ]
        )
        alerts.append(
            {"run_id": run_id, "dimension": "Feature Drift", "attribute": attr, "subgroup": None, "severity": sev, "message": f"{attr} feature drift ks={ks_stat} psi={psi}", "signal_value": ks_stat, "threshold_config": {"ks_red": 0.20, "ks_yellow": 0.10, "psi_red": 0.25, "psi_yellow": 0.10}}
        )


def _add_algorithmic_drift(
    run_id: str, windows_df: pd.DataFrame, summary_df: pd.DataFrame, cfg: WorkerConfig, metrics: List[Dict[str, Any]], alerts: List[Dict[str, Any]]
) -> None:
    for _, r in windows_df.iterrows():
        auc_w = None if pd.isna(r.get("overall_auc")) else float(r.get("overall_auc"))
        w_id = int(r.get("window_id", 0))
        is_cp = bool(r.get("is_changepoint", False))
        metrics.append(
            {"run_id": run_id, "dimension": "Algorithmic Drift (PELT)", "attribute": "model_overall", "subgroup": f"window_{w_id}", "metric_name": "overall_auc", "metric_value": auc_w, "metadata": {"window_id": w_id, "is_changepoint": is_cp}}
        )
    for _, r in summary_df.iterrows():
        baseline_auc = None if pd.isna(r.get("baseline_auc")) else float(r.get("baseline_auc"))
        current_auc = None if pd.isna(r.get("current_auc")) else float(r.get("current_auc"))
        auc_drop = None if pd.isna(r.get("auc_drop")) else float(r.get("auc_drop"))
        sev = str(r.get("severity", "INSUFFICIENT_DATA"))
        cps = str(r.get("changepoints", ""))
        metrics.extend(
            [
                {"run_id": run_id, "dimension": "Algorithmic Drift (PELT)", "attribute": "model_overall", "subgroup": None, "metric_name": "baseline_auc", "metric_value": baseline_auc, "metadata": {}},
                {"run_id": run_id, "dimension": "Algorithmic Drift (PELT)", "attribute": "model_overall", "subgroup": None, "metric_name": "current_auc", "metric_value": current_auc, "metadata": {}},
                {"run_id": run_id, "dimension": "Algorithmic Drift (PELT)", "attribute": "model_overall", "subgroup": None, "metric_name": "auc_drop", "metric_value": auc_drop, "metadata": {"changepoints": cps, "n_changepoints": int(r.get("n_changepoints", 0))}},
            ]
        )
        alerts.append(
            {"run_id": run_id, "dimension": "Algorithmic Drift (PELT)", "attribute": "model_overall", "subgroup": None, "severity": sev, "message": f"overall auc drop={auc_drop} changepoints={cps}", "signal_value": auc_drop, "threshold_config": {"red_drop": cfg.algo_drift_red_drop, "yellow_drop": cfg.algo_drift_yellow_drop, "pelt_pen": cfg.algo_pelt_pen}}
        )


def build_metric_and_alert_rows(
    run_id: str,
    outputs: Dict[str, pd.DataFrame],
    cfg: WorkerConfig,
) -> Dict[str, List[Dict[str, Any]]]:
    metrics: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []
    _add_demographic(run_id, outputs["demographic"], cfg, metrics, alerts)
    _add_representation(run_id, outputs["representation"], cfg, metrics, alerts)
    _add_intersectionality(run_id, outputs["intersectionality_all"], outputs["intersectionality_top"], metrics, alerts)
    _add_fairness_drift(run_id, outputs["fairness_drift"], outputs["fairness_drift_summary"], cfg, metrics, alerts)
    _add_threshold_parity(run_id, outputs.get("threshold_parity", pd.DataFrame()), cfg, metrics, alerts)
    _add_fnr_gap(run_id, outputs.get("fnr_gap", pd.DataFrame()), cfg, metrics, alerts)
    _add_calibration(run_id, outputs.get("calibration_gap", pd.DataFrame()), cfg, metrics, alerts)
    _add_feature_drift(run_id, outputs.get("feature_drift", pd.DataFrame()), metrics, alerts)
    _add_algorithmic_drift(run_id, outputs.get("algorithmic_drift_windows", pd.DataFrame()), outputs.get("algorithmic_drift_summary", pd.DataFrame()), cfg, metrics, alerts)
    return {"metrics": metrics, "alerts": alerts}


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
