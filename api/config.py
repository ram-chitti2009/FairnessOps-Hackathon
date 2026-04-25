from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class ApiConfig:
    title: str = "FairnessOps API"
    version: str = "0.2.0"
    stream_poll_seconds: float = 3.0
    default_model_name: str = "default_model"
    default_alert_limit: int = 50
    default_metric_limit: int = 200
    default_protected_attrs: List[str] = field(
        default_factory=lambda: ["ethnicity", "gender", "age_group", "region"]
    )

    @classmethod
    def from_env(cls) -> "ApiConfig":
        poll = float(os.getenv("API_STREAM_POLL_SECONDS", "3.0"))
        model = os.getenv("API_DEFAULT_MODEL_NAME", "default_model")
        return cls(stream_poll_seconds=poll, default_model_name=model)
