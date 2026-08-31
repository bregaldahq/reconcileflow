import type { Dataset, Decision, Run } from "../types";

export const datasetA: Dataset = {
  dataset_id: "dataset-a",
  name: "ledger.csv",
  side: "A",
  fingerprint: "a".repeat(64),
  headers: ["id", "amount", "currency", "date", "document", "reference"],
  row_count: 3,
  byte_size: 200,
  is_mapped: true,
  created_at: "2026-01-01T12:00:00Z",
};

export const datasetB: Dataset = {
  ...datasetA,
  dataset_id: "dataset-b",
  name: "bank.csv",
  side: "B",
  fingerprint: "b".repeat(64),
};

export const run: Run = {
  run_id: "run-demo-001",
  dataset_a_id: "dataset-a",
  dataset_b_id: "dataset-b",
  dataset_a_fingerprint: "a".repeat(64),
  dataset_b_fingerprint: "b".repeat(64),
  rule_id: "standard",
  rule_version: "1",
  normalization_version: "br-v1",
  status: "COMPLETED",
  progress_percent: 100,
  counts: {
    MATCHED: 1,
    SPLIT_MATCHED: 1,
    UNMATCHED: 1,
    AMBIGUOUS: 1,
    DUPLICATE: 0,
    MANUAL_REVIEW: 0,
  },
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:01Z",
  correlation_id: "corr-1",
  error_code: null,
};

export const ambiguousDecision: Decision = {
  decision_id: "decision-ambiguous",
  status: "AMBIGUOUS",
  source_ids: ["dataset-a:A1"],
  target_ids: ["dataset-b:B1", "dataset-b:B2"],
  rule_id: "amount_date_tolerance",
  rule_version: "1",
  confidence: "0.900000",
  explanation: "Multiple equally valid candidates require manual review.",
  evidence: [
    "candidate sources=dataset-a:A1 targets=dataset-b:B1",
    "candidate sources=dataset-a:A1 targets=dataset-b:B2",
  ],
};
