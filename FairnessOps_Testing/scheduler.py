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

from scheduler_alerting import AlertNotifier
from scheduler_core import log, run_scheduler_loop
from scheduler_runtime import startup_runtime


def main() -> None:
    state = startup_runtime(log)
    notifier = AlertNotifier()
    run_scheduler_loop(state, notifier)


if __name__ == "__main__":
    main()
