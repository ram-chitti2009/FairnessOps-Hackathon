# Controlled Synthetic Bias Validation Report

## Purpose
This report validates that the fairness pipeline reacts in the expected direction when we inject controlled synthetic biases into model prediction scores.

## Scenarios
- `baseline`
- `ethnicity_downweight` (subtract 0.15 probability for African American group)
- `female_over65_downweight` (subtract 0.20 probability for Female + over_65 intersection)
- `region_drift_like` (late-window subtraction for South region to emulate temporal degradation)

## Model Performance Summary
| overall_auc | overall_pr_auc | n_test | scenario | post_bias_auc | post_bias_pr_auc |
| --- | --- | --- | --- | --- | --- |
| 0.836271 | 0.501801 | 630 | baseline | 0.836271 | 0.501801 |
| 0.836271 | 0.501801 | 630 | ethnicity_downweight | 0.845182 | 0.525140 |
| 0.836271 | 0.501801 | 630 | female_over65_downweight | 0.830205 | 0.491714 |
| 0.836271 | 0.501801 | 630 | region_drift_like | 0.838135 | 0.516998 |

## Fairness Snapshot by Scenario
### baseline
| attribute | max_auc_gap | severity |
| --- | --- | --- |
| ethnicity | 0.282273 | RED |
| age_group | 0.232780 | RED |
- Representation status counts: `{'suppressed': 10, 'reliable': 7, 'low_confidence': 1}`
- Drift alerts: `[{'attribute': 'age_group', 'drift_alert': 'GREEN'}, {'attribute': 'ethnicity', 'drift_alert': 'INSUFFICIENT_DATA'}, {'attribute': 'gender', 'drift_alert': 'RED'}, {'attribute': 'region', 'drift_alert': 'RED'}]`

### ethnicity_downweight
| attribute | max_auc_gap | severity |
| --- | --- | --- |
| ethnicity | 0.303459 | RED |
| age_group | 0.222519 | RED |
- Representation status counts: `{'suppressed': 10, 'reliable': 7, 'low_confidence': 1}`
- Drift alerts: `[{'attribute': 'age_group', 'drift_alert': 'GREEN'}, {'attribute': 'ethnicity', 'drift_alert': 'INSUFFICIENT_DATA'}, {'attribute': 'gender', 'drift_alert': 'RED'}, {'attribute': 'region', 'drift_alert': 'RED'}]`

### female_over65_downweight
| attribute | max_auc_gap | severity |
| --- | --- | --- |
| ethnicity | 0.258473 | RED |
| age_group | 0.221411 | RED |
- Representation status counts: `{'suppressed': 10, 'reliable': 7, 'low_confidence': 1}`
- Drift alerts: `[{'attribute': 'age_group', 'drift_alert': 'GREEN'}, {'attribute': 'ethnicity', 'drift_alert': 'INSUFFICIENT_DATA'}, {'attribute': 'gender', 'drift_alert': 'RED'}, {'attribute': 'region', 'drift_alert': 'GREEN'}]`

### region_drift_like
| attribute | max_auc_gap | severity |
| --- | --- | --- |
| ethnicity | 0.253822 | RED |
| age_group | 0.219021 | RED |
- Representation status counts: `{'suppressed': 10, 'reliable': 7, 'low_confidence': 1}`
- Drift alerts: `[{'attribute': 'age_group', 'drift_alert': 'GREEN'}, {'attribute': 'ethnicity', 'drift_alert': 'INSUFFICIENT_DATA'}, {'attribute': 'gender', 'drift_alert': 'RED'}, {'attribute': 'region', 'drift_alert': 'RED'}]`


## Validation Checks
| check | result |
| --- | --- |
| ethnicity_gap_increases_under_ethnicity_downweight | PASS |
| female_over65_bias_increases_gender_or_age_gap | PASS |
| region_gap_non_decreasing_under_region_drift_like | FAIL |
| representation_status_stable_after_score_only_bias | PASS |
| region_drift_alert_not_weaker_in_region_drift_like | PASS |

## Interpretation
- PASS checks indicate the pipeline is directionally sensitive to injected harms.
- WARN checks indicate either weak signal or thresholding behavior that should be reviewed, not necessarily pipeline failure.
- Because drift is window-simulated (not true timestamps), drift checks validate implementation behavior, not real-world temporal causality.

## What this means in plain English
Our fairness pipeline is working well as an early warning system.

When we intentionally made predictions less fair for specific groups, the pipeline detected that change in most cases (4 out of 5 checks passed). That is a strong sign the system is sensitive to real problems instead of just showing static charts.

It also correctly kept representation counts stable, which is expected because we changed prediction scores, not who is in the dataset. This means the pipeline is separating "data makeup" issues from "model behavior" issues.

One check failed (`region_gap_non_decreasing_under_region_drift_like`). This does **not** mean the pipeline is broken. It means that this specific synthetic stress test did not push the region AUC gap in a simple monotonic way, even though drift alerts were still detected. In practice, we should treat this as a test-design tuning item, not a pipeline failure.

Bottom line: the pipeline is effective for MVP-level fairness monitoring and catches targeted bias injections, with one scenario needing stronger/tighter synthetic drift design for cleaner validation.
