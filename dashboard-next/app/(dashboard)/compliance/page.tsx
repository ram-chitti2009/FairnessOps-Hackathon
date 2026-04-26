"use client";

import { useMemo } from "react";
import { useDashboardData } from "@/hooks/useDashboardData";

export default function CompliancePage() {
  const { audit, alerts, modelName, ctx, lastFetched } = useDashboardData();
  const critical = useMemo(() => alerts.filter((a) => a.severity === "RED"), [alerts]);

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-sm font-semibold text-text-primary">Compliance and audit evidence</p>
        <p className="text-xs text-text-muted mt-1">
          Operational evidence for governance reviews, with latest run metadata and high-priority findings.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <div className="rounded-md border border-border bg-muted/20 p-3">
          <p className="text-xs text-text-muted">Model</p>
          <p className="text-sm font-semibold text-text-primary">{modelName}</p>
        </div>
        <div className="rounded-md border border-border bg-muted/20 p-3">
          <p className="text-xs text-text-muted">Last run time</p>
          <p className="text-sm font-semibold text-text-primary">{lastFetched.toLocaleString()}</p>
        </div>
        <div className="rounded-md border border-border bg-muted/20 p-3">
          <p className="text-xs text-text-muted">Active checks</p>
          <p className="text-sm font-semibold text-text-primary">{audit?.dimensions?.length ?? 0}</p>
        </div>
        <div className="rounded-md border border-border bg-muted/20 p-3">
          <p className="text-xs text-text-muted">Critical findings</p>
          <p className="text-sm font-semibold text-critical">{critical.length}</p>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-surface p-4 space-y-3">
        <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">Policy anchor</p>
        <p className="text-sm text-text-primary">{ctx.complianceNote}</p>
        <p className="text-xs text-text-muted">
          Recommended export packet for review board: run metadata, findings table, drift panel screenshot, and action log.
        </p>
        <button
          type="button"
          className="px-3 py-1.5 rounded-md border border-info/40 text-info text-xs bg-info/10 hover:bg-info/20 transition-colors"
        >
          Export audit packet (demo)
        </button>
      </div>

      <div className="rounded-lg border border-border bg-surface overflow-hidden">
        <div className="px-4 py-3 border-b border-border">
          <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">Top critical findings</p>
        </div>
        <div className="p-4 space-y-2">
          {critical.slice(0, 8).map((a, idx) => (
            <div key={`${a.run_id}-${a.dimension}-${idx}`} className="rounded-md border border-critical/30 bg-critical/10 p-3">
              <p className="text-xs font-semibold text-critical">{a.dimension}</p>
              <p className="text-xs text-text-secondary mt-1">
                {a.attribute}{a.subgroup ? ` (${a.subgroup})` : ""} · signal {a.signal_value ?? "—"}
              </p>
            </div>
          ))}
          {critical.length === 0 && (
            <p className="text-sm text-text-muted">No critical findings in the latest run.</p>
          )}
        </div>
      </div>
    </div>
  );
}
