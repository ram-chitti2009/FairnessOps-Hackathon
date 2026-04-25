from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd

from SDK.monitor.supabase_client import SupabaseConfig
from SDK.workers.config import WorkerConfig


def _extract_attrs(attrs_value: Any) -> Dict[str, Any]:
    if isinstance(attrs_value, dict):
        return attrs_value
    return {}


def fetch_rolling_events(client: Any, s_cfg: SupabaseConfig, cfg: WorkerConfig) -> pd.DataFrame:
    result = (
        client.schema(s_cfg.schema)
        .table(s_cfg.prediction_table)
        .select("event_id, created_at, model_name, y_pred_proba, y_true, attrs")
        .eq("model_name", cfg.model_name)
        .order("event_id", desc=True)
        .limit(cfg.window_n)
        .execute()
    )
    rows = list(result.data or [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("event_id").reset_index(drop=True)
    attrs_expanded = df["attrs"].apply(_extract_attrs).apply(pd.Series)
    return pd.concat([df.drop(columns=["attrs"]), attrs_expanded], axis=1)


def insert_audit_run(client: Any, s_cfg: SupabaseConfig, cfg: WorkerConfig, df: pd.DataFrame) -> str:
    now = datetime.now(timezone.utc).isoformat()
    start = str(df["created_at"].iloc[0]) if not df.empty else now
    end = str(df["created_at"].iloc[-1]) if not df.empty else now
    payload = {
        "created_at": now,
        "model_name": cfg.model_name,
        "window_start": start,
        "window_end": end,
        "window_size": int(len(df)),
        "audit_schema_version": cfg.audit_schema_version,
        "pipeline_version": cfg.pipeline_version,
        "status": "completed",
    }
    res = client.schema(s_cfg.schema).table("audit_runs").insert(payload).execute()
    data = list(res.data or [])
    if not data or "run_id" not in data[0]:
        raise RuntimeError("Failed to create audit_runs row with run_id.")
    return str(data[0]["run_id"])


def insert_many(client: Any, s_cfg: SupabaseConfig, table: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    client.schema(s_cfg.schema).table(table).insert(rows).execute()
