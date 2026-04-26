from __future__ import annotations

import time
from datetime import datetime

import schedule

from SDK.workers.run_worker import run_once

from scheduler_alerting import AlertNotifier
from scheduler_config import BATCH_SIZE, DASHBOARD_URL, MODEL_NAME, PREDICT_INTERVAL, WORKER_INTERVAL
from scheduler_runtime import RuntimeState


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{ts()}] {msg}", flush=True)


def simulate_predictions(state: RuntimeState) -> None:
    n = len(state.x_monitor)
    start = state.batch_cursor % n
    end = min(start + BATCH_SIZE, n)
    batch_x = state.x_monitor.iloc[start:end]
    batch_y = state.y_all[start:end]
    batch_ids = state.ids_all[start:end]
    state.predict_fn(batch_x, y_true=batch_y, patient_ids=batch_ids)
    state.batch_cursor += BATCH_SIZE
    log(f"Predicted batch [{start}:{end}] ({len(batch_x)} patients) -> Supabase")


def run_worker_job(state: RuntimeState, notifier: AlertNotifier) -> None:
    log("Running fairness worker...")
    try:
        run_once(state.worker_cfg)
        log("Worker complete. Checking for alerts...")
        notifier.check_and_notify(log)
    except Exception as exc:
        log(f"Worker error: {exc}")


def run_scheduler_loop(state: RuntimeState, notifier: AlertNotifier) -> None:
    simulate_predictions(state)
    run_worker_job(state, notifier)

    schedule.every(PREDICT_INTERVAL).seconds.do(lambda: simulate_predictions(state))
    schedule.every(WORKER_INTERVAL).seconds.do(lambda: run_worker_job(state, notifier))

    log(f"Ready. Predictions every {PREDICT_INTERVAL}s | Worker every {WORKER_INTERVAL}s")
    log("Scheduler running. Press Ctrl+C to stop.")
    log(f"Dashboard: {DASHBOARD_URL}?model={MODEL_NAME}")
    print("=" * 60, flush=True)

    try:
        while True:
            schedule.run_pending()
            time.sleep(5)
    except KeyboardInterrupt:
        log("Scheduler stopped.")

