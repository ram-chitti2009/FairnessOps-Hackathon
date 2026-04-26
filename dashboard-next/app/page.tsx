"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { fetchModels, fetchAuditLatest, fetchAlertsLatest, fetchMetricsLatest } from "@/lib/api";
import type { AuditRun, AlertRow, MetricRow } from "@/lib/types";
import { Navbar } from "@/components/navbar";
import { HealthScoreCard } from "@/components/health-score";
import { AIAnalysis } from "@/components/ai-analysis";
import { DimensionStatus } from "@/components/dimension-status";
import { AlertCharts } from "@/components/alert-charts";
import { AlertsTable } from "@/components/alerts-table";
import { MetricsExplorer } from "@/components/metrics-explorer";
import { DriftChart } from "@/components/drift-chart";
import { LiveAlertFeed } from "@/components/live-alerts";
import { useRealtimeDashboard } from "@/hooks/useRealtimeDashboard";
import { getModelContext } from "@/lib/registry";
import type { ModelContext } from "@/lib/registry";
import { AlertTriangle } from "lucide-react";

const FALLBACK_MODEL = "monitor_ingest_smoke_20260425212709";

interface LLMState { text: string | null; error: string | null; loading: boolean }

async function callLLM(
  audit: AuditRun,
  alerts: AlertRow[],
  metrics: MetricRow[],
  clinicalContext: ModelContext,
): Promise<{ text: string | null; error: string | null }> {
  try {
    const res = await fetch("/api/llm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audit,
        alerts: alerts.slice(0, 8),
        metrics: metrics.slice(0, 10),
        clinicalContext,
      }),
    });
    const json = await res.json();
    return { text: json.text ?? null, error: json.error ?? null };
  } catch (e) {
    return { text: null, error: String(e) };
  }
}

