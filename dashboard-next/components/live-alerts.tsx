"use client";
import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import { DIM_ABBR, humanSignal, riskContext } from "@/lib/utils";
import type { AlertRow, SeverityLevel } from "@/lib/types";
import type { ModelContext } from "@/lib/registry";
import { Wifi, WifiOff } from "lucide-react";

interface Props {
  alerts: AlertRow[];
  realtimeStatus: "connecting" | "live" | "error";
  ctx?: ModelContext;
}

export function LiveAlertFeed({ alerts, realtimeStatus, ctx }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);

  const statusConfig = {
    live:       { color: "#22c55e", label: "Live updates active", Icon: Wifi },
    connecting: { color: "#f59e0b", label: "Connecting…",        Icon: Wifi },
    error:      { color: "#ef4444", label: "Live updates offline",       Icon: WifiOff },
  }[realtimeStatus];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <CardTitle>Live clinical finding feed</CardTitle>
          <div className="flex items-center gap-1.5 ml-auto">
            <span
              className={`h-2 w-2 rounded-full ${realtimeStatus === "live" ? "animate-pulse" : ""}`}
              style={{ background: statusConfig.color, boxShadow: `0 0 6px ${statusConfig.color}` }}
            />
            <statusConfig.Icon className="h-3.5 w-3.5" style={{ color: statusConfig.color }} />
            <span className="text-xs" style={{ color: statusConfig.color }}>{statusConfig.label}</span>
          </div>
        </div>
        <p className="text-xs text-text-muted mt-1">
          Updates as soon as each worker run finishes.
        </p>
      </CardHeader>
      <CardContent className="pt-0">
        {alerts.length === 0 ? (
          <p className="text-sm text-text-muted py-8 text-center">
            No new findings yet. New results will appear automatically after the next run.
          </p>
        ) : (
          <div className="space-y-1.5 max-h-[420px] overflow-y-auto pr-1">
            {alerts.map((a, i) => {
              const isOpen = expanded === i;
              return (
                <div
                  key={i}
                  className="rounded-lg border border-border/50 bg-muted/10 hover:border-border transition-colors cursor-pointer"
                  onClick={() => setExpanded(isOpen ? null : i)}
                >
                  <div className="flex items-center gap-3 px-3 py-2.5">
                    <SeverityBadge severity={a.severity as SeverityLevel} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-text-secondary truncate">
                        {DIM_ABBR[a.dimension] ?? a.dimension}
                        {a.attribute && <span className="text-text-muted"> · {a.attribute}</span>}
                      </p>
                    </div>
                    <span className="text-[11px] font-mono text-text-muted flex-shrink-0">
                      {humanSignal(a)}
                    </span>
                  </div>
                  {isOpen && (
                    <div className="px-3 pb-3 pt-0 border-t border-border/30">
                      <p className="text-xs text-text-secondary mt-2 leading-relaxed">
                        {riskContext(a, ctx) || a.message || "No additional detail."}
                      </p>
                      {a.subgroup && (
                        <p className="text-[11px] font-mono text-text-muted mt-1">
                          Group: {a.subgroup}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
