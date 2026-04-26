"use client";
import { Card, CardContent } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import { SEV_RANK } from "@/lib/utils";
import type { AlertRow, SeverityLevel } from "@/lib/types";

interface Props { alerts: AlertRow[] }

const DIM_LABEL: Record<string, string> = {
  "Demographic Fairness": "Demographic Fairness",
  "Representation": "Representation",
  "Intersectionality (2-way)": "Intersectionality",
  "Fairness Drift": "Fairness Drift",
};

export function DimensionStatus({ alerts }: Props) {
  const dims = Array.from(new Set(alerts.map((a) => a.dimension))).sort();

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
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
              <p className="text-xs text-text-muted mt-2">{sub.length} alert{sub.length !== 1 ? "s" : ""}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
