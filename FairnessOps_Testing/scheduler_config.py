from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

MODEL_NAME = "cancer_survival_v1"
PREDICT_INTERVAL = int(os.getenv("PREDICT_INTERVAL_SECS", "30"))
WORKER_INTERVAL = int(os.getenv("WORKER_INTERVAL_SECS", "120"))
BATCH_SIZE = int(os.getenv("PREDICT_BATCH_SIZE", "10"))
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "").strip()
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:3000")

# Console labels are ASCII-safe for Windows terminals.
SEV_CONSOLE = {"RED": "[CRIT]", "YELLOW": "[WARN]", "GREEN": "[OK  ]"}
SEV_EMOJI = {"RED": "🚨", "YELLOW": "⚠️", "GREEN": "✅"}

