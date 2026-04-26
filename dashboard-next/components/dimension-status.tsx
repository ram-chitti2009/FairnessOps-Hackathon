"use client";
import { Card, CardContent } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import { SEV_RANK } from "@/lib/utils";
import type { AlertRow, SeverityLevel } from "@/lib/types";

interface Props { alerts: AlertRow[] }

const DIM_LABEL: Record<string, string> = {
  "Demographic Fairness": "Demographic equity",
  "Representation": "Data sufficiency",
  "Intersectionality (2-way)": "Compound group equity",
  "Fairness Drift": "Equity trend over time",
  "Algorithmic Drift (PELT)": "Model stability over time",
  "Threshold Parity": "Care-escalation parity",
  "False Negative Gap": "Missed-care parity",
  "Calibration Fairness": "Risk-score reliability parity",
  "Feature Drift": "Input pattern shift",
};

export function DimensionStatus({ alerts }: Props) {
  const dims = Array.from(new Set(alerts.map((a) => a.dimension))).sort();

  if (!dims.length) {
    return (
      <Card className="border-border">
        <CardContent className="pt-4 pb-4">
          <p className="text-sm text-text-primary font-semibold">Clinical status by safety check</p>
          <p className="text-xs text-text-muted mt-1">No findings yet. Status cards appear after a completed worker run.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <div>
        <p className="text-sm text-text-primary font-semibold">Clinical status by safety check</p>
        <p className="text-xs text-text-muted mt-1">
          Each card shows the current worst status for that check and how many findings were detected.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {dims.map((dim) => {
          const sub = alerts.filter((a) => a.dimension === dim);
          const worstSev = sub.reduce(
            (best, a) =>
              SEV_RANK[a.severity?.toUpperCase() ?? ""] > SEV_RANK[best] ? a.severity : best,
            "INSUFFICIENT_DATA" as string,
          ) as SeverityLevel;

          return (
            <Card key={dim} className="border-border">
              <CardContent className="pt-4 pb-4">
                <p className="text-xs font-medium text-text-secondary mb-2 leading-tight">
                  {DIM_LABEL[dim] ?? dim}
                </p>
                <SeverityBadge severity={worstSev} size="sm" />
                <p className="text-xs text-text-muted mt-2">{sub.length} finding{sub.length !== 1 ? "s" : ""}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
