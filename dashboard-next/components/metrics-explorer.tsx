"use client";
import { useState, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { MetricRow } from "@/lib/types";

interface Props { metrics: MetricRow[] }

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const val = payload[0].value as number;
  return (
    <div className="bg-surface border border-border rounded-lg px-3 py-2 text-xs">
      <p className="text-text-secondary mb-0.5 font-mono">{label}</p>
      <p className="text-text-primary font-semibold">{val.toFixed(4)}</p>
    </div>
  );
};

export function MetricsExplorer({ metrics }: Props) {
  const dims = useMemo(() => Array.from(new Set(metrics.map((m) => m.dimension))).sort(), [metrics]);
  const [dim, setDim] = useState(dims[0] ?? "");

  const metricNames = useMemo(
    () => Array.from(new Set(metrics.filter((m) => m.dimension === dim).map((m) => m.metric_name))).sort(),
    [metrics, dim],
  );
  const [metricName, setMetricName] = useState(metricNames[0] ?? "");
  const currentMetricName = metricNames.includes(metricName) ? metricName : metricNames[0] ?? "";

  const chartData = useMemo(() => {
    return metrics
      .filter((m) => m.dimension === dim && m.metric_name === currentMetricName && m.metric_value !== null)
      .map((m) => ({
        label: `${m.attribute} · ${m.subgroup ?? "all"}`,
        value: m.metric_value as number,
      }))
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
      .slice(0, 20);
  }, [metrics, dim, currentMetricName]);

  if (!dims.length) return null;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <CardTitle>Metrics Explorer</CardTitle>
          <div className="flex gap-2">
            <select
              value={dim}
              onChange={(e) => { setDim(e.target.value); setMetricName(""); }}
              className="bg-muted border border-border text-text-secondary text-xs rounded-md px-3 py-1.5 focus:outline-none focus:border-info"
            >
              {dims.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <select
              value={currentMetricName}
              onChange={(e) => setMetricName(e.target.value)}
              className="bg-muted border border-border text-text-secondary text-xs rounded-md px-3 py-1.5 focus:outline-none focus:border-info"
            >
              {metricNames.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {chartData.length ? (
          <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 28)}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
              <XAxis type="number" tick={{ fill: "#3d5a7a", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="label" tick={{ fill: "#7a9cc0", fontSize: 11 }} axisLine={false} tickLine={false} width={180} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "#0f2035" }} />
              <ReferenceLine x={0} stroke="#1a2d45" />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={20}>
                {chartData.map((d, i) => (
                  <Cell key={i} fill={d.value < 0 ? "#ef4444" : d.value > 0.1 ? "#3b82f6" : "#22c55e"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-text-muted py-8 text-center">No numeric values for this selection.</p>
        )}
      </CardContent>
    </Card>
  );
}
