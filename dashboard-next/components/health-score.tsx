"use client";
import { Card, CardContent } from "@/components/ui/card";
import { computeHealthScore } from "@/lib/utils";
import type { AuditRun, AlertRow } from "@/lib/types";
import type { ModelContext } from "@/lib/registry";
import { estimateImpact } from "@/lib/registry";
// ctx is used for clinical banner; estimateImpact uses audit.window_size directly
import { Building2, Users, AlertTriangle } from "lucide-react";

interface Props {
  audit: AuditRun;
  alerts: AlertRow[];
  lastFetched: Date;
  ctx: ModelContext;
}

export function HealthScoreCard({ audit, alerts, lastFetched, ctx }: Props) {
  const { score, grade, color } = computeHealthScore(alerts);
  const red    = alerts.filter((a) => a.severity === "RED").length;
  const yellow = alerts.filter((a) => a.severity === "YELLOW").length;

  // Worst signal for impact estimate — skip Intersectionality alerts since their
  // signal_value is a priority score (gap × √n_eff), not a 0-1 gap fraction.
  const worstRed = alerts.filter(
    (a) => a.severity === "RED",
  )[0];
  const impact = worstRed
    ? estimateImpact(audit.window_size, worstRed.signal_value, worstRed.dimension)
    : null;

  const stats = [
    { label: "Immediate Review", value: red, color: "#ef4444" },
    { label: "Monitor Closely", value: yellow, color: "#f59e0b" },
    { label: "Findings This Run", value: audit.alert_count, color: "#e8f0fe" },
    { label: "Safety Signals Checked", value: audit.metric_count, color: "#3b82f6" },
    { label: "Patients Reviewed", value: (audit.window_size ?? 0).toLocaleString(), color: "#8b5cf6" },
  ];

  return (
    <Card className="bg-gradient-to-br from-[#0d1929] to-[#060d1a] border-border overflow-hidden">
      {/* Clinical context banner */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 px-5 pt-4 pb-3 border-b border-border/50">
        <div className="flex items-center gap-1.5">
          <Building2 className="h-3.5 w-3.5 text-info flex-shrink-0" />
          <span className="text-xs font-semibold text-text-primary">{ctx.useCase}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Users className="h-3.5 w-3.5 text-text-muted flex-shrink-0" />
          <span className="text-xs text-text-secondary">{ctx.population}</span>
        </div>
        <span className="text-xs text-text-muted">{ctx.department}</span>
        <span className="text-xs text-text-muted">~{ctx.patientsPerMonth.toLocaleString()} patients/month</span>
        {impact && red > 0 && (
          <div className="ml-auto flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-critical/10 border border-critical/30">
            <AlertTriangle className="h-3 w-3 text-critical flex-shrink-0" />
            <span className="text-[11px] font-semibold text-critical">
              Est. {impact} affected by top finding
            </span>
          </div>
        )}
      </div>

      <CardContent className="pt-5">
        <div className="flex flex-col lg:flex-row gap-8 items-start lg:items-center">
          {/* Score */}
          <div className="flex-shrink-0">
            <p className="text-xs font-semibold uppercase tracking-widest text-text-secondary mb-2">
              Clinical Fairness Status
            </p>
            <div className="flex items-end gap-3">
              <span className="text-7xl font-black leading-none" style={{ color }}>
                {score}
              </span>
              <div className="mb-1">
                <span
                  className="inline-block px-2.5 py-0.5 rounded text-sm font-bold"
                  style={{ color, background: `${color}18`, border: `1px solid ${color}44` }}
                >
                  {grade}
                </span>
              </div>
            </div>
            <p className="text-xs text-text-muted mt-2">
              {audit.dimensions.length} fairness checks active · Run {new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "UTC", timeZoneName: "short" }).format(new Date(audit.created_at))}
            </p>
          </div>

          <div className="hidden lg:block w-px h-20 bg-border" />

          {/* Stats */}
          <div className="flex flex-wrap gap-4">
            {stats.map((s) => (
              <div key={s.label} className="min-w-[100px]">
                <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">{s.label}</p>
                <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Dimension chips */}
          <div className="lg:ml-auto flex flex-wrap gap-2">
            {audit.dimensions.map((d) => (
              <span
                key={d}
                className="px-2.5 py-1 rounded-md text-xs font-medium border border-border text-text-secondary bg-muted/30"
              >
                {d}
              </span>
            ))}
          </div>
        </div>

        {/* Score bar */}
        <div className="mt-5 h-1.5 rounded-full bg-border overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${score}%`, background: color }}
          />
        </div>
      </CardContent>
    </Card>
  );
}
