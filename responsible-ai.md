# Responsible AI - FairnessOps

---

## Data Sources

### 1. eICU Collaborative Research Database (Demo v2.0.1)

A de-identified, multi-center ICU dataset from Philips Healthcare and MIT Lab for Computational Physiology. The demo subset is publicly available at [eicu-crd.mit.edu](https://eicu-crd.mit.edu/). The full credentialed version requires a data use agreement.

**Tables used:** `apachePatientResult`, `lab`, `vitalPeriodic`, `hospital`

**Features extracted:**
- Lab values: creatinine, sodium, glucose, potassium
- Vital signs: heart rate, SpO2, respiration rate
- Clinical severity: APACHE score
- Protected attributes: ethnicity, gender, age group, region (hospital-derived)
- Outcome: in-hospital mortality (`y_true`)

All records are de-identified per HIPAA Safe Harbor. No patient names, exact ages, or direct identifiers are stored or logged.

**Known limitations:**
- The demo subset covers roughly 200 hospitals. Ethnic group sample sizes become thin for minority populations in smaller hospitals.
- eICU ethnic categories do not align with US Census definitions and likely undercount some communities.
- Groups with insufficient representation are flagged `INSUFFICIENT_DATA` rather than silently excluded, but the underlying fairness question for those groups remains unresolved.

### 2. Kaggle Clinical Dataset (`imtkaggleteam/clinical-dataset`)

A public clinical survival dataset downloaded via `kagglehub`. Used only in the `cancer` scheduler mode to generate a prediction event stream for demonstration. Not used for any patient-facing output. The dataset's provenance is not fully documented by its publisher; for this reason it is restricted to demo mode only.

### 3. Synthetic Runtime Dataset

Generated programmatically in `FairnessOps_Testing/scheduler_runtime_synthetic.py` using NumPy with a fixed seed (`SYNTH_SEED=42`). Contains 5,000 rows. No real patient data.

**How the synthetic data is structured:**

The true risk process reflects documented ICU disparities: `over_65` and `Black` ethnicity patients carry higher baseline mortality risk, consistent with published ICU literature.

The prediction signal adds deliberate bias on top of that risk process to simulate a model trained on historically skewed data:
- Black patients: -0.35 logit reduction in predicted risk
- Black male patients: additional -0.28 logit
- Over-65 patients: -0.18 logit reduction
- Feature drift in glucose, heart rate, and APACHE scores starting at 55% of the window

The injected bias exists in the monitored model signal, not in the FairnessOps monitoring layer.

### 4. Controlled Bias Scenarios (`controlled_synthetic_bias/`)

Four scenarios applied to the canonical eICU-derived dataset to validate that fairness dimensions respond correctly to known harms:

| Scenario | Perturbation |
|----------|-------------|
| Baseline | No changes |
| Ethnicity downweight | -0.15 predicted risk for African American patients |
| Female over-65 downweight | -0.20 for Female + over_65 patients |
| Region drift | -0.25 for South region patients in the final third of rows |

All four produce the expected alerts. Results: `controlled_synthetic_bias/results/VALIDATION_REPORT.md`

---

## Model Choices

FairnessOps is a monitoring layer. It does not make clinical decisions. The reference models used for testing and demonstration are logistic regression classifiers.

**Algorithm:** `sklearn.linear_model.LogisticRegression`

**Why logistic regression:**

From a developer perspective, logistic regression outputs calibrated probabilities, which is a hard requirement for the Calibration Fairness dimension. Its coefficients are directly inspectable, which makes it easier to trace why a specific fairness alert fired back to specific features.

From a clinical perspective, logistic regression underlies many deployed clinical risk scores, including variations of APACHE, NEWS, and early warning systems. Testing against it means testing against something representative of real ICU deployments.

The reference models are trained without fairness-aware techniques deliberately, to produce realistic biased signals for the monitoring system to detect.

**Configuration:**

```python
LogisticRegression(
    max_iter=1000,
    class_weight="balanced",   # adjusts for outcome imbalance; mortality is rare (~10-15%)
    solver="liblinear",
    random_state=42
)
```

Missing numeric values: median imputation. Missing demographic values: filled with `"Unknown"` to ensure no patient is silently excluded from fairness calculations.

**Operating threshold: 0.40** (not 0.50). In an ICU triage context, a missed high-risk patient (false negative) carries more clinical risk than an unnecessary escalation. This threshold is configurable in `WorkerConfig` and is itself monitored by the Threshold Parity dimension.

**What FairnessOps does not do:**
- Does not retrain or modify the monitored model
- Does not alter, suppress, or override any clinical score
- Does not make or block clinical decisions

All responses to fairness alerts are human decisions made by clinical staff, informatics teams, or compliance officers.

---

## Bias Considerations

### Protected attributes monitored by default

| Attribute | Why it is monitored |
|-----------|---------------------|
| `ethnicity` | Structural disparities in healthcare access and historical under-treatment create documented mortality gaps across ethnic groups in ICU data. Models trained on historical records inherit these patterns. |
| `gender` | Women are historically under-diagnosed for certain conditions, including cardiac events. This can introduce label noise into training data in ways that reduce model reliability for women. |
| `age_group` | Comorbidity profiles differ significantly by age. Clinical escalation norms for elderly patients differ from younger cohorts in ways that can embed into training labels. |
| `region` | Hospital resources, protocols, and population health vary significantly by geography. Models trained primarily on urban academic medical center data may underperform at rural critical access hospitals. |

`insurance` and `language` are collected in the event schema but not included by default. They can be added to any `WorkerConfig`.

### Known data biases

**APACHE score:** The APACHE severity system has documented calibration gaps across ethnic groups (Glance et al., 2012; Decruyenaere et al., 2020). Using APACHE as a model feature propagates that existing bias into the model signal. FairnessOps surfaces this rather than concealing it.

**Outcome imbalance:** In-hospital ICU mortality is a rare event at approximately 10-15% prevalence. Even with `class_weight="balanced"`, the precision-recall tradeoff affects minority groups disproportionately because they have fewer positive cases in the training window.

**Synthetic bias is labeled:** Every injected score penalty is documented in source code and in this document. No injected bias exists in the monitoring infrastructure. It exists only in the reference models being monitored.

### Metric limitations

| Dimension | What it measures | What it misses |
|-----------|-----------------|----------------|
| Demographic Fairness | AUC gap across groups | AUC is rank-based; does not reflect calibration or threshold effects |
| Threshold Parity | Positive-flag rate gap at operating threshold | The operating threshold itself may have been chosen in a way that disadvantages certain groups |
| False Negative Rate Gap | Missed-high-risk rate per group at threshold | Sensitive to class imbalance; noisy for small rare-event groups |
| Calibration Fairness | Mean predicted risk vs. observed event rate per group | Unreliable for groups with very few positive outcomes |
| Intersectionality | 2-way cross-attribute combinations | 3-way and above combinations are not computed due to sample size collapse |
| Fairness Drift | Linear slope of AUC gap across rolling windows | Will not detect non-linear or oscillating drift patterns |
| Algorithmic Drift | PELT changepoint detection on overall AUC | Requires `ruptures`; degrades to trend-only without it |
| Feature Drift | KL divergence on numeric features per window | Categorical feature drift is not tracked |
| Representation | Effective sample size per group | Does not assess whether the demographic category definitions are clinically meaningful |

FairnessOps implements **group fairness**: equal AUC, equal FNR, and equal calibration across defined demographic categories. This is not the same as individual fairness or equity. Group fairness metrics are used because they are computable from logged prediction data without counterfactuals, and they align with current CMS and ONC guidance on AI bias monitoring.

---

## Failure Cases

### Groups too small to evaluate

If a demographic group has fewer than 30 prediction events in the rolling window, or if all patients in the group share the same outcome, the group is marked `INSUFFICIENT_DATA`. No alert fires for that group.

A small, systematically disadvantaged group at a low-volume hospital may never accumulate enough records to produce actionable metrics. The Representation dimension flags groups as `suppressed` or `low_confidence` on the dashboard, but the fairness question for those groups remains open.

### Worker finds no events

If the worker finds zero prediction events for the configured model name, it exits cleanly without creating an audit run. This can occur due to a model name mismatch, a Supabase connectivity issue, or the monitored service having stopped logging predictions.

The dashboard will continue showing the previous run with no indication that monitoring has lapsed. Production deployments should implement an external health check on `MAX(created_at)` in the prediction events table and alert on staleness.

### Missing demographic data

Prediction events with null protected attribute values are filled with the string `"Unknown"` in `prepare_scored_frame()`. The `"Unknown"` group participates in fairness calculations like any named group.

If demographic data collection is sparse (common in real EHR environments), the `"Unknown"` group can grow large enough to dilute observed disparities. FairnessOps reports its size via the Representation dimension. The root cause is data collection quality at the EHR or intake workflow level.

### Noisy calibration alerts for small groups

Calibration error is the absolute difference between mean predicted probability and observed event rate within a group. For groups with very few positive outcomes, this estimate has high variance. A spurious RED calibration alert is possible. Alerts include `row_kind` metadata to distinguish per-group detail rows from attribute-level summaries, which helps reviewers assess whether an alert reflects a real pattern or small-sample noise.

### PELT changepoint detection without `ruptures`

If `ruptures` is not installed, `_detect_pelt_changepoints()` catches the `ImportError` and returns an empty list. Window-by-window AUC trends are still reported. Severity thresholds on trend slope still fire if the drop is large enough. The precise changepoint timestamp will not be available. Install with `pip install ruptures` for full capability.

### Single-tenant architecture

FairnessOps is designed for single-organization deployment. All models share the same Supabase schema. There is no row-level security separating data from different clinical departments or organizations.

Do not deploy in a multi-tenant context without implementing Supabase row-level security or per-organization schema isolation. Multi-tenant isolation is the next infrastructure milestone on the roadmap.

### LLM-generated clinical summaries

The AI Analysis panel uses OpenAI GPT to generate plain-language summaries of fairness findings. These can overstate the significance of borderline metrics or introduce clinical framing that is not supported by the underlying data.

Summaries are labeled as AI-generated in the UI. The underlying numeric metrics are always displayed alongside the narrative. The feature is fully optional; the dashboard functions without an OpenAI key. Any summary used in governance reporting should be reviewed before distribution.

---

## Compliance Context

FairnessOps produces audit records relevant to:

- **CMS AI Transparency and Bias Rule (2025):** Documentation of AI-assisted clinical decision processes
- **ONC Health Data, Technology, and Interoperability Rule:** Algorithmic bias in certified health IT
- **Joint Commission:** Evolving standards on health equity and AI oversight

Each audit run writes an immutable record to Supabase containing model name, prediction window size, dimension results, alert severities, clinical context metadata, and a timestamp. The Compliance view in the dashboard surfaces these records in a format exportable for regulatory or accreditation review.

FairnessOps produces an audit trail. Compliance with any specific regulation depends on broader organizational practices outside the scope of this tool.

---

_Last updated: April 2026_
