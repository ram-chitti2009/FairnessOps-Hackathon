export interface AuditRun {
  run_id: string;
  created_at: string;
  model_name: string;
  model_version: string | null;
  window_size: number;
  status: string;
  metric_count: number;
  alert_count: number;
  dimensions: string[];
  /** JSON blob written by the worker. Contains a "clinical" key with ModelContext fields. */
  metadata?: Record<string, unknown> | null;
}

export interface MetricRow {
  id?: string;
  run_id: string;
  dimension: string;
  attribute: string;
  subgroup: string | null;
  metric_name: string;
  metric_value: number | null;
  created_at?: string;
  metadata?: Record<string, unknown>;
}

export interface AlertRow {
  id?: string;
  run_id: string;
  dimension: string;
  attribute: string;
  subgroup: string | null;
  severity: "RED" | "YELLOW" | "GREEN" | "INSUFFICIENT_DATA";
  message: string;
  signal_value: number | null;
  threshold_config?: Record<string, unknown>;
  created_at?: string;
}

export interface MetricsResponse {
  items: MetricRow[];
}

export interface AlertsResponse {
  items: AlertRow[];
}

export type SeverityLevel = "RED" | "YELLOW" | "GREEN" | "INSUFFICIENT_DATA";
