from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MetricItem(BaseModel):
    metric_id: int
    created_at: str
    run_id: str
    dimension: str
    attribute: Optional[str] = None
    subgroup: Optional[str] = None
    metric_name: str
    metric_value: Optional[float] = None
    metadata: Dict[str, Any] = {}


class MetricsLatestResponse(BaseModel):
    model_name: str
    run_id: str
    dimension: Optional[str] = None
    count: int
    items: List[MetricItem]
