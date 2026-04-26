# SDK Testing

This folder contains lightweight scripts to test the FairnessOps SDK end-to-end.

## Scripts

- `test_sdk_smoke.py`  
  Runs one baseline audit and verifies all required artifacts are produced.

- `test_sdk_contract.py`  
  Validates output schema, enum labels, and metadata keys for the latest smoke run.

- `test_sdk_scenarios.py`  
  Runs all synthetic scenarios through the SDK and exports a comparison summary.

## How to run

From project root:

```bash
python SDK_testing/test_sdk_smoke.py
python SDK_testing/test_sdk_contract.py
python SDK_testing/test_sdk_scenarios.py
python SDK_testing/run_all_tests.py
```

## Expected outputs

- Smoke run artifacts: `runs/sdk_test_outputs/smoke/<run_id>/`
- Scenario summary: `runs/sdk_test_outputs/scenarios/scenario_test_summary.csv`
