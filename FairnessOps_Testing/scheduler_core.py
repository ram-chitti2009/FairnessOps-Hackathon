from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import schedule as schedule_lib

from SDK.workers.run_worker import run_once
from scheduler_alerting import AlertNotifier
from scheduler_config import DASHBOARD_URL


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{ts()}] {msg}", flush=True)


def simulate_predictions(state: Any, model_name: str, batch_size: int) -> None:
    n = len(state.x_monitor)
    start = state.batch_cursor % n
    end = min(start + batch_size, n)
    batch_x  = state.x_monitor.iloc[start:end]
    batch_y  = state.y_all[start:end]
    batch_ids = state.ids_all[start:end]
    state.predict_fn(batch_x, y_true=batch_y, patient_ids=batch_ids)
    state.batch_cursor += batch_size
    log(f"[{model_name}] Predicted batch [{start}:{end}] ({len(batch_x)} patients) -> Supabase")


def run_worker_job(state: Any, notifier: AlertNotifier, model_name: str) -> None:
    log(f"[{model_name}] Running fairness worker...")
    try:
        run_once(state.worker_cfg)
        log(f"[{model_name}] Worker complete. Checking for alerts...")
        notifier.check_and_notify(log)
    except Exception as exc:
        log(f"[{model_name}] Worker error: {exc}")


def run_scheduler_loop(state: Any, notifier: AlertNotifier, model_cfg: dict) -> None:
    """Run the full predict + worker loop for one model. Designed to run in a thread."""
    model_name       = model_cfg["model_name"]
    predict_interval = model_cfg["predict_interval"]
    worker_interval  = model_cfg["worker_interval"]
    batch_size       = model_cfg["batch_size"]

    # Run immediately on startup
    simulate_predictions(state, model_name, batch_size)
    run_worker_job(state, notifier, model_name)

    # Each model gets its own Scheduler instance so intervals are fully independent
    sched = schedule_lib.Scheduler()
    sched.every(predict_interval).seconds.do(
        lambda: simulate_predictions(state, model_name, batch_size)
    )
    sched.every(worker_interval).seconds.do(
        lambda: run_worker_job(state, notifier, model_name)
    )

    log(f"[{model_name}] Ready. Predictions every {predict_interval}s | Worker every {worker_interval}s")
    log(f"[{model_name}] Dashboard: {DASHBOARD_URL}?model={model_name}")

    while True:
        sched.run_pending()
        time.sleep(5)
