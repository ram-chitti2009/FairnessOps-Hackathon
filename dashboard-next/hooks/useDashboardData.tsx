"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { fetchAlertsLatest, fetchAuditLatest, fetchMetricsLatest, fetchModels } from "@/lib/api";
import { getModelContext } from "@/lib/registry";
import type { ModelContext } from "@/lib/registry";
import type { AlertRow, AuditRun, MetricRow } from "@/lib/types";
import { useRealtimeDashboard } from "@/hooks/useRealtimeDashboard";

interface LLMState {
  text: string | null;
  error: string | null;
  loading: boolean;
}

type RoleMode = "Clinical Admin" | "Data Science" | "Compliance";

interface DashboardDataValue {
  models: string[];
  modelName: string;
  audit: AuditRun | null;
  alerts: AlertRow[];
  liveAlerts: AlertRow[];
  metrics: MetricRow[];
  ctx: ModelContext;
  lastFetched: Date;
  loading: boolean;
  error: string | null;
  realtimeStatus: "connecting" | "live" | "error";
  llm: LLMState;
  roleMode: RoleMode;
  setModelName: (name: string) => void;
  refresh: () => Promise<void>;
  setRoleMode: (role: RoleMode) => void;
}

const DashboardDataContext = createContext<DashboardDataValue | null>(null);
const MODEL_KEY = "fairnessops_model";
const ROLE_KEY = "fairnessops_role_mode";
const FALLBACK_MODEL = "synthetic_monitor_v1";

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

export function DashboardDataProvider({ children }: { children: React.ReactNode }) {
  const [models, setModels] = useState<string[]>([]);
  const [modelName, setModelNameState] = useState<string>(FALLBACK_MODEL);
  const [audit, setAudit] = useState<AuditRun | null>(null);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [liveAlerts, setLiveAlerts] = useState<AlertRow[]>([]);
  const [metrics, setMetrics] = useState<MetricRow[]>([]);
  const [ctx, setCtx] = useState<ModelContext>(() => getModelContext(FALLBACK_MODEL));
  const [lastFetched, setLastFetched] = useState<Date>(new Date());
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [realtimeStatus, setRealtimeStatus] = useState<"connecting" | "live" | "error">("connecting");
  const [llm, setLLM] = useState<LLMState>({ text: null, error: null, loading: false });
  const [roleMode, setRoleModeState] = useState<RoleMode>("Clinical Admin");
  const lastRunId = useRef<string | null>(null);

  useEffect(() => {
    try {
      const cached = window.localStorage.getItem(MODEL_KEY);
      if (cached) setModelNameState(cached);
      const role = window.localStorage.getItem(ROLE_KEY) as RoleMode | null;
      if (role) setRoleModeState(role);
    } catch {
      // no-op
    }
  }, []);

  useEffect(() => {
    fetchModels()
      .then((list) => {
        setModels(list);
        if (!list.length) return;
        if (!list.includes(modelName)) setModelNameState(list[0]);
      })
      .catch(() => {
        // API can be warming up; hard failure is handled in main refresh.
      });
  }, [modelName]);

  const refresh = useCallback(async () => {
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
      setLiveAlerts(al.slice(0, 50));
      setMetrics(me);
      setLastFetched(new Date());
      const freshCtx = getModelContext(modelName, a.metadata);
      setCtx(freshCtx);

      if (a.run_id !== lastRunId.current) {
        lastRunId.current = a.run_id;
        setLLM({ text: null, error: null, loading: true });
        callLLM(a, al, me, freshCtx).then(({ text, error: llmError }) =>
          setLLM({ text, error: llmError, loading: false }),
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [modelName]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useRealtimeDashboard({
    modelName,
    onNewRun: () => {
      setRealtimeStatus("live");
      refresh();
    },
    onNewAlert: (alert) => {
      setRealtimeStatus("live");
      if (!lastRunId.current || alert.run_id !== lastRunId.current) return;
      setLiveAlerts((prev) => [alert, ...prev].slice(0, 50));
    },
  });

  useEffect(() => {
    const t = setTimeout(() => setRealtimeStatus((s) => (s === "connecting" ? "live" : s)), 3000);
    return () => clearTimeout(t);
  }, [modelName]);

  const setModelName = useCallback((name: string) => {
    setModelNameState(name);
    setAudit(null);
    setAlerts([]);
    setMetrics([]);
    setLiveAlerts([]);
    setLLM({ text: null, error: null, loading: false });
    setError(null);
    setCtx(getModelContext(name));
    setRealtimeStatus("connecting");
    lastRunId.current = null;
    try {
      window.localStorage.setItem(MODEL_KEY, name);
    } catch {
      // no-op
    }
  }, []);

  const setRoleMode = useCallback((role: RoleMode) => {
    setRoleModeState(role);
    try {
      window.localStorage.setItem(ROLE_KEY, role);
    } catch {
      // no-op
    }
  }, []);

  const value = useMemo<DashboardDataValue>(
    () => ({
      models,
      modelName,
      audit,
      alerts,
      liveAlerts,
      metrics,
      ctx,
      lastFetched,
      loading,
      error,
      realtimeStatus,
      llm,
      roleMode,
      setModelName,
      refresh,
      setRoleMode,
    }),
    [models, modelName, audit, alerts, liveAlerts, metrics, ctx, lastFetched, loading, error, realtimeStatus, llm, roleMode, setModelName, refresh, setRoleMode],
  );

  return <DashboardDataContext.Provider value={value}>{children}</DashboardDataContext.Provider>;
}

export function useDashboardData() {
  const ctx = useContext(DashboardDataContext);
  if (!ctx) throw new Error("useDashboardData must be used within DashboardDataProvider");
  return ctx;
}
