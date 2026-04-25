from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.config import ApiConfig
from api.schemas.audit import AuditLatestResponse
from api.services.supabase_read import SupabaseReadService


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/latest", response_model=AuditLatestResponse)
def get_latest_audit(model_name: str = Query(..., min_length=1)) -> AuditLatestResponse:
    service = SupabaseReadService()
    latest = service.latest_run(model_name)
    if not latest:
        raise HTTPException(status_code=404, detail=f"No runs found for model_name={model_name}")

    metrics = service.latest_run_metrics(run_id=latest["run_id"], limit=1000)
    alerts = service.latest_run_alerts(run_id=latest["run_id"], limit=1000)
    dimensions = sorted(set([str(m.get("dimension")) for m in metrics if m.get("dimension")]))

    return AuditLatestResponse(
        run_id=str(latest["run_id"]),
        created_at=str(latest["created_at"]),
        model_name=str(latest["model_name"]),
        model_version=latest.get("model_version"),
        window_size=latest.get("window_size"),
        status=str(latest.get("status", "unknown")),
        metric_count=len(metrics),
        alert_count=len(alerts),
        dimensions=dimensions,
    )
