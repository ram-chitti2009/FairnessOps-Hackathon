"use client";

import { DriftChart } from "@/components/drift-chart";
import { useDashboardData } from "@/hooks/useDashboardData";

export default function DriftPage() {
  const { metrics } = useDashboardData();

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-sm font-semibold text-text-primary">Trend and stability monitoring</p>
        <p className="text-xs text-text-muted mt-1">
          Track fairness trends and model reliability changes over time, including PELT changepoints.
        </p>
      </div>
      <DriftChart metrics={metrics} />
    </div>
  );
}
