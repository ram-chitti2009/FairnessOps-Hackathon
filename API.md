# FairnessOps API Reference

Base URL: `http://localhost:8000` (dev)

Interactive docs available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` once the server is running.

---

## Starting the server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

The server requires `SUPABASE_URL` and `SUPABASE_KEY` to be set in the environment (or a `.env` file at the project root).

---

## Authentication

None — the API is designed for internal / localhost use. The Supabase connection uses the key from the server's environment; clients never touch credentials directly.

---

## Endpoints

### `GET /health`

Liveness check.

**Response `200`**
```json
{ "status": "ok" }
```

---

### `GET /audit/models`

Returns every distinct model name that has at least one completed audit run in the database. Used by the dashboard's model selector to populate the dropdown.

**Query parameters** — none

**Response `200`** — `string[]`

```json
[
  "deterioration_v1",
  "readmission_v2",
  "sepsis_monitor_20260425"
]
```

Models are returned in alphabetical order.

---

### `GET /audit/latest`

Returns a summary of the most recent audit run for the given model, including aggregate counts and the clinical metadata written by the worker.

**Query parameters**

| param | type | required | description |
|---|---|---|---|
| `model_name` | `string` | yes | Exact model name (as used in `@monitor` or `WorkerConfig`) |

**Response `200`**

```json
{
  "run_id":       "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "created_at":   "2026-04-25T21:27:09.123Z",
  "model_name":   "readmission_v2",
  "model_version": null,
  "window_size":  4821,
  "status":       "completed",
  "metric_count": 142,
  "alert_count":  18,
  "dimensions": [
    "Algorithmic Drift (PELT)",
    "Calibration Fairness",
    "Demographic Fairness",
    "Fairness Drift",
    "Feature Drift",
    "False Negative Gap",
    "Intersectionality (2-way)",
    "Representation",
    "Threshold Parity"
  ],
  "metadata": {
    "clinical": {
      "useCase":          "30-Day Readmission Prediction",
      "outcome":          "predicted for readmission within 30 days",
      "population":       "Adult Inpatients (All Wards)",
      "department":       "Hospital Medicine",
      "patientsPerMonth": 2400,
      "complianceNote":   "CMS Hospital Readmissions Reduction Program"
    }
  }
}
```

**Response schema**

| field | type | description |
|---|---|---|
| `run_id` | `string` (UUID) | Unique identifier for this audit run |
| `created_at` | `string` (ISO 8601) | Timestamp when the run was persisted |
| `model_name` | `string` | Model identifier |
| `model_version` | `string \| null` | Optional version tag |
| `window_size` | `integer \| null` | Number of prediction events included in this window |
| `status` | `string` | Always `"completed"` for runs returned by this endpoint |
| `metric_count` | `integer` | Total fairness metric rows written |
| `alert_count` | `integer` | Total alert rows written |
| `dimensions` | `string[]` | Dimensions that produced at least one metric |
| `metadata` | `object \| null` | JSON blob written by the worker — contains `clinical` key with dashboard display context |

**Errors**

| status | condition |
|---|---|
| `404` | No audit runs found for `model_name` |

---

### `GET /alerts/latest`

Returns fairness alerts from the most recent audit run for a model, sorted by creation time descending.

**Query parameters**

| param | type | required | default | constraints |
|---|---|---|---|---|
| `model_name` | `string` | yes | — | min length 1 |
| `limit` | `integer` | no | `50` | 1 – 1000 |

**Response `200`**

```json
{
  "model_name": "readmission_v2",
  "run_id":     "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "count":      18,
  "items": [
    {
      "alert_id":    101,
      "created_at":  "2026-04-25T21:27:12.000Z",
      "run_id":      "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "dimension":   "Demographic Fairness",
      "attribute":   "race",
      "subgroup":    null,
      "severity":    "RED",
      "message":     "race max_auc_gap=0.2341",
      "signal_value": 0.2341,
      "threshold_config": { "red": 0.2, "yellow": 0.1 }
    }
  ]
}
```

**`AlertItem` schema**

| field | type | description |
|---|---|---|
| `alert_id` | `integer` | Auto-incrementing primary key |
| `created_at` | `string` (ISO 8601) | |
| `run_id` | `string` (UUID) | Links back to the audit run |
| `dimension` | `string` | One of the 9 worker dimensions |
| `attribute` | `string \| null` | Protected attribute name (e.g. `"race"`, `"gender"`) |
| `subgroup` | `string \| null` | Specific value within the attribute (e.g. `"Black"`) or compound key for intersectionality (`"race=Black\|gender=F"`) |
| `severity` | `string` | `RED`, `YELLOW`, `GREEN`, or `INSUFFICIENT_DATA` |
| `message` | `string \| null` | Raw worker message — prefer `signal_value` for programmatic use |
| `signal_value` | `float \| null` | The raw metric value that triggered this alert (see interpretation table below) |
| `threshold_config` | `object` | The thresholds active when this alert was created |

**`signal_value` interpretation by dimension**

| dimension | what `signal_value` represents | example |
|---|---|---|
| `Demographic Fairness` | Max AUC gap between subgroup and rest (0–1 scale) | `0.23` |
| `Representation` | Effective sample count proxy / low-sample indicator | `8.0` |
| `Intersectionality (2-way)` | Compound subgroup disparity score | `0.61` |
| `Fairness Drift` | Trend slope of fairness gap over windows | `0.031` |
| `Threshold Parity` | Gap in positive decision rates at operating threshold | `0.18` |
| `False Negative Gap` | Gap in missed-positive rate across groups | `0.22` |
| `Calibration Fairness` | Gap between predicted risk and observed outcome rates | `0.11` |
| `Feature Drift` | Drift signal (uses KS-based alerting) | `0.27` |
| `Algorithmic Drift (PELT)` | Performance drop from baseline over recent windows | `0.09` |

**Errors**

| status | condition |
|---|---|
| `404` | No audit runs found for `model_name` |

---

### `GET /metrics/latest`

Returns raw fairness metric rows from the most recent audit run. Useful for building custom visualisations or exporting data.

**Query parameters**

| param | type | required | default | constraints |
|---|---|---|---|---|
| `model_name` | `string` | yes | — | min length 1 |
| `dimension` | `string` | no | all dimensions | exact match |
| `limit` | `integer` | no | `200` | 1 – 5000 |

**`dimension` filter values**: any of the 9 dimensions listed above.

**Response `200`**

```json
{
  "model_name": "readmission_v2",
  "run_id":     "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "dimension":  null,
  "count":      142,
  "items": [
    {
      "metric_id":    501,
      "created_at":   "2026-04-25T21:27:11.000Z",
      "run_id":       "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "dimension":    "Demographic Fairness",
      "attribute":    "race",
      "subgroup":     null,
      "metric_name":  "max_auc_gap",
      "metric_value": 0.2341,
      "metadata":     { "overall_auc": 0.78 }
    },
    {
      "metric_id":    502,
      "created_at":   "2026-04-25T21:27:11.000Z",
      "run_id":       "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "dimension":    "Fairness Drift",
      "attribute":    "race",
      "subgroup":     "window_3",
      "metric_name":  "window_gap",
      "metric_value": 0.18,
      "metadata":     { "window_id": 3 }
    }
  ]
}
```

**`MetricItem` schema**

| field | type | description |
|---|---|---|
| `metric_id` | `integer` | Auto-incrementing primary key |
| `created_at` | `string` (ISO 8601) | |
| `run_id` | `string` (UUID) | |
| `dimension` | `string` | Fairness dimension |
| `attribute` | `string \| null` | Protected attribute |
| `subgroup` | `string \| null` | Specific value or window label |
| `metric_name` | `string` | See metric name reference below |
| `metric_value` | `float \| null` | Raw numeric value |
| `metadata` | `object` | Dimension-specific extra fields |

**Metric name reference**

| `metric_name` | dimension | description |
|---|---|---|
| `max_auc_gap` | Demographic Fairness | Largest AUC gap across groups for an attribute |
| `overall_auc` | Demographic Fairness | Overall AUC in this run |
| `n`, `n_eff`, `positive_rate` | Representation | Subgroup sample reliability and prevalence markers |
| `auc_subgroup`, `gap_vs_overall`, `score` | Intersectionality (2-way) | Compound subgroup fairness metrics |
| `window_gap`, `gap_trend_slope` | Fairness Drift | Time trend metrics |
| `positive_rate_at_threshold`, `parity_gap` | Threshold Parity | Threshold action-rate parity metrics |
| `fnr`, `fnr_gap` | False Negative Gap | Missed-positive safety gap metrics |
| `calibration_error`, `calibration_gap` | Calibration Fairness | Risk-score reliability parity metrics |
| `ks_stat`, `ks_pvalue`, `psi` | Feature Drift | Input distribution shift metrics |
| `baseline_auc`, `current_auc`, `auc_drop` | Algorithmic Drift (PELT) | Performance drift metrics |

**Errors**

| status | condition |
|---|---|
| `404` | No audit runs found for `model_name` |

---

### `GET /audit/files/{run_id}`

Returns file artifacts for a run stored on disk (legacy — used by the file-based audit pipeline, not the Supabase worker). Only relevant if you used `sdk_runner.py` to run an audit from a CSV.

**Path parameters**

| param | type | description |
|---|---|---|
| `run_id` | `string` | Run ID returned by `sdk_runner.py` |

**Response `200`**

```json
{
  "run_id":    "20260425_143022_abc123",
  "metadata":  { "overall_status": "RED", "alert_count": 5 },
  "available_files": ["alerts.csv", "metrics.csv", "run_metadata.json"],
  "output_dir": "runs/sdk_outputs/20260425_143022_abc123"
}
```

**Errors**

| status | condition |
|---|---|
| `404` | Run directory not found on disk |

---

### `GET /stream/alerts`

Server-Sent Events (SSE) stream that polls for new alerts since the last seen `alert_id`. This endpoint is a fallback — the dashboard uses Supabase Realtime directly instead. Included for integrations that cannot use WebSockets.

**Query parameters**

| param | type | required | description |
|---|---|---|---|
| `model_name` | `string` | yes | Model to stream alerts for |

**Response** — `text/event-stream`

```
event: ready
data: {"model_name": "readmission_v2", "cursor": 100}

