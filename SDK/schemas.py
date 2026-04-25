from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd


@dataclass
class RunMetadata:
    run_id: str
    run_timestamp_utc: str
    audit_schema_version: str
    pipeline_version: str
    n_rows: int
    protected_attributes: List[str]
    thresholds: Dict[str, float]


@dataclass
class AuditResult:
    run_id: str
    output_dir: Path
    overall_status: str
    top_alerts: List[str]
    metadata: RunMetadata
    outputs: Dict[str, pd.DataFrame]
