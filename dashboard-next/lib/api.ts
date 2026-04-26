import type { AuditRun, AlertRow, MetricRow } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(`${BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`GET ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

/** Returns all distinct model names that have at least one audit run. */
export async function fetchModels(): Promise<string[]> {
  return get<string[]>("/audit/models");
}

export async function fetchAuditLatest(modelName: string): Promise<AuditRun> {
  return get<AuditRun>("/audit/latest", { model_name: modelName });
}

export async function fetchAlertsLatest(modelName: string, limit = 300): Promise<AlertRow[]> {
  const data = await get<{ items: AlertRow[] }>("/alerts/latest", {
    model_name: modelName,
    limit,
  });
  return data.items ?? [];
}

export async function fetchMetricsLatest(
  modelName: string,
  limit = 300,
  dimension?: string,
): Promise<MetricRow[]> {
  const params: Record<string, string | number> = { model_name: modelName, limit };
  if (dimension) params.dimension = dimension;
  const data = await get<{ items: MetricRow[] }>("/metrics/latest", params);
  return data.items ?? [];
}
