from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from SDK.monitor.decorator import monitor
from SDK.workers.config import WorkerConfig

from scheduler_config import EICU_DATA_PATH


@dataclass
class RuntimeState:
    predict_fn: Callable[..., list[float]]
    x_monitor: pd.DataFrame
    y_all: list[int]
    ids_all: list[int]
    worker_cfg: WorkerConfig
    batch_cursor: int = 0


def _pick_first(df: pd.DataFrame, candidates: list[str]) -> str:
    cols = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in cols:
            return cols[c.lower()]
    raise ValueError(f"None of these columns found: {candidates}")


def startup_runtime(log: Callable[[str], None], model_name: str = "eicu_logreg_v1") -> RuntimeState:
    log("FairnessOps scheduler starting up (eICU mode)...")
    if not EICU_DATA_PATH:
        raise ValueError("EICU_DATA_PATH is empty. Set it in .env to a local eICU CSV file.")

    csv_path = Path(EICU_DATA_PATH)
    if not csv_path.exists():
        raise FileNotFoundError(f"EICU_DATA_PATH does not exist: {csv_path}")

    log(f"Loading eICU dataset from: {csv_path}")
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("Loaded eICU dataset is empty.")

    # Flexible column mapping for common eICU exports.
    target_col = _pick_first(
        df, ["y_true", "hospital_expire_flag", "mortality", "death", "label", "target", "y", "outcome"]
    )
    gender_col = _pick_first(df, ["gender", "sex"])
    race_col = _pick_first(df, ["ethnicity", "race", "ethnic_group"])
    patient_col = _pick_first(df, ["patientunitstayid", "patient_id", "stay_id", "subject_id", "id"])
    log(
        "Detected columns -> "
        f"target='{target_col}', gender='{gender_col}', race='{race_col}', patient_id='{patient_col}'"
    )

    # Normalize protected attributes for dashboard and worker.
    df["gender"] = df[gender_col].astype(str).str.strip().replace({"M": "Male", "F": "Female"})
    df["race"] = df[race_col].astype(str).str.strip().replace({"": "Unknown"}).fillna("Unknown")
    df[target_col] = pd.to_numeric(df[target_col], errors="coerce").fillna(0).astype(int).clip(0, 1)

    # Use all non-protected, non-id, non-target columns as model features.
    drop_cols = {target_col, patient_col, gender_col, race_col, "gender", "race"}
    feature_cols = [c for c in df.columns if c not in drop_cols]
    if not feature_cols:
        raise ValueError("No feature columns available after dropping id/target/protected columns.")
    log(
        f"Feature selection -> total={len(feature_cols)}, "
        f"numeric={len(df[feature_cols].select_dtypes(include=['number', 'bool']).columns)}, "
        f"categorical={len(feature_cols) - len(df[feature_cols].select_dtypes(include=['number', 'bool']).columns)}"
    )

    x_raw = df[feature_cols].copy()
    # Monitor payload must be JSON-safe: replace inf with NaN, then map NaN to None.
    x_raw = x_raw.replace([float("inf"), float("-inf")], pd.NA)
    y = df[target_col].values
    classes = sorted(set(int(v) for v in y))
    if len(classes) < 2:
        raise ValueError(
            f"Target column '{target_col}' has only one class ({classes}). "
            "Need both 0 and 1 for LogisticRegression."
        )
    log(f"Target distribution -> positives={int((y == 1).sum())}, negatives={int((y == 0).sum())}")

    numeric_cols = x_raw.select_dtypes(include=["number", "bool"]).columns.tolist()
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
            ("model", LogisticRegression(max_iter=2000, random_state=42, class_weight="balanced")),
        ]
    )

    x_train, _, y_train, _ = train_test_split(
        x_raw, y, test_size=0.25, random_state=42, stratify=y if len(set(y)) > 1 else None
    )
    clf.fit(x_train, y_train)
    log(f"eICU model trained on {len(x_train)} rows. Model name: {model_name}")

    protected = ["gender", "race"]
    x_monitor = x_raw.copy()
    # Convert all missing/NaN-like values to Python None so JSON encoding is safe.
    x_monitor = x_monitor.astype(object).where(pd.notnull(x_monitor), None)
    x_monitor["gender"] = df["gender"]
    x_monitor["race"] = df["race"]

    @monitor(model_name=model_name, protected_attrs=protected)
    def predict(x_df: pd.DataFrame) -> list[float]:
        return clf.predict_proba(x_df[feature_cols])[:, 1].tolist()

    worker_cfg = WorkerConfig(
        model_name=model_name,
        protected_attrs=protected,
        window_n=500,
        min_group_n_auc=20,
        inter_min_group_n=10,
        clinical_context={
            "useCase": "ICU Mortality Risk Screening",
            "outcome": "flagged as high mortality risk",
            "population": "Adult ICU Patients",
            "department": "Critical Care",
            "patientsPerMonth": 1200,
            "complianceNote": "CMS AI Transparency & Bias Rule (2025)",
        },
    )

    return RuntimeState(
        predict_fn=predict,
        x_monitor=x_monitor.reset_index(drop=True),
        y_all=df[target_col].astype(int).tolist(),
        ids_all=df[patient_col].astype(str).tolist(),
        worker_cfg=worker_cfg,
    )