// ── Inner component (needs Suspense boundary for useSearchParams) ─────────────
function DashboardInner() {
  const searchParams = useSearchParams();
  const router       = useRouter();

  // Model selection — URL param takes priority, then fallback constant
  const [models, setModels]             = useState<string[]>([]);
  const [modelName, setModelNameState]  = useState<string>(
    searchParams.get("model") ?? FALLBACK_MODEL,
  );

  const [audit, setAudit]               = useState<AuditRun | null>(null);
  const [alerts, setAlerts]             = useState<AlertRow[]>([]);
  const [liveAlerts, setLiveAlerts]     = useState<AlertRow[]>([]);
  const [metrics, setMetrics]           = useState<MetricRow[]>([]);
  const [lastFetched, setLastFetched]   = useState<Date>(new Date());
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState<string | null>(null);
  const [rtStatus, setRtStatus]         = useState<"connecting" | "live" | "error">("connecting");
  const [llm, setLLM]                   = useState<LLMState>({ text: null, error: null, loading: false });
  const [activeTab, setActiveTab]       = useState<"overview" | "alerts" | "metrics" | "drift" | "live">("overview");
  const [ctx, setCtx]                   = useState<ModelContext>(() => getModelContext(modelName));
  const lastRunId                        = useRef<string | null>(null);

  // ── Load available models once on mount ──────────────────────────────────
  useEffect(() => {
    fetchModels()
      .then((list) => {
        setModels(list);
        // If URL has no model param but DB has models, default to first
        if (!searchParams.get("model") && list.length > 0 && !list.includes(modelName)) {
          handleModelChange(list[0]);
        }
      })
      .catch(() => {/* API might not be up yet — silent */});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Switch model ─────────────────────────────────────────────────────────
  const handleModelChange = useCallback((name: string) => {
    setModelNameState(name);
    router.push(`?model=${encodeURIComponent(name)}`, { scroll: false });
    // Reset all data so old model's data doesn't flash during load
    setAudit(null);
    setAlerts([]);
    setMetrics([]);
    setLiveAlerts([]);
    setLLM({ text: null, error: null, loading: false });
    setError(null);
    setCtx(getModelContext(name));
    lastRunId.current = null;
    setRtStatus("connecting");
  }, [router]);

  // ── Full data refresh ─────────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [a, al, me] = await Promise.all([
        fetchAuditLatest(modelName),
        fetchAlertsLatest(modelName, 300),
        fetchMetricsLatest(modelName, 1000),
      ]);
      setAudit(a);
      setAlerts(al);
      // Seed live feed from latest run so the tab is never empty after refresh
      // or when realtime inserts arrive before run_id sync completes.
      setLiveAlerts(al.slice(0, 50));
      setMetrics(me);
      setLastFetched(new Date());
      const freshCtx = getModelContext(modelName, a.metadata);
      setCtx(freshCtx);

      if (a.run_id !== lastRunId.current) {
        lastRunId.current = a.run_id;
        setLLM({ text: null, error: null, loading: true });
        callLLM(a, al, me, freshCtx).then(({ text, error }) =>
          setLLM({ text, error, loading: false }),
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [modelName]);

  // Re-fetch when model changes or on mount
  useEffect(() => { loadData(); }, [loadData]);

  // ── Supabase Realtime ─────────────────────────────────────────────────────
  useRealtimeDashboard({
    modelName,
    onNewRun: () => {
      setRtStatus("live");
      loadData();
    },
    onNewAlert: (alert) => {
      setRtStatus("live");
      // Guard against cross-model/cross-run inserts when multiple workers are active.
      if (!lastRunId.current || alert.run_id !== lastRunId.current) return;
      setLiveAlerts((prev) => [alert, ...prev].slice(0, 50));
    },
  });

  useEffect(() => {
    const t = setTimeout(() => setRtStatus((s) => (s === "connecting" ? "live" : s)), 3000);
    return () => clearTimeout(t);
  }, []);

  const tabs = [
    { id: "overview",  label: "Overview" },
    { id: "alerts",    label: "Clinical Findings" },
    { id: "metrics",   label: "Detailed Review" },
    { id: "drift",     label: "Trend Monitoring" },
    { id: "live",      label: "Live Updates" },
  ] as const;

  return (
    <div className="min-h-screen bg-background">
      <Navbar
        modelName={modelName}
        models={models}
        ctx={ctx}
        realtimeStatus={rtStatus}
        lastFetched={lastFetched}
        loading={loading}
        onRefresh={loadData}
        onModelChange={handleModelChange}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {error && (
          <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-critical-bg border border-critical/30 text-critical text-sm">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            API unreachable: {error}
          </div>
        )}

        {audit && (
          <HealthScoreCard audit={audit} alerts={alerts} lastFetched={lastFetched} ctx={ctx} />
        )}

        <div className="flex gap-1 border-b border-border">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === t.id
                  ? "text-info border-info"
                  : "text-text-muted border-transparent hover:text-text-secondary"
              }`}
            >
              {t.label}
              {t.id === "live" && liveAlerts.length > 0 && (
                <span className="ml-1.5 text-[10px] bg-critical text-white rounded-full px-1.5 py-0.5">
                  {liveAlerts.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {activeTab === "overview" && (
          <div className="space-y-5">
            <AIAnalysis text={llm.text} error={llm.error} loading={llm.loading} />
            {alerts.length > 0 && <DimensionStatus alerts={alerts} />}
            {alerts.length > 0 && <AlertCharts alerts={alerts} />}
          </div>
        )}

        {activeTab === "alerts" && (
          <AlertsTable alerts={alerts} ctx={ctx} windowSize={audit?.window_size} />
        )}

        {activeTab === "metrics" && <MetricsExplorer metrics={metrics} />}

        {activeTab === "drift" && <DriftChart metrics={metrics} />}

        {activeTab === "live" && (
          <LiveAlertFeed alerts={liveAlerts} realtimeStatus={rtStatus} ctx={ctx} />
        )}
      </main>
    </div>
  );
}

// ── Root export — Suspense required for useSearchParams in App Router ─────────
export default function Dashboard() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-text-muted text-sm">Loading dashboard…</p>
      </div>
    }>
      <DashboardInner />
    </Suspense>
  );
}
