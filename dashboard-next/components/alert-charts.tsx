"use client";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { SEV_COLOR, DIM_ABBR } from "@/lib/utils";
import type { AlertRow, SeverityLevel } from "@/lib/types";

const SEV_ORDER: SeverityLevel[] = ["RED", "YELLOW", "GREEN", "INSUFFICIENT_DATA"];

interface Props { alerts: AlertRow[] }

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface border border-border rounded-lg px-3 py-2 text-xs">
      <p className="text-text-secondary mb-0.5">{label}</p>
      <p className="text-text-primary font-semibold">{payload[0].value} findings</p>
    </div>
  );
};

export function AlertCharts({ alerts }: Props) {
  const sevData = SEV_ORDER.map((sev) => ({
    label: sev === "INSUFFICIENT_DATA" ? "Insuf. Data" : sev.charAt(0) + sev.slice(1).toLowerCase(),
    count: alerts.filter((a) => a.severity?.toUpperCase() === sev).length,
    sev,
  })).filter((d) => d.count > 0);

  const dimCounts = Object.entries(
    alerts.reduce<Record<string, number>>((acc, a) => {
      acc[a.dimension] = (acc[a.dimension] ?? 0) + 1;
      return acc;
    }, {}),
  ).sort((a, b) => b[1] - a[1]);

  const dimData = dimCounts.map(([dim, count]) => ({
    label: DIM_ABBR[dim] ?? dim,
    count,
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <Card>
        <CardHeader><CardTitle>Urgency mix across findings</CardTitle></CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={sevData} layout="vertical" margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
              <XAxis type="number" tick={{ fill: "#3d5a7a", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="label" tick={{ fill: "#7a9cc0", fontSize: 12 }} axisLine={false} tickLine={false} width={75} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "#0f2035" }} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={24}>
                {sevData.map((d) => (
                  <Cell key={d.sev} fill={SEV_COLOR[d.sev as SeverityLevel] ?? "#3d5a7a"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Where care-equity risks are concentrated</CardTitle></CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={dimData} layout="vertical" margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
              <XAxis type="number" tick={{ fill: "#3d5a7a", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="label" tick={{ fill: "#7a9cc0", fontSize: 12 }} axisLine={false} tickLine={false} width={95} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "#0f2035" }} />
              <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} maxBarSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
