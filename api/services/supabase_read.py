from __future__ import annotations

from typing import Any, Dict, List, Optional

from supabase import create_client  # type: ignore

from SDK.monitor.supabase_client import SupabaseConfig


class SupabaseReadService:
    def __init__(self) -> None:
        self.s_cfg = SupabaseConfig.from_env()
        self.client = create_client(self.s_cfg.url, self.s_cfg.key)

    def _table(self, name: str):
        return self.client.schema(self.s_cfg.schema).table(name)

    def latest_run(self, model_name: str) -> Optional[Dict[str, Any]]:
        res = (
            self._table("audit_runs")
            .select("run_id, created_at, model_name, model_version, window_size, status")
            .eq("model_name", model_name)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = list(res.data or [])
        return rows[0] if rows else None

    def latest_run_alerts(self, run_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        res = (
            self._table("metric_alerts")
            .select(
                "alert_id, created_at, run_id, dimension, attribute, subgroup, severity, message, signal_value, threshold_config"
            )
            .eq("run_id", run_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(res.data or [])

    def latest_run_metrics(
        self, run_id: str, dimension: Optional[str] = None, limit: int = 200
    ) -> List[Dict[str, Any]]:
        query = self._table("fairness_metrics").select(
            "metric_id, created_at, run_id, dimension, attribute, subgroup, metric_name, metric_value, metadata"
        ).eq("run_id", run_id)
        if dimension:
            query = query.eq("dimension", dimension)
        res = query.order("created_at", desc=True).limit(limit).execute()
        return list(res.data or [])

    def latest_alert_id(self, model_name: str) -> Optional[int]:
        run = self.latest_run(model_name)
        if not run:
            return None
        res = (
            self._table("metric_alerts")
            .select("alert_id")
            .eq("run_id", run["run_id"])
            .order("alert_id", desc=True)
            .limit(1)
            .execute()
        )
        rows = list(res.data or [])
        return int(rows[0]["alert_id"]) if rows else None

    def alerts_after(self, model_name: str, after_alert_id: int) -> List[Dict[str, Any]]:
        run = self.latest_run(model_name)
        if not run:
            return []
        res = (
            self._table("metric_alerts")
            .select(
                "alert_id, created_at, run_id, dimension, attribute, subgroup, severity, message, signal_value, threshold_config"
            )
            .eq("run_id", run["run_id"])
            .gt("alert_id", after_alert_id)
            .order("alert_id", desc=False)
            .execute()
        )
        return list(res.data or [])
