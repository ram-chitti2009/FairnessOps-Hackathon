from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import altair as alt
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv  # type: ignore

# Always reload .env so fresh keys are picked up even mid-session
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────
_SEV_RANK = {"RED": 4, "YELLOW": 3, "ORANGE": 2, "GREEN": 1, "INSUFFICIENT_DATA": 0}
_SEV_HEX = {
    "RED": "#ef4444",
    "YELLOW": "#f59e0b",
    "ORANGE": "#f97316",
    "GREEN": "#22c55e",
    "INSUFFICIENT_DATA": "#475569",
}
_DIM_ICON = {
    "Demographic Fairness": "👥",
    "Representation": "📊",
    "Intersectionality (2-way)": "🔀",
    "Fairness Drift": "📈",
}


# ──────────────────────────────────────────────────────────────
# Theme injection
# ──────────────────────────────────────────────────────────────
def _inject_css() -> None:
    st.markdown(
        """
        <style>
        /* ── Global ── */
        [data-testid="stAppViewContainer"] { background: #0b0f1a; }
        [data-testid="stSidebar"] { background: #0f1629; border-right: 1px solid #1e2d4a; }
        [data-testid="stSidebar"] * { color: #94a3b8 !important; }
        h1,h2,h3,h4,h5,h6 { color: #f1f5f9 !important; }
        p, label, span, div { color: #cbd5e1; }
        .stTabs [data-baseweb="tab-list"] { background: #111827; border-radius: 12px; padding: 4px; gap: 4px; }
        .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 20px; color: #64748b !important; font-weight: 600; }
        .stTabs [aria-selected="true"] { background: #1d4ed8 !important; color: #fff !important; }
        [data-testid="stMetricValue"] { color: #f1f5f9 !important; }
        div[data-testid="stDataFrame"] { border: 1px solid #1e2d4a; border-radius: 10px; }

        /* ── Cards ── */
        .fo-hero { background: linear-gradient(135deg, #1e3a5f 0%, #0f2040 100%);
            border: 1px solid #2563eb44; border-radius: 20px; padding: 28px 32px; margin-bottom: 24px; }
        .fo-score { font-size: 4.5rem; font-weight: 900; line-height: 1; }
        .fo-score-label { font-size: 0.9rem; color: #64748b; text-transform: uppercase; letter-spacing: .12em; }
        .fo-score-sub { font-size: 1.05rem; color: #94a3b8; margin-top: 6px; }

        .fo-stat { background: #111827; border: 1px solid #1e293b; border-radius: 14px;
            padding: 18px 20px; text-align: center; }
        .fo-stat-num { font-size: 2rem; font-weight: 800; color: #f1f5f9; line-height: 1.1; }
        .fo-stat-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: .1em; margin-top: 4px; }

        .fo-pill { display: inline-block; padding: 3px 10px; border-radius: 999px;
            font-size: 0.72rem; font-weight: 700; letter-spacing: .06em; }
        .fo-alert-row { background: #111827; border: 1px solid #1e293b;
            border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; }
        .fo-alert-dim { font-size: 0.78rem; color: #64748b; }
        .fo-alert-msg { font-size: 0.9rem; color: #e2e8f0; margin-top: 2px; }

        .fo-ai-box { background: linear-gradient(135deg, #1a1040 0%, #0d1f3c 100%);
            border: 1px solid #7c3aed44; border-radius: 16px; padding: 22px 26px; margin: 16px 0; }
        .fo-ai-title { font-size: 0.8rem; font-weight: 700; color: #a78bfa;
            text-transform: uppercase; letter-spacing: .1em; margin-bottom: 10px; }
        .fo-ai-text { color: #c4b5fd; font-size: 0.97rem; line-height: 1.7; }

        .fo-dim-card { background: #111827; border: 1px solid #1e293b;
            border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; }
        .fo-dim-title { font-size: 0.95rem; font-weight: 700; color: #e2e8f0; }
        .fo-dim-sub { font-size: 0.78rem; color: #64748b; margin-top: 2px; }

        /* ── Sidebar ── */
        .fo-side-label { font-size: 0.7rem; text-transform: uppercase;
            letter-spacing: .1em; color: #475569 !important; margin-bottom: 2px; }
        [data-testid="stSidebarContent"] .stButton > button {
            background: #1d4ed8; color: #fff !important; border: none;
            border-radius: 8px; width: 100%; font-weight: 700; padding: 10px; }
        [data-testid="stSidebarContent"] .stButton > button:hover { background: #2563eb; }

        /* ── Hide Streamlit chrome ── */
        #MainMenu, footer, [data-testid="stDecoration"] { display: none !important; }
        .stDeployButton { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────
# API helpers
# ──────────────────────────────────────────────────────────────
def _safe_json(resp: requests.Response) -> Tuple[Optional[dict], Optional[str]]:
    try:
        return resp.json(), None
    except Exception:
        return None, resp.text[:500]


def fetch_audit_latest(api_base: str, model_name: str) -> Tuple[Optional[dict], Optional[str]]:
    try:
        resp = requests.get(f"{api_base}/audit/latest", params={"model_name": model_name}, timeout=45)
    except Exception as exc:
        return None, f"Network error: {exc}"
    data, raw = _safe_json(resp)
    if resp.status_code != 200:
        msg = (data or {}).get("detail") if isinstance(data, dict) else raw or resp.reason
        return None, f"HTTP {resp.status_code}: {msg}"
    return data, None


def fetch_metrics_latest(
    api_base: str, model_name: str, dimension: Optional[str] = None, limit: int = 300
) -> Tuple[List[dict], Optional[str]]:
    params: Dict[str, Any] = {"model_name": model_name, "limit": limit}
    if dimension:
        params["dimension"] = dimension
    try:
        resp = requests.get(f"{api_base}/metrics/latest", params=params, timeout=45)
    except Exception as exc:
        return [], f"Network error: {exc}"
    data, raw = _safe_json(resp)
    if resp.status_code != 200:
        msg = (data or {}).get("detail") if isinstance(data, dict) else raw or resp.reason
        return [], f"HTTP {resp.status_code}: {msg}"
    return (data or {}).get("items", []) if isinstance(data, dict) else [], None


def fetch_alerts_latest(api_base: str, model_name: str, limit: int = 300) -> Tuple[List[dict], Optional[str]]:
    try:
        resp = requests.get(f"{api_base}/alerts/latest", params={"model_name": model_name, "limit": limit}, timeout=45)
    except Exception as exc:
        return [], f"Network error: {exc}"
    data, raw = _safe_json(resp)
    if resp.status_code != 200:
        msg = (data or {}).get("detail") if isinstance(data, dict) else raw or resp.reason
        return [], f"HTTP {resp.status_code}: {msg}"
    return (data or {}).get("items", []) if isinstance(data, dict) else [], None


def fetch_stream_snapshot(api_base: str, model_name: str, max_events: int = 8) -> Tuple[List[dict], str]:
    events: List[dict] = []
    try:
        with requests.get(
            f"{api_base}/stream/alerts", params={"model_name": model_name},
            stream=True, timeout=(5, 6),
        ) as resp:
            if resp.status_code != 200:
                return [], f"http_{resp.status_code}"
            current_event = None
            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = raw_line.strip()
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    try:
                        data = json.loads(line.split(":", 1)[1].strip())
                    except Exception:
                        continue
                    if current_event == "alert" and isinstance(data, dict):
                        events.append(data.get("data", data))
                    if len(events) >= max_events:
                        break
    except Exception:
        return [], "disconnected"
    return events, "live"


def to_df(rows: List[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ──────────────────────────────────────────────────────────────
# Fairness Health Score (0–100)
# ──────────────────────────────────────────────────────────────
def _health_score(alerts: List[dict]) -> Tuple[int, str, str]:
    if not alerts:
        return 100, "A", "#22c55e"
    red = sum(1 for a in alerts if str(a.get("severity", "")).upper() == "RED")
    yellow = sum(1 for a in alerts if str(a.get("severity", "")).upper() == "YELLOW")
    total = len(alerts)
    penalty = min(100, red * 8 + yellow * 3 + max(0, (total - 10) // 5))
    score = max(0, 100 - penalty)
    if score >= 85:
        return score, "A", "#22c55e"
    if score >= 70:
        return score, "B", "#86efac"
    if score >= 50:
        return score, "C", "#f59e0b"
    if score >= 30:
        return score, "D", "#f97316"
    return score, "F", "#ef4444"


# ──────────────────────────────────────────────────────────────
# LLM explanation
# ──────────────────────────────────────────────────────────────
def llm_explain(audit: dict, alerts: List[dict], metrics: List[dict]) -> Tuple[Optional[str], Optional[str]]:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None, "OPENAI_API_KEY not set in .env"
    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return None, "openai package not installed"

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    context = {
        "run_summary": {k: audit.get(k) for k in ["status", "alert_count", "metric_count", "dimensions", "window_size"]},
        "top_alerts": [
            {k: a.get(k) for k in ["dimension", "attribute", "subgroup", "severity", "message", "signal_value"]}
            for a in sorted(alerts, key=lambda a: _SEV_RANK.get(str(a.get("severity", "")).upper(), 0), reverse=True)[:6]
        ],
        "high_gap_metrics": [
            m for m in metrics
            if str(m.get("metric_name", "")) == "gap_vs_overall"
            and abs(float(m.get("metric_value") or 0)) > 0.05
        ][:6],
    }
    prompt = (
        "You are a senior AI fairness auditor presenting findings to a product team. "
        "Analyze this fairness monitoring snapshot. Be direct and clinical. "
        "Output ONLY: 2–3 sentence executive summary, then exactly 3 bullet 'ACTION ITEMS' "
        "in format '• [bold label]: explanation'. Use concrete numbers from the data. "
        "Do not say 'it appears' or hedge unnecessarily.\n\n"
        f"DATA:\n{json.dumps(context, default=str)}"
    )
    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model, temperature=0.15,
            messages=[
                {"role": "system", "content": "You are a clinical AI fairness analyst. Be precise and direct."},
                {"role": "user", "content": prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip() or None, None
    except Exception as exc:
        return None, f"LLM error: {exc}"


# ──────────────────────────────────────────────────────────────
# Render sections
# ──────────────────────────────────────────────────────────────
def render_hero(audit: dict, alerts: List[dict], llm_text: Optional[str], llm_err: Optional[str]) -> None:
    score, grade, color = _health_score(alerts)
    red_count = sum(1 for a in alerts if str(a.get("severity", "")).upper() == "RED")
    yellow_count = sum(1 for a in alerts if str(a.get("severity", "")).upper() == "YELLOW")
    dims = audit.get("dimensions", []) or []
    window = audit.get("window_size", "–")
    ts = datetime.now(timezone.utc).strftime("%b %d, %Y · %H:%M UTC")

    st.markdown(
        f"""
        <div class="fo-hero">
          <div style="display:flex;align-items:flex-start;gap:36px;flex-wrap:wrap;">
            <div>
              <div class="fo-score-label">Fairness Health Score</div>
              <div class="fo-score" style="color:{color};">{score}</div>
              <div style="margin-top:6px;">
                <span class="fo-pill" style="background:{color}22;color:{color};border:1px solid {color}55;">
                  GRADE {grade}
                </span>
              </div>
              <div class="fo-score-sub" style="margin-top:10px;">
                {len(dims)} dimensions &nbsp;·&nbsp; {window:,} predictions &nbsp;·&nbsp; {ts}
              </div>
            </div>
            <div style="flex:1;display:flex;gap:14px;flex-wrap:wrap;align-items:center;padding-top:6px;">
              <div class="fo-stat">
                <div class="fo-stat-num" style="color:#ef4444;">{red_count}</div>
                <div class="fo-stat-label">Critical</div>
              </div>
              <div class="fo-stat">
                <div class="fo-stat-num" style="color:#f59e0b;">{yellow_count}</div>
                <div class="fo-stat-label">Warning</div>
              </div>
              <div class="fo-stat">
                <div class="fo-stat-num">{len(alerts)}</div>
                <div class="fo-stat-label">Total Alerts</div>
              </div>
              <div class="fo-stat">
                <div class="fo-stat-num" style="color:#38bdf8;">{audit.get("metric_count", "–")}</div>
                <div class="fo-stat-label">Metrics</div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if llm_text:
        st.markdown(
            f"""
            <div class="fo-ai-box">
              <div class="fo-ai-title">⚡ AI Audit Analysis</div>
              <div class="fo-ai-text">{llm_text.replace(chr(10), '<br>')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif llm_err:
        st.caption(f"AI analysis unavailable: {llm_err}")


def render_dimension_cards(alerts_df: pd.DataFrame) -> None:
    if alerts_df.empty:
        st.info("No alert data available.")
        return

    for col in ["severity", "dimension", "attribute", "message"]:
        if col not in alerts_df.columns:
            alerts_df[col] = "—"

    dims = sorted(alerts_df["dimension"].dropna().unique().tolist())
    cols = st.columns(min(len(dims), 4))
    for i, dim in enumerate(dims):
        sub = alerts_df[alerts_df["dimension"] == dim]
        worst_sev = sub["severity"].map(lambda s: _SEV_RANK.get(str(s).upper(), 0)).max()
        worst_label = sub.loc[sub["severity"].map(lambda s: _SEV_RANK.get(str(s).upper(), 0)) == worst_sev, "severity"].iloc[0].upper() if not sub.empty else "OK"
        color = _SEV_HEX.get(worst_label, "#475569")
        icon = _DIM_ICON.get(dim, "🔍")
        with cols[i % 4]:
            st.markdown(
                f"""
                <div class="fo-dim-card" style="border-color:{color}44;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div class="fo-dim-title">{icon} {dim}</div>
                    <span class="fo-pill" style="background:{color}22;color:{color};border:1px solid {color}55;">
                      {worst_label}
                    </span>
                  </div>
                  <div class="fo-dim-sub">{len(sub)} alerts</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_alert_chart(alerts_df: pd.DataFrame) -> None:
    if alerts_df.empty:
        return

    for col in ["severity", "dimension"]:
        if col not in alerts_df.columns:
            alerts_df[col] = "unknown"

    alerts_df = alerts_df.copy()
    alerts_df["severity"] = alerts_df["severity"].astype(str).str.upper()

    sev_order = ["RED", "YELLOW", "ORANGE", "GREEN", "INSUFFICIENT_DATA"]
    sev_df = (
        alerts_df.groupby("severity", as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    sev_df["order"] = sev_df["severity"].map(lambda s: sev_order.index(s) if s in sev_order else 99)
    sev_df = sev_df.sort_values("order")

    dim_df = (
        alerts_df.groupby("dimension", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("count", ascending=False)
    )

    cl, cr = st.columns(2)
    with cl:
        st.markdown("**Alerts by Severity**")
        sev_chart = (
            alt.Chart(sev_df)
            .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
            .encode(
                y=alt.Y("severity:N", sort=None, title="", axis=alt.Axis(labelColor="#94a3b8", grid=False)),
                x=alt.X("count:Q", title="Alerts", axis=alt.Axis(labelColor="#64748b", gridColor="#1e293b")),
                color=alt.Color(
                    "severity:N",
                    scale=alt.Scale(
                        domain=sev_df["severity"].tolist(),
                        range=[_SEV_HEX.get(s, "#475569") for s in sev_df["severity"].tolist()],
                    ),
                    legend=None,
                ),
                tooltip=["severity", "count"],
            )
            .properties(height=180, background="transparent")
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(sev_chart, use_container_width=True)

    with cr:
        st.markdown("**Alerts by Dimension**")
        dim_chart = (
            alt.Chart(dim_df)
            .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6, color="#3b82f6")
            .encode(
                y=alt.Y("dimension:N", sort="-x", title="", axis=alt.Axis(labelColor="#94a3b8", grid=False)),
                x=alt.X("count:Q", title="Alerts", axis=alt.Axis(labelColor="#64748b", gridColor="#1e293b")),
                tooltip=["dimension", "count"],
            )
            .properties(height=180, background="transparent")
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(dim_chart, use_container_width=True)


def render_alerts_tab(api_base: str, model_name: str, alerts_df: pd.DataFrame) -> None:
    if alerts_df.empty:
        st.info("No alerts in latest run.")
        return

    for col in ["severity", "dimension", "attribute", "subgroup", "message", "signal_value"]:
        if col not in alerts_df.columns:
            alerts_df[col] = "—"

    alerts_df = alerts_df.copy()
    alerts_df["_rank"] = alerts_df["severity"].map(lambda s: _SEV_RANK.get(str(s).upper(), 0))
    alerts_df["abs_signal"] = pd.to_numeric(alerts_df["signal_value"], errors="coerce").abs()

    cl, cr = st.columns([2, 3])
    with cl:
        sev_opts = sorted(alerts_df["severity"].dropna().unique(), key=lambda s: _SEV_RANK.get(str(s).upper(), 0), reverse=True)
        sev_filter = st.multiselect("Severity", sev_opts, default=sev_opts, key="alrt_sev")
    with cr:
        dim_opts = sorted(alerts_df["dimension"].dropna().unique())
        dim_filter = st.multiselect("Dimension", dim_opts, default=dim_opts, key="alrt_dim")

    filt = alerts_df[alerts_df["severity"].isin(sev_filter) & alerts_df["dimension"].isin(dim_filter)]
    filt = filt.sort_values(["_rank", "abs_signal"], ascending=[False, False])

    st.markdown(f"**{len(filt)} alerts** · sorted by severity")

    display_cols = [c for c in ["dimension", "attribute", "subgroup", "severity", "message", "signal_value"] if c in filt.columns]
    st.dataframe(
        filt[display_cols].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("Pull live alerts", key="pull_stream"):
            events, status = fetch_stream_snapshot(api_base, model_name)
            st.session_state["stream_events"] = events
            st.session_state["stream_status"] = status
            st.rerun()
    with c2:
        status = st.session_state.get("stream_status", "idle")
        color = "#22c55e" if status == "live" else "#475569"
        st.markdown(f'<span style="color:{color};font-size:.8rem;font-weight:700;">● STREAM: {status.upper()}</span>', unsafe_allow_html=True)

    stream_events = st.session_state.get("stream_events", [])
    if stream_events:
        st.markdown("**Live Streamed Alerts**")
        st.dataframe(to_df(stream_events), use_container_width=True, hide_index=True)


def render_metrics_tab(metrics_df: pd.DataFrame) -> None:
    if metrics_df.empty:
        st.info("No metrics in latest run.")
        return

    for col in ["dimension", "metric_name", "metric_value", "attribute", "subgroup"]:
        if col not in metrics_df.columns:
            metrics_df[col] = None

    dims = sorted(metrics_df["dimension"].dropna().unique())
    selected_dim = st.selectbox("Dimension", dims, key="met_dim")
    f = metrics_df[metrics_df["dimension"] == selected_dim].copy()

    metric_names = sorted(f["metric_name"].dropna().unique())
    selected_metric = st.selectbox("Metric", metric_names, key="met_name")
    chart_df = f[f["metric_name"] == selected_metric].copy()
    chart_df["metric_value"] = pd.to_numeric(chart_df["metric_value"], errors="coerce")
    chart_df = chart_df.dropna(subset=["metric_value"])

    if not chart_df.empty:
        chart_df["label"] = chart_df["attribute"].astype(str) + " · " + chart_df["subgroup"].fillna("all").astype(str)
        chart_df = chart_df.sort_values("metric_value", ascending=False).head(25)

        bar = (
            alt.Chart(chart_df)
            .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, color="#0ea5e9")
            .encode(
                y=alt.Y("label:N", sort="-x", title="", axis=alt.Axis(labelColor="#94a3b8", labelLimit=250, grid=False)),
                x=alt.X("metric_value:Q", title=selected_metric, axis=alt.Axis(labelColor="#64748b", gridColor="#1e293b")),
                tooltip=["attribute", "subgroup", "metric_name", "metric_value"],
            )
            .properties(height=max(180, len(chart_df) * 22), background="transparent")
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(bar, use_container_width=True)

    st.markdown("**Raw table**")
    display_cols = [c for c in ["attribute", "subgroup", "metric_name", "metric_value"] if c in f.columns]
    st.dataframe(f[display_cols].reset_index(drop=True), use_container_width=True, hide_index=True)


def render_drift_tab(metrics_df: pd.DataFrame) -> None:
    if metrics_df.empty or "dimension" not in metrics_df.columns:
        st.info("No drift metrics available.")
        return

    drift = metrics_df[metrics_df["dimension"] == "Fairness Drift"].copy()
    if drift.empty:
        st.info("No Fairness Drift dimension data in this run.")
        return

    drift["metric_value"] = pd.to_numeric(drift["metric_value"], errors="coerce")
    gap_df = drift[drift["metric_name"] == "window_gap"].dropna(subset=["metric_value"]).copy()

    if not gap_df.empty:
        attrs = sorted(gap_df["attribute"].dropna().unique())
        selected_attr = st.selectbox("Attribute", attrs, key="drift_attr")
        sub = gap_df[gap_df["attribute"] == selected_attr].copy()
        sub["window"] = sub["subgroup"].astype(str)
        sub = sub.sort_values("window")

        line = (
            alt.Chart(sub)
            .mark_line(strokeWidth=2.5, color="#a78bfa")
            .encode(
                x=alt.X("window:N", title="Window", axis=alt.Axis(labelColor="#94a3b8", labelAngle=-30, grid=False)),
                y=alt.Y("metric_value:Q", title="AUC Gap", axis=alt.Axis(labelColor="#64748b", gridColor="#1e293b")),
                tooltip=["window", "metric_value"],
            )
        )
        points = line.mark_point(filled=True, size=60, color="#c4b5fd")
        st.altair_chart((line + points).properties(height=260, background="transparent").configure_view(strokeWidth=0), use_container_width=True)

    slope_df = drift[drift["metric_name"] == "gap_trend_slope"].dropna(subset=["metric_value"])
    if not slope_df.empty:
        st.markdown("**Drift Slope Summary**")
        display_cols = [c for c in ["attribute", "metric_value"] if c in slope_df.columns]
        st.dataframe(slope_df[display_cols].reset_index(drop=True), use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(page_title="FairnessOps", layout="wide", page_icon="⚖️")
    _inject_css()

    # ── Sidebar ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚖️ FairnessOps")
        st.markdown('<div class="fo-side-label">API Endpoint</div>', unsafe_allow_html=True)
        api_base = st.text_input("", value="http://127.0.0.1:8000", label_visibility="collapsed", key="api_base")
        st.markdown('<div class="fo-side-label" style="margin-top:10px;">Model</div>', unsafe_allow_html=True)
        model_name = st.text_input("", value="monitor_ingest_smoke_20260425212709", label_visibility="collapsed", key="model_name")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⟳  Refresh Data"):
            st.rerun()
        st.markdown("---")
        with st.expander("Glossary"):
            st.markdown(
                "**Demographic Fairness** — performance gap by protected group\n\n"
                "**Representation** — group sample size sufficiency\n\n"
                "**Intersectionality** — combined group disparities\n\n"
                "**Fairness Drift** — gaps worsening over time\n\n"
                "**Score** — 100 = no concerns, 0 = critical"
            )

    # ── Session state ─────────────────────────────────────────
    if "stream_events" not in st.session_state:
        st.session_state["stream_events"] = []
    if "stream_status" not in st.session_state:
        st.session_state["stream_status"] = "idle"
    if "llm_cache" not in st.session_state:
        st.session_state["llm_cache"] = None

    # ── Fetch data in parallel ────────────────────────────────
    with st.spinner(""):
        with ThreadPoolExecutor(max_workers=3) as pool:
            audit_f = pool.submit(fetch_audit_latest, api_base, model_name)
            metrics_f = pool.submit(fetch_metrics_latest, api_base, model_name, None, 300)
            alerts_f = pool.submit(fetch_alerts_latest, api_base, model_name, 300)
            audit, audit_err = audit_f.result()
            metrics, metrics_err = metrics_f.result()
            alerts, alerts_err = alerts_f.result()

    if audit_err:
        st.error(f"API unreachable: {audit_err}")
        return

    metrics_df = to_df(metrics)
    alerts_df = to_df(alerts)

    # ── LLM — run once per run_id ─────────────────────────────
    current_run_id = (audit or {}).get("run_id", "")
    cached = st.session_state.get("llm_cache") or {}
    if cached.get("run_id") != current_run_id:
        with st.spinner("Generating AI analysis…"):
            llm_text, llm_err = llm_explain(audit or {}, alerts, metrics)
        st.session_state["llm_cache"] = {"run_id": current_run_id, "text": llm_text, "err": llm_err}
    else:
        llm_text = cached.get("text")
        llm_err = cached.get("err")

    # ── Page header + hero ────────────────────────────────────
    st.markdown("# ⚖️ FairnessOps")
    render_hero(audit or {}, alerts, llm_text, llm_err)
    render_dimension_cards(alerts_df)
    render_alert_chart(alerts_df)

    # ── Tabs ──────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    tab_alerts, tab_metrics, tab_drift = st.tabs(["🚨 Alert Triage", "📊 Metrics Explorer", "📈 Fairness Drift"])

    with tab_alerts:
        render_alerts_tab(api_base, model_name, alerts_df)
    with tab_metrics:
        render_metrics_tab(metrics_df)
    with tab_drift:
        render_drift_tab(metrics_df)


if __name__ == "__main__":
    main()
