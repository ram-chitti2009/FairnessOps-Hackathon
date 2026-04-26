"use client";

import { useMemo } from "react";
import { Download } from "lucide-react";
import { useDashboardData } from "@/hooks/useDashboardData";
import { fmtDate, humanSignal, computeHealthScore } from "@/lib/utils";
import type { AlertRow, AuditRun } from "@/lib/types";
import type { ModelContext } from "@/lib/registry";

function buildReportHTML(
  audit: AuditRun,
  alerts: AlertRow[],
  modelName: string,
  ctx: ModelContext,
): string {
  const { score, grade } = computeHealthScore(alerts);
  const critical = alerts.filter((a) => a.severity === "RED");
  const warnings = alerts.filter((a) => a.severity === "YELLOW");
  const generatedAt = new Date().toUTCString();
  const runDate = audit.created_at ? fmtDate(audit.created_at) : "—";

  function badge(sev: string) {
    if (sev === "RED") return `<span class="badge-red">Critical</span>`;
    if (sev === "YELLOW") return `<span class="badge-yellow">Warning</span>`;
    if (sev === "GREEN") return `<span class="badge-green">Normal</span>`;
    return `<span class="badge-grey">${sev}</span>`;
  }

  const findingRows = alerts.slice(0, 40).map((a) => `
    <tr>
      <td>${badge(a.severity)}</td>
      <td>${a.dimension}</td>
      <td>${a.attribute ?? "—"}${a.subgroup ? ` · ${a.subgroup}` : ""}</td>
      <td>${humanSignal(a)}</td>
      <td style="max-width:280px;word-break:break-word;">${a.message ?? "—"}</td>
    </tr>`).join("");

  const truncNote = alerts.length > 40
    ? `<p style="color:#6b7280;font-size:12px;margin-top:8px;">Showing first 40 of ${alerts.length} findings. Full data available in Supabase audit_runs.</p>`
    : "";

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>FairnessOps Audit Report — ${modelName}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #111827; background: #fff; font-size: 13px; line-height: 1.6; }
    .page { max-width: 860px; margin: 0 auto; padding: 48px 40px; }
    .header { display: flex; align-items: flex-start; justify-content: space-between; border-bottom: 2px solid #e5e7eb; padding-bottom: 20px; margin-bottom: 28px; }
    .brand { font-size: 20px; font-weight: 800; color: #1e3a5f; letter-spacing: -0.02em; }
    .brand-sub { font-size: 12px; color: #6b7280; margin-top: 3px; }
    .run-meta { text-align: right; font-size: 12px; color: #6b7280; }
    .run-meta strong { color: #374151; }
    .score-row { display: flex; align-items: center; gap: 24px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px 24px; margin-bottom: 24px; }
    .score-number { font-size: 48px; font-weight: 900; color: ${score >= 70 ? "#16a34a" : score >= 50 ? "#d97706" : "#dc2626"}; line-height: 1; }
    .score-label { font-size: 13px; font-weight: 700; color: #374151; margin-top: 4px; }
    .score-sub { font-size: 11px; color: #9ca3af; margin-top: 2px; }
    .stat-box { text-align: center; }
    .stat-value { font-size: 22px; font-weight: 800; color: #111827; }
    .stat-value.red { color: #dc2626; }
    .stat-value.yellow { color: #d97706; }
    .stat-label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }
    .divider { width: 1px; height: 48px; background: #e5e7eb; }
    h2 { font-size: 13px; font-weight: 700; color: #1e3a5f; text-transform: uppercase; letter-spacing: 0.08em; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; margin: 28px 0 14px; }
    .meta-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 24px; }
    .meta-item { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 12px 14px; }
    .meta-label { font-size: 10px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.06em; }
    .meta-value { font-size: 13px; font-weight: 600; color: #111827; margin-top: 3px; word-break: break-all; }
    .policy-box { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 14px 16px; margin-bottom: 24px; }
    .policy-box p { font-size: 12px; color: #1e40af; line-height: 1.5; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    thead th { text-align: left; padding: 8px 10px; background: #f3f4f6; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #6b7280; border-bottom: 1px solid #e5e7eb; }
    tbody td { padding: 7px 10px; border-bottom: 1px solid #f9fafb; color: #374151; vertical-align: top; }
    tbody tr:hover td { background: #fafafa; }
    .badge-red { background: #fef2f2; color: #dc2626; border: 1px solid #fca5a5; border-radius: 4px; padding: 1px 7px; font-size: 10px; font-weight: 700; white-space: nowrap; }
    .badge-yellow { background: #fffbeb; color: #d97706; border: 1px solid #fcd34d; border-radius: 4px; padding: 1px 7px; font-size: 10px; font-weight: 700; white-space: nowrap; }
    .badge-green { background: #f0fdf4; color: #16a34a; border: 1px solid #86efac; border-radius: 4px; padding: 1px 7px; font-size: 10px; font-weight: 700; white-space: nowrap; }
    .badge-grey { background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; border-radius: 4px; padding: 1px 7px; font-size: 10px; font-weight: 700; white-space: nowrap; }
    .footer { margin-top: 40px; padding-top: 14px; border-top: 1px solid #e5e7eb; display: flex; justify-content: space-between; font-size: 10px; color: #9ca3af; }
    @media print {
      body { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
      .page { padding: 0; }
      @page { margin: 0.75in; size: letter; }
      h2 { break-before: auto; }
      table { page-break-inside: auto; }
      tr { page-break-inside: avoid; }
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <div>
        <div class="brand">FairnessOps</div>
        <div class="brand-sub">Clinical AI Fairness Monitoring — Audit Evidence Report</div>
      </div>
      <div class="run-meta">
        <div><strong>Model:</strong> ${modelName}</div>
        <div><strong>Run date:</strong> ${runDate}</div>
        <div><strong>Run ID:</strong> ${audit.run_id ?? "—"}</div>
        <div style="margin-top:4px;color:#9ca3af;">Generated: ${generatedAt}</div>
      </div>
    </div>

    <div class="score-row">
      <div>
        <div class="score-number">${score}</div>
        <div class="score-label">${grade}</div>
        <div class="score-sub">Fairness Health Score</div>
      </div>
      <div class="divider"></div>
      <div class="stat-box">
        <div class="stat-value red">${critical.length}</div>
        <div class="stat-label">Critical</div>
      </div>
      <div class="stat-box">
        <div class="stat-value yellow">${warnings.length}</div>
        <div class="stat-label">Warnings</div>
      </div>
      <div class="stat-box">
        <div class="stat-value">${audit.alert_count ?? alerts.length}</div>
        <div class="stat-label">Total Findings</div>
      </div>
      <div class="stat-box">
        <div class="stat-value">${(audit.window_size ?? 0).toLocaleString()}</div>
        <div class="stat-label">Patients Reviewed</div>
      </div>
      <div class="stat-box">
        <div class="stat-value">${audit.metric_count ?? "—"}</div>
        <div class="stat-label">Checks Run</div>
      </div>
    </div>

    <h2>Model and Clinical Context</h2>
    <div class="meta-grid">
      <div class="meta-item"><div class="meta-label">Use Case</div><div class="meta-value">${ctx.useCase}</div></div>
      <div class="meta-item"><div class="meta-label">Patient Population</div><div class="meta-value">${ctx.population}</div></div>
      <div class="meta-item"><div class="meta-item"><div class="meta-label">Department</div><div class="meta-value">${ctx.department}</div></div></div>
      <div class="meta-item"><div class="meta-label">Patients / Month</div><div class="meta-value">${ctx.patientsPerMonth.toLocaleString()}</div></div>
      <div class="meta-item"><div class="meta-label">Dimensions Checked</div><div class="meta-value">${(audit.dimensions ?? []).join(", ") || "—"}</div></div>
      <div class="meta-item"><div class="meta-label">Compliance Framework</div><div class="meta-value">${ctx.complianceNote}</div></div>
    </div>

    <div class="policy-box">
      <p><strong>Compliance anchor:</strong> ${ctx.complianceNote}. This report constitutes audit evidence for governance review. Recommended evidence packet: this report, findings table, drift panel data, and action log.</p>
    </div>

    <h2>All Findings (${alerts.length} total)</h2>
    <table>
      <thead>
        <tr>
          <th style="width:80px">Priority</th>
          <th>Safety Check</th>
          <th>Patient Group</th>
          <th>Signal</th>
          <th>Message</th>
        </tr>
      </thead>
      <tbody>
        ${findingRows || '<tr><td colspan="5" style="text-align:center;color:#9ca3af;padding:20px;">No findings in this run.</td></tr>'}
      </tbody>
    </table>
    ${truncNote}

    <div class="footer">
      <span>FairnessOps Clinical AI Monitoring · ${ctx.complianceNote}</span>
      <span>Run ID: ${audit.run_id ?? "—"} · Generated ${generatedAt}</span>
    </div>
  </div>
</body>
</html>`;
}

function triggerPrintExport(
  audit: AuditRun,
  alerts: AlertRow[],
  modelName: string,
  ctx: ModelContext,
) {
  const html = buildReportHTML(audit, alerts, modelName, ctx);
  const win = window.open("", "_blank", "width=900,height=750");
  if (!win) {
    alert("Pop-up blocked. Please allow pop-ups for this site to export the report.");
    return;
  }
  win.document.write(html);
  win.document.close();
  win.focus();
  setTimeout(() => {
    win.print();
  }, 600);
}

export default function CompliancePage() {
  const { audit, alerts, modelName, ctx } = useDashboardData();
  const critical = useMemo(() => alerts.filter((a) => a.severity === "RED"), [alerts]);

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-sm font-semibold text-text-primary">Compliance and audit evidence</p>
        <p className="text-xs text-text-muted mt-1">
          Operational evidence for governance reviews, with latest run metadata and high-priority findings.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <div className="rounded-md border border-border bg-muted/20 p-3">
          <p className="text-xs text-text-muted">Model</p>
          <p className="text-sm font-semibold text-text-primary truncate" title={modelName}>{modelName}</p>
        </div>
        <div className="rounded-md border border-border bg-muted/20 p-3">
          <p className="text-xs text-text-muted">Last audit run</p>
          <p className="text-sm font-semibold text-text-primary">{audit?.created_at ? fmtDate(audit.created_at) : "—"}</p>
        </div>
        <div className="rounded-md border border-border bg-muted/20 p-3">
          <p className="text-xs text-text-muted">Active checks</p>
          <p className="text-sm font-semibold text-text-primary">{audit?.dimensions?.length ?? 0}</p>
        </div>
        <div className="rounded-md border border-border bg-muted/20 p-3">
          <p className="text-xs text-text-muted">Critical findings</p>
          <p className="text-sm font-semibold text-critical">{critical.length}</p>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-surface p-4 space-y-3">
        <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">Policy anchor</p>
        <p className="text-sm text-text-primary">{ctx.complianceNote}</p>
        <p className="text-xs text-text-muted">
          Export includes: run metadata, all findings, clinical context, and compliance anchor — print or save as PDF.
        </p>
        <button
          type="button"
          onClick={() => {
            if (!audit) return;
            triggerPrintExport(audit, alerts, modelName, ctx);
          }}
          disabled={!audit}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-info/40 text-info text-xs bg-info/10 hover:bg-info/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Download className="h-3.5 w-3.5" />
          Export audit report (PDF / print)
        </button>
        {!audit && (
          <p className="text-xs text-text-muted">Waiting for audit run to load before export is available.</p>
        )}
      </div>

      <div className="rounded-lg border border-border bg-surface overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">Top critical findings</p>
          {critical.length > 0 && (
            <span className="text-[11px] text-critical font-medium">{critical.length} requiring immediate review</span>
          )}
        </div>
        <div className="p-4 space-y-2">
          {critical.slice(0, 8).map((a, idx) => (
            <div key={`${a.run_id}-${a.dimension}-${a.attribute}-${idx}`} className="rounded-md border border-critical/30 bg-critical/10 p-3">
              <div className="flex items-start justify-between gap-2">
                <p className="text-xs font-semibold text-critical">{a.dimension}</p>
                <span className="text-[11px] font-mono text-critical/70 flex-shrink-0">{humanSignal(a)}</span>
              </div>
              <p className="text-xs text-text-secondary mt-1">
                {a.attribute}{a.subgroup ? ` · ${a.subgroup}` : ""}
              </p>
              {a.message && (
                <p className="text-xs text-text-muted mt-1 leading-relaxed">{a.message}</p>
              )}
            </div>
          ))}
          {critical.length === 0 && (
            <p className="text-sm text-text-muted py-2">No critical findings in the latest run.</p>
          )}
          {critical.length > 8 && (
            <p className="text-xs text-text-muted pt-1">
              +{critical.length - 8} more critical findings — export report for full list.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
