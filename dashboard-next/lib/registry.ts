/**
 * Clinical model registry.
 *
 * Maps a model name (or prefix) to the clinical context a CMIO
 * needs to understand what the model does, who it serves, and
 * which regulatory frameworks apply.
 *
 * To add a new model: extend REGISTRY with its exact name or a
 * unique prefix. Defaults are used for unrecognised models.
 */

export interface ModelContext {
  /** Human name shown in the UI header. */
  useCase: string;
  /** Verb phrase describing what a positive prediction means.
   *  e.g. "flagged for early sepsis intervention" */
  outcome: string;
  /** Clinical population the model operates on. */
  population: string;
  /** Hospital department / care setting. */
  department: string;
  /** Estimated number of patients scored per month (for impact math). */
  patientsPerMonth: number;
  /**
   * Regulatory or compliance programme this model falls under.
   * Shown on critical alerts to anchor urgency.
   */
  complianceNote: string;
}

// ── Per-model definitions ────────────────────────────────────────────────────
const REGISTRY: Record<string, ModelContext> = {
  monitor_ingest_smoke: {
    useCase: "Sepsis Risk Screening",
    outcome: "flagged for early sepsis intervention",
    population: "Adult ICU Patients",
    department: "Critical Care",
    patientsPerMonth: 840,
    complianceNote: "CMS AI Transparency & Bias Rule (2025)",
  },
  sepsis: {
    useCase: "Sepsis Risk Screening",
    outcome: "flagged for early sepsis intervention",
    population: "Adult ICU Patients",
    department: "Critical Care",
    patientsPerMonth: 840,
    complianceNote: "CMS AI Transparency & Bias Rule (2025)",
  },
  readmission: {
    useCase: "30-Day Readmission Prediction",
    outcome: "predicted for readmission within 30 days",
    population: "Adult Inpatients (All Wards)",
    department: "Hospital Medicine",
    patientsPerMonth: 2400,
    complianceNote: "CMS Hospital Readmissions Reduction Program",
  },
  deterioration: {
    useCase: "Clinical Deterioration Early Warning",
    outcome: "escalated to rapid response",
    population: "Adult Inpatients (Step-Down & General Med)",
    department: "Patient Safety",
    patientsPerMonth: 1600,
    complianceNote: "The Joint Commission NPSG 16.01.01",
  },
};

const DEFAULT_CONTEXT: ModelContext = {
  useCase: "Clinical Risk Model",
  outcome: "flagged as high risk",
  population: "General Inpatient",
  department: "Clinical AI Programme",
  patientsPerMonth: 1000,
  complianceNote: "CMS AI Transparency & Bias Rule (2025)",
};

// ── Lookup ───────────────────────────────────────────────────────────────────
/**
 * Resolves a ModelContext for the given model.
 *
 * Priority (highest → lowest):
 *  1. Fields present in `dbMetadata.clinical` (written by the worker when
 *     WorkerConfig.clinical_context is set).
 *  2. Matching entry in the local REGISTRY (prefix match on model_name).
 *  3. DEFAULT_CONTEXT.
 *
 * Any field missing from the DB is filled in by the registry / default,
 * so partial DB metadata is fine.
 */
export function getModelContext(
  modelName: string,
  dbMetadata?: Record<string, unknown> | null,
): ModelContext {
  // Step 1: resolve base from local registry
  let base: ModelContext = DEFAULT_CONTEXT;
  if (REGISTRY[modelName]) {
    base = REGISTRY[modelName];
  } else {
    for (const key of Object.keys(REGISTRY)) {
      if (modelName.toLowerCase().startsWith(key.toLowerCase())) {
        base = REGISTRY[key];
        break;
      }
    }
  }

  // Step 2: overlay any fields present in audit_runs.metadata.clinical
  const clinical = dbMetadata?.clinical as Partial<ModelContext> | undefined;
  if (!clinical) return base;

  return {
    useCase:          (clinical.useCase          as string)  || base.useCase,
    outcome:          (clinical.outcome          as string)  || base.outcome,
    population:       (clinical.population       as string)  || base.population,
    department:       (clinical.department       as string)  || base.department,
    patientsPerMonth: (clinical.patientsPerMonth as number)  || base.patientsPerMonth,
    complianceNote:   (clinical.complianceNote   as string)  || base.complianceNote,
  };
}

/**
 * Estimate how many patients in the scored window may be affected by an alert.
 * Uses the actual window_size from the audit run (real data) rather than any
 * hardcoded fraction.  Returns null when the signal is too small to be meaningful.
 *
 * @param windowSize  audit.window_size — number of records scored in this run
 * @param signalValue alert.signal_value — the raw gap value (0-1 scale)
 */
export function estimateImpact(
  windowSize: number | null | undefined,
  signalValue: number | null,
  dimension?: string,
): string | null {
  if (signalValue === null || signalValue === undefined || !windowSize || windowSize < 1) return null;
  if (!dimension) return null;

  // Only convert to "patients affected" for dimensions where signal_value is a
  // gap-like fraction in [0,1]. Other dimensions (e.g. Representation count,
  // Feature Drift KS statistic, Intersectionality score) should not use this.
  const impactEligible = new Set([
    "Demographic Fairness",
    "Threshold Parity",
    "False Negative Gap",
    "Calibration Fairness",
  ]);
  if (!impactEligible.has(dimension)) return null;

  const frac = Math.abs(Number(signalValue));
  if (!Number.isFinite(frac) || frac <= 0) return null;
  const bounded = Math.min(1, frac);
  const missed = Math.min(windowSize, Math.round(bounded * windowSize));
  if (missed < 1) return null;
  return `~${missed} of ${windowSize.toLocaleString()} patients`;
}
