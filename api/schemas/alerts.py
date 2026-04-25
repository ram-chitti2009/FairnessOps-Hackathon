from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AlertItem(BaseModel):
    alert_id: int
    created_at: str
    run_id: str
    dimension: str
    attribute: Optional[str] = None
    subgroup: Optional[str] = None
    severity: str
    message: Optional[str] = None
    signal_value: Optional[float] = None
    threshold_config: Dict[str, Any] = {}


class AlertsLatestResponse(BaseModel):
    model_name: str
    run_id: str
    count: int
    items: List[AlertItem]
