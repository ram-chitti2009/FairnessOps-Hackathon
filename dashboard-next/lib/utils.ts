import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { AlertRow, SeverityLevel } from "./types";
import type { ModelContext } from "./registry";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const SEV_RANK: Record<string, number> = {
  RED: 4,
  YELLOW: 3,
  GREEN: 1,
  INSUFFICIENT_DATA: 0,
};

export const SEV_COLOR: Record<SeverityLevel, string> = {
  RED: "#ef4444",
  YELLOW: "#f59e0b",
  GREEN: "#22c55e",
  INSUFFICIENT_DATA: "#3d5a7a",
};

export const SEV_BG: Record<SeverityLevel, string> = {
  RED: "#1c0a0a",
  YELLOW: "#1c1200",
  GREEN: "#051a0e",
  INSUFFICIENT_DATA: "#0a1520",
};

export const SEV_LABEL: Record<SeverityLevel, string> = {
  RED: "Critical",
  YELLOW: "Warning",
  GREEN: "Normal",
  INSUFFICIENT_DATA: "Insufficient Data",
};

export const DIM_ABBR: Record<string, string> = {
  "Demographic Fairness": "Demographic",
  "Representation": "Representation",
  "Intersectionality (2-way)": "Intersectionality",
  "Fairness Drift": "Drift",
};

export function computeHealthScore(alerts: AlertRow[]): {
  score: number;
  grade: string;
  color: string;
} {
  if (!alerts.length) return { score: 100, grade: "A", color: "#22c55e" };
  const red = alerts.filter((a) => a.severity === "RED").length;
  const yellow = alerts.filter((a) => a.severity === "YELLOW").length;
  const penalty = Math.min(100, red * 8 + yellow * 3 + Math.max(0, Math.floor((alerts.length - 10) / 5)));
  const score = Math.max(0, 100 - penalty);
  if (score >= 85) return { score, grade: "A", color: "#22c55e" };
  if (score >= 70) return { score, grade: "B", color: "#86efac" };
  if (score >= 50) return { score, grade: "C", color: "#f59e0b" };
  if (score >= 30) return { score, grade: "D", color: "#f97316" };
  return { score, grade: "F", color: "#ef4444" };
}

