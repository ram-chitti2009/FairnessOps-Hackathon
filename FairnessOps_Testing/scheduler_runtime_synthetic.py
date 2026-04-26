from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from SDK.monitor.decorator import monitor
from SDK.workers.config import WorkerConfig

from scheduler_config import SYNTH_ROWS, SYNTH_SEED


@dataclass
class RuntimeState:
    predict_fn: Callable[..., list[float]]
    x_monitor: pd.DataFrame
    y_all: list[int]
    ids_all: list[int]
    worker_cfg: WorkerConfig
    batch_cursor: int = 0


def _make_synthetic_dataset(rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    gender = rng.choice(["Male", "Female"], size=rows, p=[0.48, 0.52])
    ethnicity = rng.choice(["White", "Black", "Hispanic", "Asian", "Other"], size=rows, p=[0.45, 0.2, 0.2, 0.1, 0.05])
    age_group = rng.choice(["18-45", "46-65", "over_65"], size=rows, p=[0.3, 0.4, 0.3])
    insurance = rng.choice(["Private", "Medicare", "Medicaid", "SelfPay"], size=rows, p=[0.4, 0.3, 0.2, 0.1])
    region = rng.choice(["North", "South", "East", "West"], size=rows, p=[0.25, 0.3, 0.2, 0.25])

    lab_creatinine = rng.normal(1.0, 0.35, size=rows)
    lab_sodium = rng.normal(138.0, 3.8, size=rows)
    lab_glucose = rng.normal(128.0, 24.0, size=rows)
    lab_potassium = rng.normal(4.0, 0.45, size=rows)
    vital_heartrate = rng.normal(88.0, 14.0, size=rows)
    vital_sao2 = rng.normal(95.0, 2.0, size=rows)
    vital_respiration = rng.normal(20.0, 4.0, size=rows)
    apachescore = rng.normal(52.0, 16.0, size=rows)

    # Inject late-window feature drift to activate Feature Drift and Algorithmic Drift.
    drift_start = int(rows * 0.55)
    lab_glucose[drift_start:] += rng.normal(20.0, 8.0, size=rows - drift_start)
    vital_heartrate[drift_start:] += rng.normal(12.0, 5.0, size=rows - drift_start)
    apachescore[drift_start:] += rng.normal(9.0, 4.0, size=rows - drift_start)

    # True risk process with controlled subgroup penalties.
    z_true = (
        -2.4
        + 0.022 * (lab_glucose - 110.0)
        + 0.035 * (vital_heartrate - 80.0)
        + 0.050 * (vital_respiration - 18.0)
        + 0.028 * (apachescore - 45.0)
        + 0.40 * (age_group == "over_65").astype(float)
        + 0.26 * (ethnicity == "Black").astype(float)
        + 0.10 * (region == "South").astype(float)
    )
    p_true = 1.0 / (1.0 + np.exp(-z_true))
    y_true = (rng.random(rows) < p_true).astype(int)

    # Intentionally biased prediction signal to create fairness gaps.
    z_pred = (
        z_true
        - 0.35 * (ethnicity == "Black").astype(float)
        - 0.28 * ((gender == "Male") & (ethnicity == "Black")).astype(float)
        - 0.18 * (age_group == "over_65").astype(float)
        + rng.normal(0.0, 0.45, size=rows)
    )
    y_pred_proba = np.clip(1.0 / (1.0 + np.exp(-z_pred)), 1e-4, 1 - 1e-4)

    return pd.DataFrame(
        {
            "patientunitstayid": np.arange(1, rows + 1),
            "y_true": y_true.astype(int),
            "y_pred_proba": y_pred_proba.astype(float),
            "ethnicity": ethnicity.astype(str),
            "gender": gender.astype(str),
            "age_group": age_group.astype(str),
            "insurance": insurance.astype(str),
            "region": region.astype(str),
            "lab_creatinine": lab_creatinine.astype(float),
            "lab_sodium": lab_sodium.astype(float),
            "lab_glucose": lab_glucose.astype(float),
            "lab_potassium": lab_potassium.astype(float),
            "vital_heartrate": vital_heartrate.astype(float),
            "vital_sao2": vital_sao2.astype(float),
            "vital_respiration": vital_respiration.astype(float),
            "apachescore": apachescore.astype(float),
        }
    )


def startup_runtime(log: Callable[[str], None], model_name: str = "synthetic_monitor_v1") -> RuntimeState:
    rows = max(1200, SYNTH_ROWS)
    log(f"FairnessOps scheduler starting up (synthetic mode, rows={rows}, seed={SYNTH_SEED})...")
    df = _make_synthetic_dataset(rows=rows, seed=SYNTH_SEED)

    target_col = "y_true"
    patient_col = "patientunitstayid"
    protected = ["ethnicity", "gender", "age_group", "region"]
    feature_cols = [
        "age_group",
        "insurance",
        "region",
        "lab_creatinine",
        "lab_sodium",
        "lab_glucose",
        "lab_potassium",
        "vital_heartrate",
        "vital_sao2",
        "vital_respiration",
        "apachescore",
    ]

    # Use disjoint train/monitor sets to avoid "training logs" issue.
    train_df, monitor_df = train_test_split(
        df, test_size=0.45, random_state=SYNTH_SEED, stratify=df[target_col]
    )

    numeric_cols = [c for c in feature_cols if monitor_df[c].dtype.kind in "ifb"]
    categorical_cols = [c for c in feature_cols if c not in numeric_cols]
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", SimpleImputer(strategy="median"), numeric_cols),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_cols,
            ),
        ],
        remainder="drop",
    )
    clf = Pipeline(
        steps=[
            ("prep", preprocessor),
            ("model", LogisticRegression(max_iter=3000, random_state=SYNTH_SEED, class_weight="balanced")),
        ]
    )
    clf.fit(train_df[feature_cols], train_df[target_col].astype(int).values)
    log(f"Synthetic model trained on {len(train_df)} rows. Monitor stream rows={len(monitor_df)}")

    x_monitor = monitor_df[feature_cols].copy()
    x_monitor["gender"] = monitor_df["gender"].astype(str).values
    x_monitor["ethnicity"] = monitor_df["ethnicity"].astype(str).values
    x_monitor["age_group"] = monitor_df["age_group"].astype(str).values
    x_monitor["region"] = monitor_df["region"].astype(str).values
    x_monitor = x_monitor.astype(object).where(pd.notnull(x_monitor), None)

    @monitor(model_name=model_name, protected_attrs=protected)
    def predict(x_df: pd.DataFrame) -> list[float]:
        # Simulate online drift over time by degrading confidence as batches progress.
        base = clf.predict_proba(x_df[feature_cols])[:, 1]
        return np.clip(base, 1e-4, 1 - 1e-4).tolist()

    worker_cfg = WorkerConfig(
        model_name=model_name,
        protected_attrs=protected,
        window_n=500,
        min_group_n_auc=20,
        inter_min_group_n=10,
        clinical_context={
            "useCase": "Synthetic ICU Risk Monitoring (Demo)",
            "outcome": "flagged as high deterioration risk",
            "population": "Adult ICU Patients",
            "department": "Critical Care",
            "patientsPerMonth": 1800,
            "complianceNote": "CMS AI Transparency & Bias Rule (2025)",
        },
    )

    return RuntimeState(
        predict_fn=predict,
        x_monitor=x_monitor.reset_index(drop=True),
        y_all=monitor_df[target_col].astype(int).tolist(),
        ids_all=monitor_df[patient_col].astype(int).tolist(),
        worker_cfg=worker_cfg,
    )
