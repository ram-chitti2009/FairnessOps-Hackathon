from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from SDK import AuditConfig, run_audit


app = FastAPI(title="FairnessOps API", version="0.1.0")

DEFAULT_OUTPUT_ROOT = "runs/sdk_api_outputs"


class RunAuditRequest(BaseModel):
    input_csv: str = Field(..., description="Path to predictions CSV.")
    output_root: str = Field(DEFAULT_OUTPUT_ROOT, description="Output root for run artifacts.")
    label_col: str = "y_true"
    score_col: str = "y_pred_proba"
    id_col: str = "patientunitstayid"
    protected_attrs: List[str] = ["ethnicity", "gender", "age_group", "region"]


class RunAuditResponse(BaseModel):
    run_id: str
    overall_status: str
    output_dir: str
    top_alerts: List[str]


class RunLookupResponse(BaseModel):
    run_id: str
    metadata: dict
    available_files: List[str]
    output_dir: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/audit/run", response_model=RunAuditResponse)
def audit_run(req: RunAuditRequest) -> RunAuditResponse:
    input_csv = Path(req.input_csv)
    if not input_csv.exists():
        raise HTTPException(status_code=404, detail=f"Input CSV not found: {input_csv}")

    df = pd.read_csv(input_csv)
    cfg = AuditConfig(
        protected_attributes=req.protected_attrs,
        label_col=req.label_col,
        score_col=req.score_col,
        id_col=req.id_col,
        output_root=req.output_root,
    )
    result = run_audit(df, cfg)
    return RunAuditResponse(
        run_id=result.run_id,
        overall_status=result.overall_status,
        output_dir=str(result.output_dir),
        top_alerts=result.top_alerts,
    )


def _find_run_dir(run_id: str, search_roots: Optional[List[Path]] = None) -> Optional[Path]:
    roots = search_roots or [
        Path("runs/sdk_api_outputs"),
        Path("runs/sdk_outputs"),
        Path("runs/sdk_test_outputs/smoke"),
        Path("runs/sdk_test_outputs/scenarios"),
    ]
    for root in roots:
        cand = root / run_id
        if cand.exists() and cand.is_dir():
            return cand
    return None


@app.get("/audit/{run_id}", response_model=RunLookupResponse)
def audit_lookup(run_id: str) -> RunLookupResponse:
    run_dir = _find_run_dir(run_id)
    if run_dir is None:
        raise HTTPException(status_code=404, detail=f"Run ID not found: {run_id}")

    metadata_path = run_dir / "run_metadata.json"
    metadata = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    files = sorted([p.name for p in run_dir.iterdir() if p.is_file()])
    return RunLookupResponse(
        run_id=run_id,
        metadata=metadata,
        available_files=files,
        output_dir=str(run_dir),
    )