/** Parse LLM markdown response → clean paragraphs + action items */
export function parseLLMResponse(text: string): {
  summary: string;
  actions: { label: string; body: string }[];
} {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const summaryLines: string[] = [];
  const actions: { label: string; body: string }[] = [];

  for (const line of lines) {
    // Match "• **Label**: body" or "- **Label**: body"
    const actionMatch = line.match(/^[•\-\*]\s*\*{1,2}([^*:]+)\*{0,2}[:\s]+(.+)$/);
    if (actionMatch) {
      actions.push({ label: actionMatch[1].trim(), body: actionMatch[2].trim() });
    } else if (!line.startsWith("#") && actions.length === 0) {
      // Clean up any stray markdown
      summaryLines.push(line.replace(/\*\*/g, "").replace(/\*/g, "").replace(/^#+\s*/, ""));
    }
  }

  return {
    summary: summaryLines.join(" ").trim(),
    actions,
  };
}

export function fmtSignal(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (isNaN(n)) return "—";
  return n.toFixed(3);
}

/**
 * Plain-English label for a signal value — no stats terminology.
 */
export function humanSignal(alert: {
  dimension: string;
  metric_name?: string;
  signal_value: number | null;
  severity?: string;
}): string {
  const v = alert.signal_value;
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (isNaN(n)) return "—";

  const dim = alert.dimension ?? "";

  if (dim === "Demographic Fairness") {
    const pct = Math.abs(n * 100).toFixed(1);
    return `${pct}% outcome gap`;
  }

  if (dim === "Representation") {
    const rounded = Math.round(n);
    return `${rounded} patients`;
  }

  if (dim.includes("Intersectionality")) {
    const pct = Math.abs(n * 100).toFixed(1);
    return `${pct}% combined gap`;
  }

  if (dim === "Fairness Drift") {
    if (n > 0.005) return "Gap widening";
    if (n < -0.005) return "Gap closing";
    return "Gap stable";
  }

  return n.toFixed(3);
}

/** Capitalises first letter. */
function cap(s: string) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

/**
 * Full clinical sentence a CMIO can act on.
 * Names the real attribute group, outcome, and recommended action.
 * Pass `ctx` from getModelContext() for outcome-specific language.
 */
export function riskContext(
  alert: {
    dimension: string;
    attribute?: string;
    subgroup?: string | null;
    signal_value: number | null;
    severity?: string;
  },
  ctx?: Pick<ModelContext, "outcome" | "population" | "complianceNote">,
): string {
  const v = alert.signal_value;
  const dim = alert.dimension ?? "";
  const sev = (alert.severity ?? "").toUpperCase();

  // Build the group descriptor from attribute + subgroup
  const attr = alert.attribute ? cap(alert.attribute) : null;
  const sub  = alert.subgroup  ? cap(alert.subgroup)  : null;
  const groupDesc = attr && sub ? `${sub} ${attr} patients`
                 : sub          ? `${sub} patients`
                 : attr         ? `${attr} group patients`
                 : "patients in this group";

  const outcome   = ctx?.outcome      ?? "flagged for intervention";
  const compNote  = ctx?.complianceNote ?? "";

  if (dim === "Demographic Fairness") {
    if (v === null)
      return `Could not measure the outcome gap for ${groupDesc} — not enough data to draw conclusions.`;
    const pct = Math.abs(Number(v) * 100);
    if (pct >= 20)
      return `${cap(groupDesc)} are ${pct.toFixed(1)}% less likely to be ${outcome} compared to other groups. This level of disparity requires immediate clinical review.${compNote ? ` May trigger reporting under ${compNote}.` : ""}`;
    if (pct >= 10)
      return `${cap(groupDesc)} are ${pct.toFixed(1)}% less likely to be ${outcome}. A targeted clinical audit of this subgroup is recommended.`;
    return `Outcome rates for ${groupDesc} are within acceptable range relative to other groups.`;
  }

  if (dim === "Representation") {
    if (v === null) return "Patient count could not be determined for this group.";
    const n = Math.round(Number(v));
    if (n < 10)
      return `Only ${n} ${attr ? attr.toLowerCase() : ""}patients in this group were analyzed — too few to draw reliable conclusions. Expand data collection before acting on these findings.`;
    if (n < 30)
      return `${n} ${attr ? attr.toLowerCase() + " " : ""}patients analyzed. Results are directionally useful but should be verified against a larger sample before clinical decisions are made.`;
    return `${n} ${attr ? attr.toLowerCase() + " " : ""}patients analyzed — sufficient volume to draw reliable conclusions for this group.`;
  }

  if (dim.includes("Intersectionality")) {
    const example = attr ? `(e.g. older ${attr.toLowerCase()} patients)` : "(e.g. patients who are both elderly and from a specific racial group)";
    if (sev === "RED")
      return `Patients who fall into two overlapping risk categories ${example} are significantly less likely to be ${outcome}. This compound disparity requires immediate escalation.${compNote ? ` Review under ${compNote}.` : ""}`;
    if (sev === "YELLOW")
      return `A gap was found for patients in overlapping groups ${example}. Investigate whether care delivery differs for this combined subgroup.`;
    return `No meaningful disparity found when looking at patients across overlapping groups.`;
  }

  if (dim === "Fairness Drift") {
    if (v === null) return "Trend direction could not be determined — insufficient historical data.";
    const slope = Number(v);
    if (slope > 0.02)
      return `The gap in ${outcome.replace("flagged for ", "")} rates between patient groups has been consistently growing over recent periods. Investigate whether recent data changes or model updates are responsible.`;
    if (slope > 0.005)
      return `The outcome gap between groups is slowly widening. No immediate action needed, but monitor closely over the next few periods.`;
    if (slope < -0.005)
      return `The outcome gap between patient groups has been narrowing over time — a positive trend. Continue monitoring to confirm improvement.`;
    return `The outcome gap between patient groups has remained steady over time. No drift detected.`;
  }

  return "";
}

export function fmtDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
      timeZoneName: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}
