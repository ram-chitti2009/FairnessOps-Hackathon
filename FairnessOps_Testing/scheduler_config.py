from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

# ── Per-mode model name defaults ─────────────────────────────────────────────
CANCER_MODEL_NAME = os.getenv("CANCER_MODEL_NAME", "cancer_survival_v1").strip()
EICU_MODEL_NAME   = os.getenv("EICU_MODEL_NAME",   "eicu_logreg_v1").strip()
SYNTH_MODEL_NAME  = os.getenv("SYNTH_MODEL_NAME",  "synthetic_monitor_v1").strip()

_MODE_TO_MODEL = {
    "cancer":    CANCER_MODEL_NAME,
    "eicu":      EICU_MODEL_NAME,
    "synthetic": SYNTH_MODEL_NAME,
}

# ── Shared defaults ───────────────────────────────────────────────────────────
PREDICT_INTERVAL = int(os.getenv("PREDICT_INTERVAL_SECS",  "30"))
WORKER_INTERVAL  = int(os.getenv("WORKER_INTERVAL_SECS",  "120"))
BATCH_SIZE       = int(os.getenv("PREDICT_BATCH_SIZE",     "250"))
SLACK_WEBHOOK    = os.getenv("SLACK_WEBHOOK_URL", "").strip()
DASHBOARD_URL    = os.getenv("DASHBOARD_URL", "http://localhost:3000")
EICU_DATA_PATH   = os.getenv("EICU_DATA_PATH", "").strip()
SYNTH_ROWS       = int(os.getenv("SYNTH_ROWS", "5000"))
SYNTH_SEED       = int(os.getenv("SYNTH_SEED", "42"))

# ── Multi-model config ────────────────────────────────────────────────────────
# ENABLED_MODELS is a comma-separated list of modes: e.g. "synthetic,cancer"
# Falls back to DATASET_MODE (single-model legacy behaviour) if not set.
_enabled_raw = os.getenv("ENABLED_MODELS", "").strip()
if _enabled_raw:
    _enabled_modes = [m.strip().lower() for m in _enabled_raw.split(",") if m.strip()]
else:
    # Legacy single-model fallback
    _legacy = os.getenv("DATASET_MODE", "synthetic").strip().lower()
    _enabled_modes = [_legacy if _legacy in _MODE_TO_MODEL else "synthetic"]

MODELS_CONFIG: list[dict[str, Any]] = []
for _mode in _enabled_modes:
    if _mode not in _MODE_TO_MODEL:
        print(f"[scheduler_config] Unknown mode '{_mode}' in ENABLED_MODELS — skipping.")
        continue
    MODELS_CONFIG.append({
        "mode":             _mode,
        "model_name":       _MODE_TO_MODEL[_mode],
        "predict_interval": PREDICT_INTERVAL,
        "worker_interval":  WORKER_INTERVAL,
        "batch_size":       BATCH_SIZE,
    })

if not MODELS_CONFIG:
    raise ValueError("No valid models configured. Check ENABLED_MODELS in .env.")

# ── Legacy single-model exports (backwards compat) ───────────────────────────
# Still exported so any external script that imports MODEL_NAME still works.
DATASET_MODE = _enabled_modes[0]
MODEL_NAME   = MODELS_CONFIG[0]["model_name"]

# Console labels are ASCII-safe for Windows terminals.
SEV_CONSOLE = {"RED": "[CRIT]", "YELLOW": "[WARN]", "GREEN": "[OK  ]"}
SEV_EMOJI   = {"RED": "🚨",     "YELLOW": "⚠️",      "GREEN": "✅"}
