"use client";
import { useState, useMemo } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import type { MetricRow } from "@/lib/types";

interface Props { metrics: MetricRow[] }

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface border border-border rounded-lg px-3 py-2 text-xs">
      <p className="text-text-secondary mb-0.5">{label}</p>
      <p className="text-text-primary font-semibold">AUC Gap: {payload[0].value?.toFixed(4)}</p>
    </div>
  );
};

export function DriftChart({ metrics }: Props) {
  const driftMetrics = metrics.filter((m) => m.dimension === "Fairness Drift");
  const attrs = useMemo(
    () => Array.from(new Set(driftMetrics.filter((m) => m.metric_name === "window_gap").map((m) => m.attribute))).sort(),
    [driftMetrics],
  );
  const [attr, setAttr] = useState(attrs[0] ?? "");

  const gapData = useMemo(() => {
    return driftMetrics
      .filter((m) => m.metric_name === "window_gap" && m.attribute === attr && m.metric_value !== null)
      .map((m) => ({ window: m.subgroup ?? "", gap: m.metric_value as number }))
      .sort((a, b) => a.window.localeCompare(b.window, undefined, { numeric: true }));
  }, [driftMetrics, attr]);

  const slopeRows = driftMetrics.filter((m) => m.metric_name === "gap_trend_slope");

  if (!driftMetrics.length) {
    return (
      <Card>
        <CardHeader><CardTitle>Fairness Drift</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-text-muted py-6 text-center">No drift data in current run.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <CardTitle>AUC Gap Over Prediction Windows</CardTitle>
            {attrs.length > 1 && (
              <select
                value={attr}
                onChange={(e) => setAttr(e.target.value)}
                className="bg-muted border border-border text-text-secondary text-xs rounded-md px-3 py-1.5 focus:outline-none focus:border-info"
              >
                {attrs.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-text-muted mb-3">
            Each window represents a rolling slice of predictions. Upward trend indicates worsening fairness disparity for <span className="text-text-secondary font-medium">{attr}</span>.
          </p>
          {gapData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={gapData} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
                <XAxis dataKey="window" tick={{ fill: "#3d5a7a", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#3d5a7a", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={0} stroke="#1a2d45" strokeDasharray="4 2" />
                <Line
                  type="monotone"
                  dataKey="gap"
                  stroke="#8b5cf6"
                  strokeWidth={2.5}
                  dot={{ fill: "#8b5cf6", r: 4 }}
                  activeDot={{ r: 6, fill: "#a78bfa" }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-text-muted py-6 text-center">No window gap data for {attr}.</p>
          )}
        </CardContent>
      </Card>

      {slopeRows.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Drift Trend Summary</CardTitle></CardHeader>
          <CardContent className="pt-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-0 py-2 text-left text-[11px] font-semibold uppercase tracking-widest text-text-muted">Attribute</th>
                  <th className="px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-widest text-text-muted">Trend Slope</th>
                  <th className="px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-widest text-text-muted">Direction</th>
                </tr>
              </thead>
              <tbody>
                {slopeRows.map((r, i) => {
                  const slope = r.metric_value ?? 0;
                  return (
                    <tr key={i} className="border-b border-border/50">
                      <td className="py-2.5 font-mono text-xs text-text-primary">{r.attribute}</td>
                      <td className="px-4 py-2.5 font-mono text-xs" style={{ color: slope > 0 ? "#f59e0b" : "#22c55e" }}>
                        {slope > 0 ? "+" : ""}{slope?.toFixed(4) ?? "—"}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-text-secondary">
                        {slope > 0.02 ? "Worsening" : slope < -0.005 ? "Improving" : "Stable"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
