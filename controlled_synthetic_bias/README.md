# Controlled Synthetic Bias Experiment

This folder contains a reproducible validation harness for FairnessOps.

## Why this exists
Synthetic bias injection helps validate that fairness metrics are not just "numbers" but respond in the expected direction when known harms are introduced.

In short: we intentionally perturb prediction scores, rerun the exact fairness pipeline, and verify expected changes.

---

## Files

- `run_bias_tests.py`  
  Retrains a logistic regression baseline on `runs/canonical_dataset.csv`, generates test predictions, applies controlled bias scenarios, and exports fairness outputs per scenario.

- `analyze_bias_results.py`  
  Reads scenario outputs, runs directional validation checks, and writes a markdown summary report.

- `canonical_dataset.csv`  
  Local copy used by this experiment (copied from `runs/canonical_dataset.csv`).

- `results/`  
  Contains one subfolder per scenario plus cross-scenario summary files.

---

## Scenarios

1. `baseline`  
   No score perturbation.

2. `ethnicity_downweight`  
   Decrease predicted risk for `ethnicity == African American` by 0.15 (clipped to [0,1]).

3. `female_over65_downweight`  
   Decrease predicted risk for `(gender == Female) AND (age_group == over_65)` by 0.20.

4. `region_drift_like`  
   Decrease predicted risk for `region == South` in the final third of rows by 0.25 to emulate worsening late-window behavior.

---

## What gets exported per scenario

- `fairness_by_attribute.csv`
- `fairness_by_group.csv`
- `representation.csv`
- `intersectionality_all.csv`
- `intersectionality_top.csv`
- `fairness_drift.csv`
- `fairness_drift_summary.csv`
- `predictions.csv`
- `scenario_metrics.csv`

Cross-scenario:
- `results/scenario_comparison.csv`

---

## How to run

From project root:

```bash
python controlled_synthetic_bias/run_bias_tests.py
python controlled_synthetic_bias/analyze_bias_results.py
```

Generated report:
- `controlled_synthetic_bias/results/VALIDATION_REPORT.md`

---

## Validation logic (high level)

The analysis script checks expected directional behavior:

- Ethnicity-targeted perturbation should increase ethnicity gap.
- Female+over_65 perturbation should increase at least one of gender/age gaps.
- Region drift-like perturbation should not reduce region gap.
- Representation status should remain stable when only prediction scores are changed.
- Region drift alert should be at least as strong in drift-like scenario.

PASS means behavior matched expectation.  
WARN means the signal is weak/ambiguous and should be inspected.

---

## Important caveat

Fairness drift in this MVP is computed with window simulation, not true timestamped production streams.  
This validates implementation sensitivity, not real-world temporal causality.
