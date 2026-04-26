"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertsTable } from "@/components/alerts-table";
import { SeverityBadge } from "@/components/ui/badge";
import { useDashboardData } from "@/hooks/useDashboardData";
import type { SeverityLevel } from "@/lib/types";

type IncidentStatus = "new" | "acknowledged" | "investigating" | "resolved";

function alertKey(
  a: { run_id: string; dimension: string; attribute: string; subgroup: string | null; created_at?: string },
  idx: number,
) {
  return `${a.run_id}:${a.dimension}:${a.attribute}:${a.subgroup ?? "all"}:${a.created_at ?? idx}`;
}

export default function IncidentsPage() {
  const { alerts, ctx, audit } = useDashboardData();
  const [statusMap, setStatusMap] = useState<Record<string, IncidentStatus>>({});
  const [ownerMap, setOwnerMap] = useState<Record<string, string>>({});

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("fairnessops_incident_status");
      if (raw) setStatusMap(JSON.parse(raw) as Record<string, IncidentStatus>);
      const owners = window.localStorage.getItem("fairnessops_incident_owner");
      if (owners) setOwnerMap(JSON.parse(owners) as Record<string, string>);
    } catch {
      // no-op
    }
  }, []);

  const persistStatus = (next: Record<string, IncidentStatus>) => {
    setStatusMap(next);
    try {
      window.localStorage.setItem("fairnessops_incident_status", JSON.stringify(next));
    } catch {
      // no-op
    }
  };
  const persistOwner = (next: Record<string, string>) => {
    setOwnerMap(next);
    try {
      window.localStorage.setItem("fairnessops_incident_owner", JSON.stringify(next));
    } catch {
      // no-op
    }
  };

  const queue = useMemo(() => {
    return alerts.slice(0, 50).map((a, idx) => {
      const id = alertKey(a, idx);
      return {
        id,
        alert: a,
        status: statusMap[id] ?? "new",
        owner: ownerMap[id] ?? "",
      };
    });
  }, [alerts, statusMap, ownerMap]);

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-sm font-semibold text-text-primary">Incident workflow queue</p>
        <p className="text-xs text-text-muted mt-1">
          Track findings through operational states: new, acknowledged, investigating, and resolved.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-surface overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">Current queue</p>
          {alerts.length > 50 && (
            <p className="text-[11px] text-text-muted">Showing first 50 of {alerts.length} findings</p>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-widest text-text-muted">Finding</th>
                <th className="px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-widest text-text-muted">Priority</th>
                <th className="px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-widest text-text-muted">Status</th>
                <th className="px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-widest text-text-muted">Owner</th>
              </tr>
            </thead>
            <tbody>
              {queue.map(({ id, alert, status, owner }) => (
                <tr key={id} className="border-b border-border/50">
                  <td className="px-4 py-2.5 text-xs text-text-secondary">
                    {alert.dimension} · {alert.attribute}
                    {alert.subgroup ? ` (${alert.subgroup})` : ""}
                  </td>
                  <td className="px-4 py-2.5"><SeverityBadge severity={alert.severity as SeverityLevel} size="sm" /></td>
                  <td className="px-4 py-2.5">
                    <select
                      value={status}
                      onChange={(e) =>
                        persistStatus({
                          ...statusMap,
                          [id]: e.target.value as IncidentStatus,
                        })
                      }
                      className="bg-muted border border-border text-text-secondary text-xs rounded-md px-2 py-1 focus:outline-none focus:border-info"
                    >
                      <option value="new">new</option>
                      <option value="acknowledged">acknowledged</option>
                      <option value="investigating">investigating</option>
                      <option value="resolved">resolved</option>
                    </select>
                  </td>
                  <td className="px-4 py-2.5">
                    <input
                      value={owner}
                      onChange={(e) =>
                        persistOwner({
                          ...ownerMap,
                          [id]: e.target.value,
                        })
                      }
                      placeholder="Assign owner"
                      className="bg-muted border border-border text-text-secondary text-xs rounded-md px-2 py-1 focus:outline-none focus:border-info"
                    />
                  </td>
                </tr>
              ))}
              {queue.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-text-muted">
                    No incidents yet. Queue populates after fairness runs complete.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <AlertsTable alerts={alerts} ctx={ctx} windowSize={audit?.window_size} />
    </div>
  );
}
