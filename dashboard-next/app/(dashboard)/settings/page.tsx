"use client";

import { useDashboardData } from "@/hooks/useDashboardData";

export default function SettingsPage() {
  const { roleMode, modelName } = useDashboardData();

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-sm font-semibold text-text-primary">Operational settings</p>
        <p className="text-xs text-text-muted mt-1">
          Demo-safe controls and transparency settings for the current monitoring session.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-lg border border-border bg-surface p-4 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">Current session</p>
          <div className="rounded-md border border-border bg-muted/20 p-3">
            <p className="text-xs text-text-muted">Role mode</p>
            <p className="text-sm font-semibold text-text-primary">{roleMode}</p>
          </div>
          <div className="rounded-md border border-border bg-muted/20 p-3">
            <p className="text-xs text-text-muted">Active model</p>
            <p className="text-sm font-semibold text-text-primary">{modelName}</p>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-surface p-4 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">Threshold governance</p>
          <p className="text-sm text-text-secondary">
            Threshold tuning is currently managed in worker configuration. Keep this stable for demo consistency.
          </p>
          <button
            type="button"
            className="px-3 py-1.5 rounded-md border border-border text-text-muted text-xs cursor-not-allowed"
            disabled
          >
            Threshold editor (roadmap)
          </button>
        </div>
      </div>
    </div>
  );
}
