from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import kagglehub
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OrdinalEncoder

from SDK.monitor.decorator import monitor
from SDK.workers.config import WorkerConfig



@dataclass
class RuntimeState:
    predict_fn: Callable[..., list[float]]
    x_monitor: pd.DataFrame
    y_all: list[int]
    ids_all: list[int]
    worker_cfg: WorkerConfig
    batch_cursor: int = 0


def startup_runtime(log: Callable[[str], None], model_name: str = "cancer_survival_v1") -> RuntimeState:
    log("FairnessOps scheduler starting up...")
    log("Loading clinical dataset from Kaggle cache...")

    dataset_path = kagglehub.dataset_download("imtkaggleteam/clinical-dataset")
    df = pd.read_csv(f"{dataset_path}/Clinical Data_Discovery_Cohort.csv")

    try:
        df_val = pd.read_excel(f"{dataset_path}/Clinical_Data_Validation_Cohort.xlsx")
        if set(df.columns) == set(df_val.columns):
            df = pd.concat([df, df_val], ignore_index=True)
    except Exception:
        pass

    df["race"] = df["race"].map({"W": "White", "B": "Black", "A": "Asian", "O": "Other"}).fillna("Other")
    df["gender"] = df["sex"].map({"M": "Male", "F": "Female"}).fillna("Unknown")

    def simplify_stage(raw: str) -> str:
        s = str(raw).strip().upper()
        return "Advanced" if any(x in s for x in ["N2", "N1", "N1MX", "N2MX"]) else "Early"

    df["stage_group"] = df["Stage"].apply(simplify_stage)
    df["time_clipped"] = df["Time"].clip(upper=df["Time"].quantile(0.95))

    enc_gender = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    enc_stage = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    df["gender_enc"] = enc_gender.fit_transform(df[["gender"]])
    df["stage_enc"] = enc_stage.fit_transform(df[["stage_group"]])

    feature_cols = ["gender_enc", "stage_enc", "time_clipped"]
    protected = ["gender", "race"]

    x = df[feature_cols].values
    y = df["Event"].values
    x_train, _, y_train, _ = train_test_split(x, y, test_size=0.25, random_state=42, stratify=y)
    clf = LogisticRegression(max_iter=2000, random_state=42, class_weight="balanced")
    clf.fit(x_train, y_train)
    log(f"Model trained on {len(x_train)} samples.")

    @monitor(model_name=model_name, protected_attrs=protected)
    def predict(x_df: pd.DataFrame) -> list[float]:
        return clf.predict_proba(x_df[feature_cols].values)[:, 1].tolist()

    worker_cfg = WorkerConfig(
        model_name=model_name,
        protected_attrs=protected,
        window_n=5000,
        min_group_n_auc=20,
        inter_min_group_n=10,
        clinical_context={
            "useCase": "Cancer Survival Prediction",
            "outcome": "predicted not to survive",
            "population": "Oncology Patients",
            "department": "Oncology",
            "patientsPerMonth": 150,
            "complianceNote": "CMS AI Transparency & Bias Rule (2025)",
        },
    )

    return RuntimeState(
        predict_fn=predict,
        x_monitor=df[feature_cols + protected].copy().reset_index(drop=True),
        y_all=df["Event"].tolist(),
        ids_all=df["PatientID"].tolist(),
        worker_cfg=worker_cfg,
    )

