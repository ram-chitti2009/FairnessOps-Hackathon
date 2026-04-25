# =========================================================
# FairnessOps - Canonical Dataset EDA (Colab-ready)
# =========================================================
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

pd.set_option("display.max_columns", 200)
pd.set_option("display.width", 160)

# ----------------------------
# 1) Locate canonical dataset
# ----------------------------

# Option A: if already in /content
# DATA_PATH = Path("/content/canonical_dataset.csv")

# Option B: if in Google Drive
# from google.colab import drive
# drive.mount('/content/drive')
# DATA_PATH = Path("/content/drive/MyDrive/Fairness Ops/runs/canonical_dataset.csv")

# Auto-candidates (edit if needed)
candidates = [
    Path("/content/canonical_dataset.csv"),
    Path("/content/runs/canonical_dataset.csv"),
    Path("/content/drive/MyDrive/Fairness Ops/runs/canonical_dataset.csv"),
    Path("/content/drive/MyDrive/canonical_dataset.csv"),
]

DATA_PATH = next((p for p in candidates if p.exists()), None)
if DATA_PATH is None:
    raise FileNotFoundError(
        "canonical_dataset.csv not found. Update DATA_PATH to your actual file location."
    )

print("Using:", DATA_PATH)

# ----------------------------
# 2) Load dataset
# ----------------------------

df = pd.read_csv(DATA_PATH)
print("Shape:", df.shape)
display(df.head(5))

# ----------------------------
# 3) Basic schema + missingness
# ----------------------------

print("\nDtypes:")
display(df.dtypes.to_frame("dtype").T)
missing_pct = (df.isna().mean() * 100).round(2).sort_values(ascending=False)
print("\nMissingness (%):")
display(missing_pct.to_frame("missing_pct"))

# ----------------------------
# 4) Label distribution
# ----------------------------

if "y_true" not in df.columns:
    raise ValueError("Expected column 'y_true' not found.")

label_counts = df["y_true"].value_counts(dropna=False).sort_index()
label_pct = (
    (df["y_true"].value_counts(normalize=True, dropna=False) * 100)
    .sort_index()
    .round(2)
)

print("\nLabel counts:")
display(label_counts.to_frame("count"))
print("Label percent:")
display(label_pct.to_frame("pct"))
print(f"Mortality prevalence (y_true=1): {df['y_true'].mean():.3%}")

# ----------------------------
# 5) Protected attribute profiling
# ----------------------------

protected_cols = [
    c
    for c in ["ethnicity", "gender", "age_group", "region", "insurance", "language"]
    if c in df.columns
]

for c in protected_cols:
    print(f"\n=== {c} distribution ===")
    vc = df[c].fillna("Unknown").value_counts(dropna=False)
    display(vc.to_frame("count").head(20))

# ----------------------------
# 6) Numeric feature summary
# ----------------------------

id_and_label = {"patientunitstayid", "hospitalid", "y_true"}
numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c not in id_and_label]

print("\nNumeric modeling columns:")
print(numeric_cols)

if numeric_cols:
    print("\nSummary stats:")
    display(df[numeric_cols].describe().T)

# ----------------------------
# 7) Correlation quick look
# ----------------------------

if len(numeric_cols) >= 2:
    plt.figure(figsize=(10, 6))
    corr = df[numeric_cols + ["y_true"]].corr(numeric_only=True)
    sns.heatmap(corr, cmap="coolwarm", center=0, annot=False)
    plt.title("Correlation Heatmap (numeric + y_true)")
    plt.tight_layout()
    plt.show()

# ----------------------------
# 8) Group mortality (descriptive)
# ----------------------------


def mortality_by_group(data, group_col, min_n=20):
    tmp = (
        data.assign(group=data[group_col].astype("object").fillna("Unknown"))
        .groupby("group")
        .agg(n=("y_true", "size"), mortality_rate=("y_true", "mean"))
        .sort_values("n", ascending=False)
    )
    tmp["mortality_rate"] = tmp["mortality_rate"].round(4)
    return tmp[tmp["n"] >= min_n]


for c in [x for x in ["ethnicity", "gender", "age_group", "region"] if x in df.columns]:
    print(f"\n=== Mortality by {c} (descriptive) ===")
    display(mortality_by_group(df, c, min_n=20).head(20))