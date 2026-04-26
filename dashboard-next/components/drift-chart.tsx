"use client";
import { useState, useMemo, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { MetricRow } from "@/lib/types";

interface Props { metrics: MetricRow[] }

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface border border-border rounded-lg px-3 py-2 text-xs">
      <p className="text-text-secondary mb-0.5">{label}</p>
      <p className="text-text-primary font-semibold">Gap level: {payload[0].value?.toFixed(4)}</p>
    </div>
  );
};

export function DriftChart({ metrics }: Props) {
  const driftMetrics = metrics.filter((m) => m.dimension === "Fairness Drift");
  const algoMetrics = metrics.filter((m) => m.dimension === "Algorithmic Drift (PELT)");
  const attrs = useMemo(
    () => Array.from(new Set(driftMetrics.filter((m) => m.metric_name === "window_gap").map((m) => m.attribute))).sort(),
    [driftMetrics],
  );
  const [attr, setAttr] = useState(attrs[0] ?? "");
  useEffect(() => {
    if (!attrs.length) return;
    if (!attrs.includes(attr)) setAttr(attrs[0]);
  }, [attrs, attr]);

  const gapData = useMemo(() => {
    return driftMetrics
      .filter((m) => m.metric_name === "window_gap" && m.attribute === attr && m.metric_value !== null)
      .map((m) => ({ window: m.subgroup ?? "", gap: m.metric_value as number }))
      .sort((a, b) => a.window.localeCompare(b.window, undefined, { numeric: true }));
  }, [driftMetrics, attr]);

  const slopeRows = driftMetrics.filter((m) => m.metric_name === "gap_trend_slope");
  const algoWindow = useMemo(() => {
    return algoMetrics
      .filter((m) => m.metric_name === "overall_auc" && m.metric_value !== null)
      .map((m) => {
        const md = m.metadata ?? {};
        return {
          window: m.subgroup ?? "",
          auc: m.metric_value as number,
          isCp: Boolean(md.is_changepoint),
        };
      })
      .sort((a, b) => a.window.localeCompare(b.window, undefined, { numeric: true }));
  }, [algoMetrics]);

  const algoSummary = useMemo(() => {
    const byName = new Map(algoMetrics.map((m) => [m.metric_name, m.metric_value]));
    const cpCount = algoWindow.filter((w) => w.isCp).length;
    return {
      baseline: byName.get("baseline_auc"),
      current: byName.get("current_auc"),
      drop: byName.get("auc_drop"),
      cpCount,
    };
  }, [algoMetrics, algoWindow]);

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
            <CardTitle>Fairness gap trend over time</CardTitle>
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
            Each point is a recent monitoring window. An upward line means the fairness gap is worsening for <span className="text-text-secondary font-medium">{attr}</span>.
          </p>
          {gapData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={gapData} margin={{ left: 8, right: 20, top: 8, bottom: 4 }}>
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

      {algoWindow.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Algorithmic drift (PELT changepoints)</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-text-muted mb-3">
              This shows model performance across recent windows. Red markers indicate PELT changepoints (sudden regime shifts).
            </p>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={algoWindow} margin={{ left: 8, right: 20, top: 8, bottom: 4 }}>
                <XAxis dataKey="window" tick={{ fill: "#3d5a7a", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 1]} tick={{ fill: "#3d5a7a", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  const pt = payload[0].payload as { auc: number; isCp: boolean };
                  return (
                    <div className="bg-surface border border-border rounded-lg px-3 py-2 text-xs">
                      <p className="text-text-secondary mb-0.5">{label}</p>
                      <p className="text-text-primary font-semibold">AUC: {pt.auc?.toFixed(4)}</p>
                      {pt.isCp && <p className="text-critical mt-0.5 font-medium">Changepoint detected</p>}
                    </div>
                  );
                }} />
                <Line
                  type="monotone"
                  dataKey="auc"
                  stroke="#22c55e"
                  strokeWidth={2.5}
                  dot={{ fill: "#22c55e", r: 3 }}
                  activeDot={{ r: 5, fill: "#4ade80" }}
                />
                {algoWindow.filter((w) => w.isCp).map((w) => (
                  <ReferenceLine key={`cp-${w.window}`} x={w.window} stroke="#ef4444" strokeDasharray="4 2" />
                ))}
              </LineChart>
            </ResponsiveContainer>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-4 text-xs">
              <div className="rounded-md border border-border bg-muted/20 px-3 py-2">
                <div className="text-text-muted">Baseline AUC</div>
                <div className="text-text-primary font-semibold">{algoSummary.baseline?.toFixed(3) ?? "—"}</div>
              </div>
              <div className="rounded-md border border-border bg-muted/20 px-3 py-2">
                <div className="text-text-muted">Current AUC</div>
                <div className="text-text-primary font-semibold">{algoSummary.current?.toFixed(3) ?? "—"}</div>
              </div>
              <div className="rounded-md border border-border bg-muted/20 px-3 py-2">
                <div className="text-text-muted">AUC drop</div>
                <div className="text-text-primary font-semibold">{algoSummary.drop?.toFixed(3) ?? "—"}</div>
              </div>
              <div className="rounded-md border border-border bg-muted/20 px-3 py-2">
                <div className="text-text-muted">Changepoints</div>
                <div className="text-text-primary font-semibold">{algoSummary.cpCount}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {slopeRows.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Care equity direction by patient group</CardTitle></CardHeader>
          <CardContent className="pt-0">
            <p className="text-xs text-text-muted mb-3">
              This section shows whether fairness is getting better or worse over time for each patient group.
            </p>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-0 py-2 text-left text-[11px] font-semibold uppercase tracking-widest text-text-muted">Patient group</th>
                  <th className="px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-widest text-text-muted">Recent change</th>
                  <th className="px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-widest text-text-muted">Clinical status</th>
                </tr>
              </thead>
              <tbody>
                {slopeRows.map((r, i) => {
                  const slope = r.metric_value ?? 0;
                  const isWorsening = slope > 0.02;
                  const isImproving = slope < -0.005;
                  const statusText = isWorsening ? "Worsening" : isImproving ? "Improving" : "Watching";
                  const changeText =
                    isWorsening
                      ? "Gap is widening quickly"
                      : isImproving
                        ? "Gap is narrowing"
                        : "Small movement";
                  return (
                    <tr key={i} className="border-b border-border/50">
                      <td className="py-2.5 text-xs text-text-primary">{r.attribute}</td>
                      <td className="px-4 py-2.5 text-xs text-text-secondary">
                        {changeText}
                      </td>
                      <td
                        className="px-4 py-2.5 text-xs font-medium"
                        style={{ color: isWorsening ? "#f59e0b" : isImproving ? "#22c55e" : "#7a9cc0" }}
                      >
                        {statusText}
                        <span className="ml-1 text-text-muted font-normal">
                          ({slope > 0 ? "+" : ""}{slope.toFixed(3)})
                        </span>
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
