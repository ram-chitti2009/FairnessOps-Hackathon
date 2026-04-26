# FairnessOps

Clinical AI fairness monitoring for realtime operations. Wrap predictions with `@monitor`, compute fairness checks in scheduled runs, and review findings in a CMIO-friendly dashboard.

## Product Snapshot

- **Ingestion:** Python SDK logs prediction events to Supabase.
- **Computation:** Worker computes **9 fairness dimensions** per run.
- **Persistence:** Results stored in `audit_runs`, `fairness_metrics`, and `metric_alerts`.
- **Experience:** Next.js dashboard shows live updates via Supabase Realtime.
- **Narrative:** Optional LLM summary turns findings into plain clinical language.

## 9 Dimensions Implemented

- `Demographic Fairness`
- `Representation`
- `Intersectionality (2-way)`
- `Fairness Drift`
- `Threshold Parity`
- `False Negative Gap`
- `Calibration Fairness`
- `Feature Drift`
- `Algorithmic Drift (PELT)`

## Quickstart

### 1) Install

```bash
pip install -e .
```

### 2) Configure env (`.env`)

```env
SUPABASE_URL=...
SUPABASE_KEY=...
SUPABASE_SCHEMA=fairnessops
OPENAI_API_KEY=...              # optional (AI summary)
DATASET_MODE=synthetic          # cancer | eicu | synthetic
```

### 3) Start backend API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 4) Start dashboard

```bash
cd dashboard-next
npm install
npm run dev
```

### 5) Start scheduler

```bash
python FairnessOps_Testing/scheduler.py
```

## Scheduler Dataset Modes

Configure in `.env`:

- `DATASET_MODE=cancer` uses Kaggle cancer workflow.
- `DATASET_MODE=eicu` uses your `EICU_DATA_PATH` CSV.
- `DATASET_MODE=synthetic` uses built-in synthetic runtime for demo-safe live monitoring.

Synthetic-specific knobs:

```env
SYNTH_MODEL_NAME=synthetic_monitor_v1
SYNTH_ROWS=5000
SYNTH_SEED=42
```

## SDK Usage

```python
import pandas as pd
from SDK.monitor.decorator import monitor

@monitor(model_name="my_model_v1", protected_attrs=["gender", "race"])
def predict(X: pd.DataFrame) -> list[float]:
    return model.predict_proba(X)[:, 1].tolist()

# Logging happens automatically on each call.
scores = predict(X_batch, y_true=y_batch, patient_ids=ids)
```

## Worker Run (Manual)

```python
from SDK.workers.config import WorkerConfig
from SDK.workers.run_worker import run_once

cfg = WorkerConfig(
    model_name="my_model_v1",
    protected_attrs=["gender", "race"],
    clinical_context={
        "useCase": "ICU Deterioration Risk",
        "outcome": "flagged as high deterioration risk",
        "population": "Adult ICU Patients",
        "department": "Critical Care",
        "patientsPerMonth": 1200,
        "complianceNote": "CMS AI Transparency & Bias Rule (2025)",
    },
)
run_once(cfg)
```

## Dashboard Behavior

- Model selector auto-discovers all models with audit runs.
- Realtime channels are model-scoped to prevent cross-model mixing.
- Alert triage and signal text are clinical-language first (not math-heavy).
- Health Index is heuristic and tuned to avoid over-penalizing low-volume representation issues.

## Core API Endpoints

- `GET /health`
- `GET /audit/models`
- `GET /audit/latest?model_name=...`
- `GET /alerts/latest?model_name=...`
- `GET /metrics/latest?model_name=...`
- `GET /stream/alerts?model_name=...` (SSE fallback)

## Repo Areas

- `SDK/` Python monitor + worker
- `FairnessOps_Testing/` scheduler runtimes and orchestration
- `api/` FastAPI read API
- `dashboard-next/` Next.js dashboard
- `SDK_testing/` synthetic ingest helpers
