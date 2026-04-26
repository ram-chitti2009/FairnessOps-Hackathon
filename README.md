# FairnessOps

Continuous fairness monitoring for clinical AI models, running in production.

---

## Team Members

| Name | GitHub Handle |
|------|---------------|
| Ram | [@Ram](https://github.com/ram-chitti2009) |


---

## Problem Statement

Clinical AI models are routinely deployed without any mechanism for ongoing fairness monitoring. A model may pass a pre-deployment audit and still degrade silently over months, producing systematically worse risk scores for specific patient groups while overall accuracy metrics remain unchanged.

For a clinician, this is invisible. The model's score arrives in the EHR, and there is no indication that it is less reliable for a Black patient in the ICU than for a White patient, or that its performance on elderly women has been declining for six weeks. Without a monitoring layer, that information never reaches the care team, the CMIO, or the compliance team.

The specific failure modes this project targets:

- Subgroup AUC gaps that were not present at deployment but emerge as patient populations shift
- False negative rate disparities, where the model systematically misses high-risk patients in specific demographic groups
- Calibration drift, where the model's predicted probabilities stop matching observed outcomes for certain groups
- Intersectional gaps that single-attribute checks miss, such as a combined effect on elderly Black women that is larger than either attribute alone
- Feature distribution shifts that precede or explain fairness degradation

---

## Solution

FairnessOps is a Python SDK that wraps any clinical prediction model with a decorator and continuously monitors it across 9 fairness dimensions. Results are stored as immutable audit records and surfaced on a real-time dashboard with plain-language clinical summaries and severity-graded alerts.

### Integration

One decorator instruments the model. No changes to model logic are required.

```python
from SDK.monitor.decorator import monitor

@monitor(
    model_name="icu_deterioration_v1",
    protected_attrs=["ethnicity", "gender", "age_group", "region"]
)
def predict(X: pd.DataFrame) -> list[float]:
    return model.predict_proba(X)[:, 1].tolist()
```

Every call logs a prediction event to Supabase: score, patient demographics, clinical features, and ground truth outcome when available.

### Scheduled worker

A background scheduler (`FairnessOps_Testing/scheduler.py`) sends prediction batches every 30 seconds and runs the full fairness worker every 2 minutes. The worker pulls the most recent rolling window of events and computes all 9 dimensions.

### Dashboard

Results appear on a Next.js dashboard at `http://localhost:3000`. For clinicians and clinical leadership, each dimension shows a RED / YELLOW / GREEN severity, a plain-English description of what was found, and a trend chart. For developers, the underlying metric values and per-group breakdowns are accessible. An optional LLM summary (OpenAI) translates findings into clinical narrative.

### The 9 fairness dimensions

Each dimension maps to a specific clinical harm, not just a statistical property.

| Dimension | Clinical meaning |
|-----------|-----------------|
| **Demographic Fairness** | Is model accuracy (AUC) consistent across ethnic groups, genders, age bands, and regions? |
| **Representation** | Does each group have enough patients in the window to make the metrics statistically reliable? |
| **Intersectionality** | Are any cross-group combinations (e.g., elderly Black women) experiencing larger gaps than single-attribute checks would show? |
| **Fairness Drift** | Is the AUC gap between groups growing over time? |
| **Threshold Parity** | Are some groups being flagged positive at materially different rates at the operating threshold? |
| **False Negative Rate Gap** | Which groups is the model most likely to miss? A missed high-risk patient is the most direct clinical harm. |
| **Calibration Fairness** | Does the model's predicted probability match the observed event rate equally across groups? |
| **Feature Drift** | Have input distributions (labs, vitals) shifted in ways that could explain fairness changes? |
| **Algorithmic Drift (PELT)** | Has overall model AUC dropped, and can the point of change be detected? |

### Bias validation harness

`controlled_synthetic_bias/` injects known perturbations into a real ICU dataset and confirms the expected dimensions fire:

| Scenario | Perturbation | Expected signal |
|----------|-------------|-----------------|
| Baseline | None | All GREEN |
| Ethnicity downweight | -0.15 predicted risk for African American patients | RED on Demographic Fairness and FNR Gap |
| Female over-65 downweight | -0.20 for Female + over_65 | RED on Intersectionality |
| Region drift | -0.25 for South region in final third of window | RED on Fairness Drift |

Full results: `controlled_synthetic_bias/results/VALIDATION_REPORT.md`

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| SDK language | Python 3.9+ |
| Fairness compute | NumPy, Pandas, scikit-learn |
| Changepoint detection | `ruptures` (PELT algorithm) |
| Database + realtime | Supabase (PostgreSQL + WebSocket) |
| Backend API | FastAPI, Uvicorn |
| Dashboard | Next.js 14, TypeScript, Tailwind CSS |
| LLM narrative | OpenAI GPT via `/api/llm` route (optional) |
| Alerting | Slack Incoming Webhooks (optional) |

**Data sources:**

- **eICU Collaborative Research Database (Demo 2.0.1):** De-identified ICU records from roughly 200 US hospitals. Lab values, vital signs, APACHE scores, in-hospital mortality outcomes.
- **Kaggle clinical dataset** (`imtkaggleteam/clinical-dataset`): Used only for the cancer scheduler mode.
- **Synthetic runtime:** A reproducible 5,000-row dataset generated in code with known fairness gaps embedded. Used for demo and testing.

---

## Setup

Prerequisites: Python 3.9+, Node.js 18+, a Supabase project (free tier sufficient). OpenAI and Slack are optional.

### 1. Install

```bash
git clone <repo-url>
cd "Fairness Ops"
pip install -e .
```

### 2. Environment variables

```bash
cp .env.example .env
```

```env
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_KEY=<service-role-key>
SUPABASE_SCHEMA=fairnessops
SUPABASE_PREDICTION_TABLE=prediction_events
OPENAI_API_KEY=sk-...            # optional
SLACK_WEBHOOK_URL=https://hooks.slack.com/...   # optional

DATASET_MODE=synthetic           # synthetic | eicu | cancer
SYNTH_MODEL_NAME=synthetic_monitor_v1
SYNTH_ROWS=5000
SYNTH_SEED=42
```

### 3. Supabase tables

Create in the `fairnessops` schema:
- `prediction_events`
- `audit_runs`
- `fairness_metrics`
- `metric_alerts`

### 4. Start the API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Swagger UI: `http://localhost:8000/docs`

### 5. Start the dashboard

```bash
cd dashboard-next
npm install
npm run dev
```

Dashboard: `http://localhost:3000`

### 6. Start the scheduler

```bash
python FairnessOps_Testing/scheduler.py
```

Logs prediction batches every 30 seconds, runs the fairness worker every 2 minutes. Sends Slack alerts for RED and YELLOW findings if the webhook is configured.

### 7. One-off audit from a CSV

```bash
python sdk_runner.py \
  --input-csv runs/canonical_dataset.csv \
  --protected-attrs ethnicity gender age_group region \
  --output-root runs/sdk_outputs
```

### 8. Tests

```bash
cd SDK_testing
python run_all_tests.py
```

---

## Demo

The demo runs in synthetic mode with bias injected into the generated model:

- Ethnicity AUC gap of roughly 0.12-0.18 between Black and White patients
- Elevated false negative rate for Black patients
- Feature drift starting at 55% through the window
- PELT changepoint detection fires in the final windows

**Dashboard pages:**
- **Overview:** Health score, active alerts, dimension status grid, AI summary
- **Drift:** Trend charts for fairness and algorithmic drift over time
- **Incidents:** Alert history in clinical language
- **Compliance:** Exportable audit trail for regulatory review

> _Add screenshots or a Loom recording here before final submission._

---

## Repo Layout

```
SDK/
  monitor/          @monitor decorator, Supabase prediction logger
  workers/          fairness worker: fetch events, compute 9 dimensions, persist results
    compute/        one module per dimension
FairnessOps_Testing/
  scheduler.py                       orchestrates prediction logging and worker runs
  scheduler_runtime_synthetic.py     synthetic dataset and biased reference model
  scheduler_runtime_eicu.py          eICU runtime
api/                FastAPI backend: audit runs, alerts, metrics, SSE stream
dashboard-next/     Next.js dashboard
controlled_synthetic_bias/   bias injection harness and validation report
SDK_testing/        integration and scenario tests
```
