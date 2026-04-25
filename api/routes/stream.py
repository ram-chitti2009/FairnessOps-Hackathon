from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from api.config import ApiConfig
from api.services.supabase_read import SupabaseReadService


router = APIRouter(prefix="/stream", tags=["stream"])


async def _alerts_stream(model_name: str, poll_seconds: float) -> AsyncIterator[str]:
    service = SupabaseReadService()
    cursor = service.latest_alert_id(model_name) or 0
    yield f"event: ready\ndata: {json.dumps({'model_name': model_name, 'cursor': cursor})}\n\n"
    while True:
        rows = service.alerts_after(model_name=model_name, after_alert_id=cursor)
        for row in rows:
            cursor = max(cursor, int(row["alert_id"]))
            payload = {"type": "metric_alert_insert", "data": row}
            yield f"event: alert\ndata: {json.dumps(payload)}\n\n"
        await asyncio.sleep(poll_seconds)


@router.get("/alerts")
async def stream_alerts(model_name: str = Query(..., min_length=1)) -> StreamingResponse:
    cfg = ApiConfig.from_env()
    return StreamingResponse(
        _alerts_stream(model_name=model_name, poll_seconds=cfg.stream_poll_seconds),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
