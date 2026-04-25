from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.schemas.alerts import AlertItem, AlertsLatestResponse
from api.services.supabase_read import SupabaseReadService


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/latest", response_model=AlertsLatestResponse)
def get_latest_alerts(
    model_name: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=1000),
) -> AlertsLatestResponse:
    service = SupabaseReadService()
    latest = service.latest_run(model_name)
    if not latest:
        raise HTTPException(status_code=404, detail=f"No runs found for model_name={model_name}")

    rows = service.latest_run_alerts(run_id=str(latest["run_id"]), limit=limit)
    return AlertsLatestResponse(
        model_name=model_name,
        run_id=str(latest["run_id"]),
        count=len(rows),
        items=[AlertItem(**r) for r in rows],
    )
