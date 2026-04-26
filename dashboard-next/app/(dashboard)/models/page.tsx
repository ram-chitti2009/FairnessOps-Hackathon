"use client";

import { useDashboardData } from "@/hooks/useDashboardData";
import { MetricsExplorer } from "@/components/metrics-explorer";

export default function ModelsPage() {
  const { models, modelName, audit, alerts, setModelName, ctx, metrics } = useDashboardData();

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-sm font-semibold text-text-primary">Model registry and operating context</p>
        <p className="text-xs text-text-muted mt-1">
          Select a monitored model and review current deployment context and latest operational status.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="rounded-lg border border-border bg-surface p-4 lg:col-span-1">
          <p className="text-xs font-semibold uppercase tracking-widest text-text-muted mb-3">Monitored models</p>
          <div className="space-y-1.5 max-h-[320px] overflow-y-auto">
            {models.map((m) => (
              <button
                key={m}
                onClick={() => setModelName(m)}
                className={`w-full text-left px-3 py-2 rounded-md border text-xs transition-colors ${
                  m === modelName
                    ? "border-info/40 bg-info/10 text-info"
                    : "border-border text-text-secondary hover:text-text-primary hover:bg-muted/30"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-surface p-4 lg:col-span-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-text-muted mb-3">Current model context</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <div className="rounded-md border border-border bg-muted/20 p-3">
              <p className="text-xs text-text-muted">Use case</p>
              <p className="text-text-primary font-semibold">{ctx.useCase}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/20 p-3">
              <p className="text-xs text-text-muted">Clinical population</p>
              <p className="text-text-primary font-semibold">{ctx.population}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/20 p-3">
              <p className="text-xs text-text-muted">Outcome phrase</p>
              <p className="text-text-primary font-semibold">{ctx.outcome}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/20 p-3">
              <p className="text-xs text-text-muted">Department</p>
              <p className="text-text-primary font-semibold">{ctx.department}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/20 p-3">
              <p className="text-xs text-text-muted">Patients per month</p>
              <p className="text-text-primary font-semibold">{ctx.patientsPerMonth.toLocaleString()}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/20 p-3">
              <p className="text-xs text-text-muted">Compliance note</p>
              <p className="text-text-primary font-semibold">{ctx.complianceNote}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4 text-xs">
            <div className="rounded-md border border-border bg-muted/10 p-3">
              <p className="text-text-muted">Latest run id</p>
              <p className="text-text-secondary font-mono break-all">{audit?.run_id ?? "No run yet"}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/10 p-3">
              <p className="text-text-muted">Alerts in latest run</p>
              <p className="text-text-primary font-semibold">{alerts.length}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/10 p-3">
              <p className="text-text-muted">Window size</p>
              <p className="text-text-primary font-semibold">{audit?.window_size?.toLocaleString() ?? "—"}</p>
            </div>
          </div>
        </div>
      </div>

      <MetricsExplorer metrics={metrics} />
    </div>
  );
}
