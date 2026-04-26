from __future__ import annotations

"""
FairnessOps Demo Scheduler
==========================

Thin entrypoint that composes modular scheduler parts:
  - scheduler_runtime.py  : data/model bootstrap + monitored predict function
  - scheduler_alerting.py : query latest alerts + optional Slack notifications
  - scheduler_core.py     : scheduling loop and recurring jobs
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scheduler_alerting import AlertNotifier  # noqa: E402
from scheduler_core import log, run_scheduler_loop  # noqa: E402
from scheduler_config import DATASET_MODE  # noqa: E402

if DATASET_MODE == "eicu":
    from scheduler_runtime_eicu import startup_runtime  # noqa: E402
elif DATASET_MODE == "synthetic":
    from scheduler_runtime_synthetic import startup_runtime  # noqa: E402
elif DATASET_MODE == "cancer":
    from scheduler_runtime import startup_runtime  # noqa: E402
else:
    raise ValueError(f"Unsupported DATASET_MODE='{DATASET_MODE}'. Use 'cancer', 'eicu', or 'synthetic'.")


def main() -> None:
    log(f"Dataset mode: {DATASET_MODE}")
    state = startup_runtime(log)
    notifier = AlertNotifier()
    run_scheduler_loop(state, notifier)


if __name__ == "__main__":
    main()
