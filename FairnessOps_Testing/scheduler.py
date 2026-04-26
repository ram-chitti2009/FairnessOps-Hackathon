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
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scheduler_alerting import AlertNotifier  # noqa: E402
from scheduler_core import log, run_scheduler_loop  # noqa: E402
from scheduler_config import MODELS_CONFIG  # noqa: E402


def _import_startup(mode: str):
    if mode == "eicu":
        from scheduler_runtime_eicu import startup_runtime
    elif mode == "synthetic":
        from scheduler_runtime_synthetic import startup_runtime
    elif mode == "cancer":
        from scheduler_runtime import startup_runtime
    else:
        raise ValueError(f"Unsupported mode '{mode}'. Use 'cancer', 'eicu', or 'synthetic'.")
    return startup_runtime


def main() -> None:
    threads: list[threading.Thread] = []

    for model_cfg in MODELS_CONFIG:
        mode = model_cfg["mode"]
        model_name = model_cfg["model_name"]
        log(f"[{model_name}] Bootstrapping runtime (mode={mode})...")

        startup_runtime = _import_startup(mode)
        state = startup_runtime(log)
        notifier = AlertNotifier(model_name=model_name)

        t = threading.Thread(
            target=run_scheduler_loop,
            args=(state, notifier, model_cfg),
            daemon=True,
            name=f"scheduler-{model_name}",
        )
        threads.append(t)

    for t in threads:
        t.start()

    log(f"All {len(threads)} model scheduler(s) started. Press Ctrl+C to stop.")

    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
