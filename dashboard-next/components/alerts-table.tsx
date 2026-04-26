"use client";
import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import { SEV_RANK, humanSignal, riskContext, DIM_ABBR } from "@/lib/utils";
import type { AlertRow, SeverityLevel } from "@/lib/types";
import type { ModelContext } from "@/lib/registry";
import { estimateImpact } from "@/lib/registry";

interface Props { alerts: AlertRow[]; ctx: ModelContext; windowSize?: number }

const SEVS = ["All", "RED", "YELLOW", "GREEN", "INSUFFICIENT_DATA"];

export function AlertsTable({ alerts, ctx, windowSize }: Props) {
  const [dimFilter, setDimFilter] = useState("All");
  const [sevFilter, setSevFilter] = useState("All");
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 12;
  const dims = ["All", ...Array.from(new Set(alerts.map((a) => a.dimension))).sort()];

  const sorted = [...alerts].sort(
    (a, b) => SEV_RANK[b.severity?.toUpperCase() ?? ""] - SEV_RANK[a.severity?.toUpperCase() ?? ""],
  );

  const filtered = sorted.filter(
    (a) =>
      (dimFilter === "All" || a.dimension === dimFilter) &&
      (sevFilter === "All" || a.severity?.toUpperCase() === sevFilter),
  );

  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <CardTitle>Clinical finding triage</CardTitle>
          <div className="flex gap-2 flex-wrap">
            <Select label="Dimension" value={dimFilter} options={dims} onChange={(v) => { setDimFilter(v); setPage(0); }} />
            <Select label="Severity" value={sevFilter} options={SEVS} onChange={(v) => { setSevFilter(v); setPage(0); }} />
          </div>
          <span className="text-xs text-text-muted ml-auto">{filtered.length} findings</span>
        </div>
      </CardHeader>
      <CardContent className="pt-0 px-0 pb-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {["Priority", "Safety check", "Patient group", "What changed", "Clinical meaning"].map((h) => (
                <th key={h} className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-widest text-text-muted">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((a, i) => {
              const context = riskContext(a, ctx);
              const impact  = a.severity === "RED"
                ? estimateImpact(windowSize, a.signal_value, a.dimension)
                : null;
              const isCrit  = a.severity === "RED";
              const rowKey = `${a.run_id}-${a.dimension}-${a.attribute}-${a.subgroup ?? "all"}-${i}`;
              return (
              <tr key={rowKey} className={`border-b border-border/50 hover:bg-muted/20 transition-colors ${isCrit ? "bg-critical/5" : ""}`}>
                <td className="px-4 py-3 whitespace-nowrap align-top">
                  <SeverityBadge severity={a.severity as SeverityLevel} size="sm" />
                </td>
                <td className="px-4 py-3 text-text-secondary text-xs whitespace-nowrap align-top">{DIM_ABBR[a.dimension] ?? a.dimension}</td>
                <td className="px-4 py-3 text-xs align-top">
                  <span className="font-medium text-text-primary">{a.attribute ?? "—"}</span>
                  {a.subgroup && <span className="text-text-muted ml-1.5">· {a.subgroup}</span>}
                  {impact && (
                    <span className="block mt-0.5 text-[11px] text-critical font-medium">{impact} affected</span>
                  )}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-text-secondary whitespace-nowrap align-top">
                  {humanSignal(a)}
                </td>
                <td className="px-4 py-3 text-xs text-text-secondary max-w-[320px] align-top">
                  <p className="leading-relaxed">{context || a.message || "—"}</p>
                  {isCrit && ctx.complianceNote && (
                    <p className="mt-1 text-[11px] text-critical/80 font-medium">
                      Review under {ctx.complianceNote}
                    </p>
                  )}
                </td>
              </tr>
              );
            })}
            {paged.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-muted text-sm">
                  No alerts match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {totalPages > 1 && (
          <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-border">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1 rounded text-xs text-text-secondary hover:text-text-primary disabled:opacity-30 border border-border hover:border-info transition-colors"
            >
              Previous
            </button>
            <span className="text-xs text-text-muted">
              {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-3 py-1 rounded text-xs text-text-secondary hover:text-text-primary disabled:opacity-30 border border-border hover:border-info transition-colors"
            >
              Next
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Select({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-muted border border-border text-text-secondary text-xs rounded-md px-3 py-1.5 focus:outline-none focus:border-info transition-colors"
      aria-label={label}
    >
      {options.map((o) => (
        <option key={o} value={o}>{o === "All" ? `All ${label}s` : o}</option>
      ))}
    </select>
  );
}
