"use client";

import { useDashboardData } from "@/hooks/useDashboardData";
import { computeHealthScore } from "@/lib/utils";
import { ShieldCheck, Activity, Sliders, Info } from "lucide-react";

const THRESHOLD_DOCS: { label: string; value: string; description: string }[] = [
  { label: "Demographic Fairness — RED", value: "AUC gap ≥ 0.10", description: "Outcome probability gap between patient groups meets or exceeds 10 percentage points. Requires immediate clinical review." },
  { label: "Demographic Fairness — YELLOW", value: "AUC gap ≥ 0.05", description: "Gap is detectable and warrants monitoring, but does not meet the critical threshold." },
  { label: "Threshold Parity — RED", value: "Flag-rate gap ≥ 0.20", description: "One group is being escalated to care at rates that differ from other groups by 20+ percentage points." },
  { label: "False Negative Gap — RED", value: "Miss-rate gap ≥ 0.15", description: "One group's patients who should be flagged are being missed at a materially higher rate — a direct patient safety signal." },
  { label: "Calibration Fairness — RED", value: "Calibration gap ≥ 0.10", description: "Predicted risk scores are sufficiently miscalibrated across groups that identical scores imply different real risk levels." },
  { label: "Fairness Drift — RED", value: "Slope > 0.02/window", description: "The fairness gap between groups has been growing at a rate exceeding 2% per monitoring window — active worsening." },
  { label: "Algorithmic Drift (PELT) — RED", value: "AUC drop ≥ 0.05", description: "Structural changepoints detected and overall model performance has dropped more than 5% from baseline." },
  { label: "Feature Drift — RED", value: "KS stat ≥ 0.20", description: "Input data distribution has shifted substantially — the population being scored differs significantly from the training population." },
  { label: "Representation — suppressed", value: "n_eff < 10", description: "Effective sample size is too small to produce statistically reliable fairness measurements. Group data is suppressed from scoring." },
];

export default function SettingsPage() {
  const { roleMode, modelName, audit, alerts, ctx } = useDashboardData();
  const { score, grade, color } = computeHealthScore(alerts);

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-sm font-semibold text-text-primary">Operational settings</p>
        <p className="text-xs text-text-muted mt-1">
          Session controls, monitoring configuration, and fairness threshold reference for the current model.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Session */}
        <div className="rounded-lg border border-border bg-surface p-4 space-y-3">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="h-3.5 w-3.5 text-info" />
            <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">Current session</p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-md border border-border bg-muted/20 p-3">
              <p className="text-xs text-text-muted">Role mode</p>
              <p className="text-sm font-semibold text-text-primary">{roleMode}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/20 p-3">
              <p className="text-xs text-text-muted">Active model</p>
              <p className="text-sm font-semibold text-text-primary truncate" title={modelName}>{modelName}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/20 p-3">
              <p className="text-xs text-text-muted">Health score</p>
              <p className="text-sm font-semibold" style={{ color }}>{score} — {grade}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/20 p-3">
              <p className="text-xs text-text-muted">Patients reviewed</p>
              <p className="text-sm font-semibold text-text-primary">{(audit?.window_size ?? 0).toLocaleString()}</p>
            </div>
          </div>
        </div>

        {/* Clinical context */}
        <div className="rounded-lg border border-border bg-surface p-4 space-y-3">
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheck className="h-3.5 w-3.5 text-info" />
            <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">Clinical context</p>
          </div>
          <div className="grid grid-cols-1 gap-2 text-xs">
            <div className="flex justify-between py-1.5 border-b border-border/50">
              <span className="text-text-muted">Use case</span>
              <span className="text-text-primary font-medium">{ctx.useCase}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border/50">
              <span className="text-text-muted">Population</span>
              <span className="text-text-primary font-medium text-right max-w-[220px]">{ctx.population}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border/50">
              <span className="text-text-muted">Department</span>
              <span className="text-text-primary font-medium">{ctx.department}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border/50">
              <span className="text-text-muted">Patients / month</span>
              <span className="text-text-primary font-medium">{ctx.patientsPerMonth.toLocaleString()}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-text-muted">Compliance</span>
              <span className="text-text-primary font-medium text-right max-w-[220px]">{ctx.complianceNote}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Threshold reference */}
      <div className="rounded-lg border border-border bg-surface overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center gap-2">
          <Sliders className="h-3.5 w-3.5 text-text-muted" />
          <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">Fairness threshold reference</p>
        </div>
        <div className="px-4 py-3 bg-info/5 border-b border-border/50 flex items-start gap-2">
          <Info className="h-3.5 w-3.5 text-info flex-shrink-0 mt-0.5" />
          <p className="text-xs text-text-secondary">
            Thresholds are configured in the worker and applied consistently across all models. Changes require a worker restart. These values are fixed for demo consistency.
          </p>
        </div>
        <div className="divide-y divide-border/50">
          {THRESHOLD_DOCS.map((t) => (
            <div key={t.label} className="px-4 py-3 flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-4">
              <div className="flex-shrink-0 min-w-[280px]">
                <p className="text-xs font-semibold text-text-primary">{t.label}</p>
                <code className="text-[11px] font-mono text-info bg-info/10 px-1.5 py-0.5 rounded mt-1 inline-block">{t.value}</code>
              </div>
              <p className="text-xs text-text-muted leading-relaxed">{t.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
