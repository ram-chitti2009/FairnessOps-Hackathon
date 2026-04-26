from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

DATASET_MODE = os.getenv("DATASET_MODE", "cancer").strip().lower()
if DATASET_MODE not in {"cancer", "eicu", "synthetic"}:
    DATASET_MODE = "cancer"
CANCER_MODEL_NAME = os.getenv("CANCER_MODEL_NAME", "cancer_survival_v1").strip()
EICU_MODEL_NAME = os.getenv("EICU_MODEL_NAME", "eicu_logreg_v1").strip()
EICU_DATA_PATH = os.getenv("EICU_DATA_PATH", "").strip()
SYNTH_MODEL_NAME = os.getenv("SYNTH_MODEL_NAME", "synthetic_monitor_v1").strip()
SYNTH_ROWS = int(os.getenv("SYNTH_ROWS", "5000"))
SYNTH_SEED = int(os.getenv("SYNTH_SEED", "42"))
if DATASET_MODE == "eicu":
    MODEL_NAME = EICU_MODEL_NAME
elif DATASET_MODE == "synthetic":
    MODEL_NAME = SYNTH_MODEL_NAME
else:
    MODEL_NAME = CANCER_MODEL_NAME
PREDICT_INTERVAL = int(os.getenv("PREDICT_INTERVAL_SECS", "30"))
WORKER_INTERVAL = int(os.getenv("WORKER_INTERVAL_SECS", "120"))
BATCH_SIZE = int(os.getenv("PREDICT_BATCH_SIZE", "250"))
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "").strip()
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:3000")

# Console labels are ASCII-safe for Windows terminals.
SEV_CONSOLE = {"RED": "[CRIT]", "YELLOW": "[WARN]", "GREEN": "[OK  ]"}
SEV_EMOJI = {"RED": "🚨", "YELLOW": "⚠️", "GREEN": "✅"}

