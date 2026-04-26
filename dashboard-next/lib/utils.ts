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
  "Algorithmic Drift (PELT)": "Algo Drift",
  "Threshold Parity": "Threshold Parity",
  "False Negative Gap": "FNR Gap",
  "Calibration Fairness": "Calibration",
  "Feature Drift": "Feature Drift",
};

export function computeHealthScore(alerts: AlertRow[]): {
  score: number;
  grade: string;
  color: string;
} {
  if (!alerts.length) return { score: 100, grade: "A", color: "#22c55e" };
  // Health index weights are intentionally conservative so low-volume runs
  // don't collapse to 0 too easily while still reflecting critical risk.
  const red = alerts.filter((a) => a.severity === "RED").length;
  const yellow = alerts.filter((a) => a.severity === "YELLOW").length;
  const representationRed = alerts.filter(
    (a) => a.severity === "RED" && a.dimension === "Representation",
  ).length;
  const harmfulRed = Math.max(0, red - representationRed);
  const penalty = Math.min(
    100,
    harmfulRed * 7 +
      representationRed * 3 +
      yellow * 2 +
      Math.max(0, Math.floor((alerts.length - 12) / 8)),
  );
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
    // signal_value is gap × √(n_eff) — a priority score, NOT a 0-1 fraction.
    // Map to plain severity labels so it isn't misread as a percentage.
    if (n >= 1.0) return "Severe compound gap";
    if (n >= 0.5) return "High compound gap";
    if (n >= 0.2) return "Moderate compound gap";
    return "Low compound gap";
  }

  if (dim === "Fairness Drift") {
    if (n > 0.005) return "Gap widening";
    if (n < -0.005) return "Gap closing";
    return "Gap stable";
  }

  if (dim === "Algorithmic Drift (PELT)") {
    const pct = Math.abs(n * 100).toFixed(1);
    return `${pct}% performance drop`;
  }

  if (dim === "Threshold Parity") {
    const pct = Math.abs(n * 100).toFixed(1);
    return `${pct}% care-escalation gap`;
  }

  if (dim === "False Negative Gap") {
    const pct = Math.abs(n * 100).toFixed(1);
    return `${pct}% missed-care gap`;
  }

  if (dim === "Calibration Fairness") {
    const pct = Math.abs(n * 100).toFixed(1);
    return `${pct}% risk-score mismatch`;
  }

  if (dim === "Feature Drift") {
    if (n >= 0.20) return "Major distribution shift";
    if (n >= 0.10) return "Moderate distribution shift";
    return "Minor distribution shift";
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
      return `Only ${n} ${attr ? attr.toLowerCase() + " " : ""}patients in this group were analyzed — too few to draw reliable conclusions. Expand data collection before acting on these findings.`;
    if (n < 30)
      return `${n} ${attr ? attr.toLowerCase() + " " : ""}patients analyzed. Results are directionally useful but should be verified against a larger sample before clinical decisions are made.`;
    return `${n} ${attr ? attr.toLowerCase() + " " : ""}patients analyzed — sufficient volume to draw reliable conclusions for this group.`;
  }

  if (dim.includes("Intersectionality")) {
    // subgroup looks like "gender=Male|race=Black" — parse into readable label
    const parsedGroups = (alert.subgroup ?? "")
      .split("|")
      .map((p) => p.split("=")[1] ?? p)
      .filter(Boolean);
    const groupLabel = parsedGroups.length > 0
      ? parsedGroups.join(" + ") + " patients"
      : "patients in overlapping groups";

    if (sev === "RED")
      return `${cap(groupLabel)} face a compounded disadvantage — this combination of characteristics puts them at significantly higher risk of being missed for ${outcome}. Requires immediate escalation.${compNote ? ` Review under ${compNote}.` : ""}`;
    if (sev === "YELLOW")
      return `A gap was detected for ${groupLabel}. Investigate whether care delivery differs for patients who fall into both of these groups simultaneously.`;
    return `No meaningful disparity found for ${groupLabel}.`;
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

  if (dim === "Algorithmic Drift (PELT)") {
    if (v === null) return "Model performance drift could not be measured in this window.";
    const drop = Math.abs(Number(v) * 100);
    if (drop >= 10)
      return `Overall model performance has dropped by ${drop.toFixed(1)}% from baseline with structural changepoints detected over time. Immediate model review and recalibration are recommended.${compNote ? ` Review under ${compNote}.` : ""}`;
    if (drop >= 5)
      return `Overall model performance has dropped by ${drop.toFixed(1)}% from baseline. Monitor closely and investigate recent workflow or population changes.`;
    return `Overall model performance remains close to baseline with no material algorithmic degradation.`;
  }

  if (dim === "Threshold Parity") {
    if (v === null) return `Could not measure decision-rate parity for ${groupDesc}.`;
    const pct = Math.abs(Number(v) * 100);
    if (pct >= 20)
      return `${cap(groupDesc)} are being flagged for ${outcome} at rates that differ by ${pct.toFixed(1)}% versus other groups. This indicates material action-allocation disparity and requires immediate review.`;
    if (pct >= 10)
      return `${cap(groupDesc)} show a ${pct.toFixed(1)}% difference in how often they are flagged for ${outcome}. Validate whether this is clinically justified by underlying risk.`;
    return `Flagging rates are broadly consistent across groups for this decision threshold.`;
  }

  if (dim === "False Negative Gap") {
    if (v === null) return `Could not estimate miss-rate parity for ${groupDesc}.`;
    const pct = Math.abs(Number(v) * 100);
    if (pct >= 20)
      return `${cap(groupDesc)} have a ${pct.toFixed(1)}% higher miss-rate for patients who should be ${outcome}. This is a high-risk patient safety concern requiring immediate escalation.${compNote ? ` Review under ${compNote}.` : ""}`;
    if (pct >= 10)
      return `${cap(groupDesc)} have a ${pct.toFixed(1)}% higher miss-rate for patients requiring ${outcome}. Investigate thresholding and subgroup model behavior.`;
    return `Miss-rates are similar across groups in this audit window.`;
  }

  if (dim === "Calibration Fairness") {
    if (v === null) return `Could not estimate calibration parity for ${groupDesc}.`;
    const pct = Math.abs(Number(v) * 100);
    if (pct >= 10)
      return `Risk scores are miscalibrated across groups by ${pct.toFixed(1)}%, meaning identical scores can imply different real-world risk. Recalibration is strongly recommended before operational use.`;
    if (pct >= 5)
      return `A ${pct.toFixed(1)}% calibration gap is present across groups. Monitor and recalibrate if this pattern persists.`;
    return `Predicted risk scores are similarly calibrated across groups.`;
  }

  if (dim === "Feature Drift") {
    if (v === null) return "Input feature distribution shift could not be computed for this variable.";
    const ks = Number(v);
    if (ks >= 0.20)
      return `Input data patterns have shifted substantially, which can destabilize fairness and model validity. Investigate population or workflow changes immediately.`;
    if (ks >= 0.10)
      return `Input data patterns are drifting. Continue close monitoring and assess whether retraining is needed.`;
    return `Input data distribution remains stable relative to baseline.`;
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
