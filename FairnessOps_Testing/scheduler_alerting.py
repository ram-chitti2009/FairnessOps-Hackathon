from __future__ import annotations

import json
from typing import Callable

import requests
from supabase import create_client

from SDK.monitor.supabase_client import SupabaseConfig

from scheduler_config import DASHBOARD_URL, MODEL_NAME, SEV_CONSOLE, SEV_EMOJI, SLACK_WEBHOOK


class AlertNotifier:
    def __init__(self) -> None:
        s_cfg = SupabaseConfig.from_env()
        self._supabase = create_client(s_cfg.url, s_cfg.key)
        self._schema = s_cfg.schema

    @staticmethod
    def format_signal(alert: dict) -> str:
        dim = alert.get("dimension", "")
        v = alert.get("signal_value")
        if v is None:
            return "-"
        n = float(v)
        if dim == "Demographic Fairness":
            return f"{abs(n * 100):.1f}% outcome gap"
        if dim == "Representation":
            return f"{round(n)} patients"
        if "Intersectionality" in dim:
            if n >= 1.0:
                return "Severe compound gap"
            if n >= 0.5:
                return "High compound gap"
            return "Moderate compound gap"
        if dim == "Fairness Drift":
            if n > 0.005:
                return "Gap widening"
            if n < -0.005:
                return "Gap closing"
            return "Gap stable"
        return f"{n:.3f}"

    def check_and_notify(self, log: Callable[[str], None]) -> None:
        try:
            run_res = (
                self._supabase.schema(self._schema)
                .table("audit_runs")
                .select("run_id, window_size")
                .eq("model_name", MODEL_NAME)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if not run_res.data:
                return

            run_id = run_res.data[0]["run_id"]
            window_size = run_res.data[0].get("window_size", 0)
            alert_res = (
                self._supabase.schema(self._schema)
                .table("metric_alerts")
                .select("dimension, attribute, subgroup, severity, signal_value, message")
                .eq("run_id", run_id)
                .in_("severity", ["RED", "YELLOW"])
                .order("severity")
                .execute()
            )
            alerts = list(alert_res.data or [])
            if not alerts:
                log("No RED/YELLOW alerts in this run - all clear.")
                return

            red_count = sum(1 for a in alerts if a["severity"] == "RED")
            yellow_count = sum(1 for a in alerts if a["severity"] == "YELLOW")
            log(f"Found {red_count} RED, {yellow_count} YELLOW alerts - notifying...")

            self._post_to_slack(alerts, window_size, log)
            self._print_alerts(alerts)
        except Exception as exc:
            log(f"Alert check error: {exc}")

    def _post_to_slack(self, alerts: list[dict], window_size: int, log: Callable[[str], None]) -> None:
        if not SLACK_WEBHOOK:
            return
        red_count = sum(1 for a in alerts if a["severity"] == "RED")
        yellow_count = sum(1 for a in alerts if a["severity"] == "YELLOW")
        header = (
            f"{'🚨' if red_count else '⚠️'} *FairnessOps Alert - {MODEL_NAME}*\n"
            f"*{red_count} Critical | {yellow_count} Warnings* | {window_size:,} patients scored"
        )

        lines: list[str] = []
        for a in alerts[:6]:
            emoji = SEV_EMOJI.get(a["severity"], "-")
            dim = a.get("dimension", "Unknown").replace("(2-way)", "").strip()
            attr = a.get("attribute") or ""
            sub = a.get("subgroup") or ""
            sig = self.format_signal(a)
            group = f"{attr} | {sub}" if sub else attr
            lines.append(f"{emoji} *{dim}* | {group}\n    {sig}")
        if len(alerts) > 6:
            lines.append(f"_...and {len(alerts) - 6} more_")

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": header}},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n\n".join(lines)}},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Dashboard"},
                        "url": f"{DASHBOARD_URL}?model={MODEL_NAME}",
                        "style": "danger" if red_count else "primary",
                    }
                ],
            },
        ]

        try:
            resp = requests.post(
                SLACK_WEBHOOK,
                data=json.dumps({"blocks": blocks}),
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            if resp.status_code == 200:
                log("Slack notification sent.")
            else:
                log(f"Slack returned {resp.status_code}: {resp.text}")
        except Exception as exc:
            log(f"Slack post failed: {exc}")

    def _print_alerts(self, alerts: list[dict]) -> None:
        print("", flush=True)
        for a in alerts:
            label = SEV_CONSOLE.get(a["severity"], "[ ?? ]")
            dim = a.get("dimension", "")
            attr = a.get("attribute", "")
            sig = self.format_signal(a)
            print(f"  {label}  {dim:30s}  {attr:12s}  {sig}", flush=True)
        print("", flush=True)

