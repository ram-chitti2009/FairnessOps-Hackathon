import { NextRequest, NextResponse } from "next/server";
import { readFileSync } from "fs";
import { join } from "path";

// Load .env from project root at runtime (server only)
function getOpenAIKey(): string {
  const key = process.env.OPENAI_API_KEY?.trim();
  if (key) return key;
  try {
    const envPath = join(process.cwd(), "..", ".env");
    const content = readFileSync(envPath, "utf-8");
    const match = content.match(/^OPENAI_API_KEY=(.+)$/m);
    return match?.[1]?.trim() ?? "";
  } catch {
    return "";
  }
}

export async function POST(req: NextRequest) {
  const apiKey = getOpenAIKey();
  if (!apiKey) {
    return NextResponse.json({ text: null, error: "OPENAI_API_KEY not configured" });
  }

  const { audit, alerts, metrics, clinicalContext } = await req.json();

  function llmSignalText(a: any): string | null {
    const dim = String(a?.dimension ?? "");
    const raw = a?.signal_value;
    if (raw === null || raw === undefined || Number.isNaN(Number(raw))) return null;
    const n = Number(raw);

    if (dim === "Demographic Fairness") return `${Math.abs(n * 100).toFixed(1)}% outcome gap`;
    if (dim === "Representation") return `${Math.round(n)} patients`;
    if (dim.includes("Intersectionality")) {
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
    if (dim === "Algorithmic Drift (PELT)") return `${Math.abs(n * 100).toFixed(1)}% performance drop`;
    if (dim === "Threshold Parity") return `${Math.abs(n * 100).toFixed(1)}% care-escalation gap`;
    if (dim === "False Negative Gap") return `${Math.abs(n * 100).toFixed(1)}% missed-care gap`;
    if (dim === "Calibration Fairness") return `${Math.abs(n * 100).toFixed(1)}% risk-score mismatch`;
    if (dim === "Feature Drift") {
      if (n >= 0.20) return "Major distribution shift";
      if (n >= 0.10) return "Moderate distribution shift";
      return "Minor distribution shift";
    }
    return null;
  }

  const topAlerts = (alerts ?? []).slice(0, 6).map((a: any) => ({
    dimension: a.dimension,
    attribute: a.attribute,
    subgroup: a.subgroup,
    severity: a.severity,
    signal_text: llmSignalText(a),
    raw_signal_value: a.signal_value,
  }));

  const context = {
    clinical_model: {
      use_case:           clinicalContext?.useCase       ?? "Clinical Risk Model",
      outcome_label:      clinicalContext?.outcome       ?? "flagged as high risk",
      patient_population: clinicalContext?.population    ?? "General Inpatient",
      department:         clinicalContext?.department    ?? "Unknown",
      patients_per_month: clinicalContext?.patientsPerMonth ?? null,
      compliance:         clinicalContext?.complianceNote  ?? null,
    },
    audit_summary: {
      patient_records_scored: audit?.window_size,
      total_findings:         audit?.alert_count,
      critical_findings:      (alerts ?? []).filter((a: any) => a.severity === "RED").length,
      dimensions_checked:     audit?.dimensions,
    },
    top_findings: topAlerts,
    notable_gaps: (metrics ?? [])
      .filter((m: any) => m.metric_name === "gap_vs_overall" && Math.abs(m.metric_value ?? 0) > 0.05)
      .slice(0, 5)
      .map((m: any) => ({
        group: `${m.attribute} — ${m.subgroup ?? "overall"}`,
        gap: `${(Math.abs(m.metric_value) * 100).toFixed(1)}%`,
      })),
  };

  const prompt = `You are a senior clinical AI fairness auditor briefing a Chief Medical Information Officer (CMIO).

The model under review is: ${context.clinical_model.use_case}.
It scores ${context.clinical_model.patient_population} in ${context.clinical_model.department}.
A positive prediction means the patient is ${context.clinical_model.outcome_label}.
This model scores approximately ${context.clinical_model.patients_per_month ?? "unknown"} patients per month.
${context.clinical_model.compliance ? `Compliance framework: ${context.clinical_model.compliance}.` : ""}

Analyze the findings below. Write for an executive who understands healthcare operations but not statistics.
Use plain language — never say "AUC", "p-value", "disparity metric", or any other statistical term.
Instead say things like "less likely to receive care", "the gap between groups", "patients may be missed".

Rules:
- No markdown, no bold stars, no bullet symbols.
- Output exactly: one summary paragraph (2-3 sentences, include specific values and group names from the data).
- Then write "Recommended Actions:" followed by exactly 3 numbered items. Each item must start with a short action label, then a colon, then one sentence explaining what to do and why.
- Reference the compliance framework if there are critical findings.
- Never convert patient counts into percentages.
- Never infer or compute new percentages from raw_signal_value.
- Use signal_text verbatim when citing a finding.
- If a finding is a low-sample representation issue, describe it as a data sufficiency risk (not a performance % gap).

DATA:
${JSON.stringify(context, null, 2)}`;

  try {
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        temperature: 0.1,
        messages: [
          { role: "system", content: "You are a clinical AI fairness analyst. Be precise, data-driven, and professional. No markdown." },
          { role: "user", content: prompt },
        ],
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ text: null, error: `OpenAI error: ${res.status}` });
    }

    const json = await res.json();
    const text = json.choices?.[0]?.message?.content?.trim() ?? null;
    return NextResponse.json({ text, error: null });
  } catch (e) {
    return NextResponse.json({ text: null, error: String(e) });
  }
}
