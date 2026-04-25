from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from uuid import uuid4

import pandas as pd

from .config import AuditConfig
from .schemas import RunMetadata


def build_run_metadata(
    n_rows: int,
    config: AuditConfig,
    run_id: str | None = None,
) -> RunMetadata:
    now = datetime.now(timezone.utc).isoformat()
    rid = run_id or f"{config.run_prefix}_{uuid4().hex[:10]}"
    return RunMetadata(
        run_id=rid,
        run_timestamp_utc=now,
        audit_schema_version=config.audit_schema_version,
        pipeline_version=config.pipeline_version,
        n_rows=n_rows,
        protected_attributes=config.protected_attributes,
        thresholds=config.threshold_snapshot(),
    )


def write_outputs(
    outputs: Dict[str, pd.DataFrame],
    metadata: RunMetadata,
    config: AuditConfig,
) -> Path:
    out_dir = Path(config.output_root) / metadata.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, df in outputs.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)

    with (out_dir / "run_metadata.json").open("w", encoding="utf-8") as f:
        json.dump(asdict(metadata), f, indent=2)

    return out_dir
