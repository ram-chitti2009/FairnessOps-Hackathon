"""
FairnessOps end-to-end test using the Kaggle clinical dataset.

Flow:
  1. Download dataset (imtkaggleteam/clinical-dataset)
  2. Clean + encode features
  3. Train a LogisticRegression survival model
  4. Wrap predict() with @monitor → logs events to Supabase
  5. Run 25 passes over the dataset to seed enough events for the worker
  6. Run the 4-dimension fairness worker
  7. Open http://localhost:3000 to see results on the dashboard

Run from the project root:
  python FairnessOps_Testing/train_and_monitor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so SDK imports work
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import kagglehub
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OrdinalEncoder

load_dotenv(ROOT / ".env")

from SDK.monitor.decorator import monitor
from SDK.workers.config import WorkerConfig
from SDK.workers.run_worker import run_once


# ── 1. Download ───────────────────────────────────────────────────────────────
print("Downloading dataset...")
dataset_path = Path(kagglehub.dataset_download("imtkaggleteam/clinical-dataset"))
df = pd.read_csv(dataset_path / "Clinical Data_Discovery_Cohort.csv")

# Also load validation cohort and stack for more rows
try:
    df_val = pd.read_excel(dataset_path / "Clinical_Data_Validation_Cohort.xlsx")
    # Align columns if they match
    if set(df.columns) == set(df_val.columns):
        df = pd.concat([df, df_val], ignore_index=True)
        print(f"Loaded discovery + validation cohorts: {len(df)} rows total")
    else:
        print(f"Validation cohort has different columns — using discovery only: {len(df)} rows")
except Exception as e:
    print(f"Could not load validation cohort ({e}) — using discovery only: {len(df)} rows")


# ── 2. Clean + feature engineering ───────────────────────────────────────────

# Map abbreviated race/sex codes to full labels for the dashboard
RACE_MAP = {"W": "White", "B": "Black", "A": "Asian", "O": "Other"}
SEX_MAP  = {"M": "Male", "F": "Female"}

df["race"]   = df["race"].map(RACE_MAP).fillna("Other")
df["gender"] = df["sex"].map(SEX_MAP).fillna("Unknown")

# Simplify stage: anything with N1/N2 → "Advanced", otherwise "Early"
def simplify_stage(raw: str) -> str:
    s = str(raw).strip().upper()
    if any(x in s for x in ["N2", "N1", "N1MX", "N2MX"]):
        return "Advanced"
    return "Early"

df["stage_group"] = df["Stage"].apply(simplify_stage)

# Encode categorical features for the model
enc_gender = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
enc_stage  = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)

df["gender_enc"] = enc_gender.fit_transform(df[["gender"]])
df["stage_enc"]  = enc_stage.fit_transform(df[["stage_group"]])

# Clip Time to remove outlier long-survivors (keeps model sensible)
df["time_clipped"] = df["Time"].clip(upper=df["Time"].quantile(0.95))

FEATURE_COLS  = ["gender_enc", "stage_enc", "time_clipped"]
TARGET_COL    = "Event"      # 1 = died, 0 = survived
PROTECTED     = ["gender", "race"]

print(f"\nClass distribution — Event=1 (died): {df[TARGET_COL].sum()}, Event=0 (alive): {(df[TARGET_COL]==0).sum()}")
print(f"Race breakdown: {df['race'].value_counts().to_dict()}")
print(f"Sex breakdown:  {df['gender'].value_counts().to_dict()}")


# ── 3. Train LogisticRegression ───────────────────────────────────────────────
X = df[FEATURE_COLS].values
y = df[TARGET_COL].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

clf = LogisticRegression(max_iter=2000, random_state=42, class_weight="balanced")
clf.fit(X_train, y_train)

y_prob = clf.predict_proba(X_test)[:, 1]
print(f"\nModel trained.")
print(f"Test AUC: {roc_auc_score(y_test, y_prob):.3f}")
print(classification_report(y_test, clf.predict(X_test), target_names=["Alive", "Died"]))


# ── 4. Define @monitor-wrapped predict ───────────────────────────────────────
# X passed to this function must contain FEATURE_COLS + PROTECTED as columns.

@monitor(
    model_name="cancer_survival_v1",
    protected_attrs=PROTECTED,
)
def predict(X: pd.DataFrame) -> list[float]:
    return clf.predict_proba(X[FEATURE_COLS].values)[:, 1].tolist()


# ── 5. Log predictions (25 passes to seed enough events for the worker) ───────
# 30 rows × 25 passes = 750 prediction events in Supabase.
# The worker needs at least ~30 events per subgroup for reliable AUC estimates.

X_monitor = df[FEATURE_COLS + PROTECTED].copy()
y_all     = df[TARGET_COL].tolist()
ids_all   = df["PatientID"].tolist()

N_PASSES = 25
print(f"\nLogging predictions to Supabase ({N_PASSES} passes × {len(df)} rows = {N_PASSES * len(df)} events)...")

for i in range(N_PASSES):
    predict(X_monitor, y_true=y_all, patient_ids=ids_all)
    if (i + 1) % 5 == 0:
        print(f"  {i + 1}/{N_PASSES} passes complete")

print("All prediction events logged to Supabase.")


# ── 6. Run the 4-dimension fairness worker ────────────────────────────────────
print("\nRunning fairness worker...")

cfg = WorkerConfig(
    model_name="cancer_survival_v1",
    protected_attrs=PROTECTED,
    window_n=5000,
    min_group_n_auc=20,         # lowered from 30 — dataset is small
    inter_min_group_n=10,        # lowered — dataset is small
    clinical_context={
        "useCase":          "Cancer Survival Prediction",
        "outcome":          "predicted not to survive",
        "population":       "Oncology Patients",
        "department":       "Oncology",
        "patientsPerMonth": 150,
        "complianceNote":   "CMS AI Transparency & Bias Rule (2025)",
    },
)

run_once(cfg)

print("\nDone! Open http://localhost:3000 and select 'cancer_survival_v1' from the model selector.")
