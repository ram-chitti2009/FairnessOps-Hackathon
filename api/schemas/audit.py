from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AuditLatestResponse(BaseModel):
    run_id: str
    created_at: str
    model_name: str
    model_version: Optional[str] = None
    window_size: Optional[int] = None
    status: str
    metric_count: int
    alert_count: int
    dimensions: List[str]
    metadata: Optional[Dict[str, Any]] = None
