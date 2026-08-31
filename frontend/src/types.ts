export type MatchStatus =
  | "MATCHED"
  | "UNMATCHED"
  | "AMBIGUOUS"
  | "DUPLICATE"
  | "MANUAL_REVIEW"
  | "SPLIT_MATCHED";

export type RunStatus =
  "PENDING" | "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";

export interface Dataset {
  dataset_id: string;
  name: string;
  side: "A" | "B";
  fingerprint: string;
  headers: string[];
  row_count: number;
  byte_size: number;
  is_mapped: boolean;
  created_at: string;
}

export interface Profile {
  rule_id: string;
  version: string;
  label: string;
  amount_tolerance: string;
  date_tolerance_days: number;
  split_enabled: boolean;
}

export interface Run {
  run_id: string;
  dataset_a_id: string;
  dataset_b_id: string;
  dataset_a_fingerprint: string;
  dataset_b_fingerprint: string;
  rule_id: string;
  rule_version: string;
  normalization_version: string;
  status: RunStatus;
  progress_percent: number;
  counts: Record<MatchStatus, number>;
  created_at: string;
  updated_at: string;
  correlation_id: string;
  error_code: string | null;
}

export interface Decision {
  decision_id: string;
  status: MatchStatus;
  source_ids: string[];
  target_ids: string[];
  rule_id: string | null;
  rule_version: string | null;
  confidence: string | null;
  explanation: string;
  evidence: string[];
}

export interface AuditEvent {
  event_id: string;
  event_type: string;
  actor_id: string;
  detail: string;
  created_at: string;
}

export interface ReviewEvent {
  event_id: string;
  run_id: string;
  decision_id: string;
  action: "APPROVE" | "REJECT";
  actor_id: string;
  reason: string;
  created_at: string;
}

export interface ApiErrorBody {
  error: { code: string; message: string; issues?: unknown[] };
  correlation_id: string;
}