event: alert
data: {"type": "metric_alert_insert", "data": { ...AlertItem... }}

event: alert
data: {"type": "metric_alert_insert", "data": { ...AlertItem... }}
```

The stream polls every 3 seconds (configurable via `API_STREAM_POLL_SECONDS` env var). Keep the connection open; the server will push new events as they arrive.

---

## Error format

All errors return a standard FastAPI error body:

```json
{
  "detail": "No runs found for model_name=unknown_model"
}
```

---

## Environment variables

| variable | required | description |
|---|---|---|
| `SUPABASE_URL` | yes | Supabase project URL |
| `SUPABASE_KEY` | yes | Supabase anon or service-role key |
| `SUPABASE_SCHEMA` | no (default: `fairnessops`) | Database schema name |
| `API_STREAM_POLL_SECONDS` | no (default: `3.0`) | SSE poll interval in seconds |

For scheduler flows (outside API process), common variables include:

| variable | required | description |
|---|---|---|
| `DATASET_MODE` | no (default: `cancer`) | `cancer`, `eicu`, or `synthetic` |
| `EICU_DATA_PATH` | required when `eicu` | Local path to eICU-style CSV |
| `SYNTH_MODEL_NAME` | no | Model name used by synthetic runtime |
| `SYNTH_ROWS` | no | Synthetic population size |
| `SYNTH_SEED` | no | Synthetic RNG seed |

---

## CORS

The API allows cross-origin requests from `http://localhost:3000` and `http://127.0.0.1:3000` (the Next.js dashboard). All HTTP methods and headers are permitted. Update `api/main.py` `allow_origins` before deploying to a non-localhost environment.
