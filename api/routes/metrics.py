from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.schemas.metrics import MetricItem, MetricsLatestResponse
from api.services.supabase_read import SupabaseReadService


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/latest", response_model=MetricsLatestResponse)
def get_latest_metrics(
    model_name: str = Query(..., min_length=1),
    dimension: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=5000),
) -> MetricsLatestResponse:
    service = SupabaseReadService()
    latest = service.latest_run(model_name)
    if not latest:
        raise HTTPException(status_code=404, detail=f"No runs found for model_name={model_name}")

    rows = service.latest_run_metrics(run_id=str(latest["run_id"]), dimension=dimension, limit=limit)
    return MetricsLatestResponse(
        model_name=model_name,
        run_id=str(latest["run_id"]),
        dimension=dimension,
        count=len(rows),
        items=[MetricItem(**r) for r in rows],
    )
