import type {
  ApiErrorBody,
  AuditEvent,
  Dataset,
  Decision,
  MatchStatus,
  Profile,
  ReviewEvent,
  Run,
} from "./types";
import { translateApiMessage } from "./presentation";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly correlationId: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let body: ApiErrorBody | undefined;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = undefined;
    }
    throw new ApiError(
      translateApiMessage(
        body?.error.message ??
          `A requisição falhou com status ${response.status}`,
      ),
      body?.error.code ?? "http_error",
      body?.correlation_id ??
        response.headers.get("X-Correlation-Id") ??
        "unknown",
      response.status,
    );
  }
  return (await response.json()) as T;
}

export const api = {
  datasets: () => request<Dataset[]>("/api/v1/datasets"),
  dataset: (id: string) => request<Dataset>(`/api/v1/datasets/${id}`),
  upload: async (side: "A" | "B", file: File) => {
    const form = new FormData();
    form.append("side", side);
    form.append("file", file);
    return request<Dataset>("/api/v1/datasets", { method: "POST", body: form });
  },
  mapDataset: (
    id: string,
    mapping: {
      amount: string;
      booking_date: string;
      currency: string | null;
      transaction_id: string | null;
      source_record_id: string | null;
      document: string | null;
      reference: string | null;
      default_currency: string;
    },
  ) =>
    request<Dataset>(`/api/v1/datasets/${id}/mapping`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(mapping),
    }),
  profiles: () => request<Profile[]>("/api/v1/profiles"),
  runs: () => request<Run[]>("/api/v1/runs"),
  run: (id: string) => request<Run>(`/api/v1/runs/${id}`),
  startRun: (datasetAId: string, datasetBId: string, profile: Profile) =>
    request<Run>("/api/v1/runs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Idempotency-Key": crypto.randomUUID(),
        "X-Correlation-Id": crypto.randomUUID(),
      },
      body: JSON.stringify({
        dataset_a_id: datasetAId,
        dataset_b_id: datasetBId,
        profile_id: profile.rule_id,
        profile_version: profile.version,
      }),
    }),
  decisions: (runId: string, status?: MatchStatus) =>
    request<Decision[]>(
      `/api/v1/runs/${runId}/decisions${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  audit: (runId: string) =>
    request<AuditEvent[]>(`/api/v1/runs/${runId}/audit`),
  reviews: (runId: string) =>
    request<ReviewEvent[]>(`/api/v1/runs/${runId}/reviews`),
  review: (
    runId: string,
    decisionId: string,
    action: "APPROVE" | "REJECT",
    reason: string,
  ) =>
    request<{ event_id: string }>(
      `/api/v1/runs/${runId}/decisions/${decisionId}/reviews`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Actor-Id": "demo-analyst",
          "X-Idempotency-Key": crypto.randomUUID(),
        },
        body: JSON.stringify({ action, reason }),
      },
    ),
  exportReport: async (runId: string) => {
    const response = await fetch(`/api/v1/runs/${runId}/exports`, {
      method: "POST",
      headers: {
        "X-Actor-Id": "demo-analyst",
        "X-Idempotency-Key": crypto.randomUUID(),
      },
    });
    if (!response.ok)
      throw new ApiError(
        "Não foi possível exportar a planilha",
        "export_failed",
        "unknown",
        response.status,
      );
    return response.blob();
  },
};
