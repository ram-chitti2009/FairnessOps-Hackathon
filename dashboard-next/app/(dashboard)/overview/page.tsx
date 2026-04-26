"use client";

import { AlertTriangle } from "lucide-react";
import { HealthScoreCard } from "@/components/health-score";
import { AIAnalysis } from "@/components/ai-analysis";
import { DimensionStatus } from "@/components/dimension-status";
import { AlertCharts } from "@/components/alert-charts";
import { LiveAlertFeed } from "@/components/live-alerts";
import { useDashboardData } from "@/hooks/useDashboardData";

export default function OverviewPage() {
  const { audit, alerts, lastFetched, ctx, llm, error, liveAlerts, realtimeStatus } = useDashboardData();

  return (
    <div className="space-y-5">
      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-critical-bg border border-critical/30 text-critical text-sm">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          API unreachable: {error}
        </div>
      )}

      {audit ? (
        <HealthScoreCard audit={audit} alerts={alerts} lastFetched={lastFetched} ctx={ctx} />
      ) : (
        <div className="rounded-lg border border-border bg-surface p-6">
          <p className="text-sm font-semibold text-text-primary">Clinical fairness status</p>
          <p className="text-xs text-text-muted mt-1">Waiting for the latest audit run to load.</p>
        </div>
      )}

      <AIAnalysis text={llm.text} error={llm.error} loading={llm.loading} />
      <DimensionStatus alerts={alerts} />
      <AlertCharts alerts={alerts} />
      <LiveAlertFeed alerts={liveAlerts} realtimeStatus={realtimeStatus} ctx={ctx} />
    </div>
  );
}
