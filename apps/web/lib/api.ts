// Server-only API client.
//
// The API key lives in a server-side env var and is used exclusively from
// Server Components / route handlers. It is never shipped to the browser —
// a credential in client JS is a credential in the user's clipboard.
import "server-only";

const API_URL = process.env.CRUCIBLE_API_URL ?? "http://localhost:8100";
const API_KEY = process.env.CRUCIBLE_API_KEY ?? "";

export type Dataset = {
  id: string;
  name: string;
  created_at: string;
};

export type DatasetVersion = {
  id: string;
  dataset_id: string;
  version_no: number;
  status: "awaiting_upload" | "pending_profile" | "ready" | "invalid";
  content_sha256: string | null;
  schema_hash: string | null;
  row_count: number | null;
  column_count: number | null;
  size_bytes: number | null;
  invalid_reason: string | null;
  created_at: string | null;
};

export type Run = {
  id: string;
  dataset_version_id: string;
  question: string;
  status: string;
  terminal_detail: string | null;
  failure_category: string | null;
  cancel_requested: boolean;
  answer: {
    value: unknown;
    text: string;
    limitations: string;
    provenance: {
      operation: string;
      columns_used: string[];
      code_sha256: string;
      attempt_count: number;
      executor_backend: string;
      image_ref: string;
      dataset_sha256: string | null;
    };
  } | null;
  verification: Record<string, unknown> | null;
  config_manifest: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RunEvent = {
  sequence_no: number;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type Attempt = {
  attempt_no: number;
  kind: string;
  sequence_no: number;
  payload: Record<string, unknown>;
  model_provider: string | null;
  model_id: string | null;
  exit_class: string | null;
  failure_category: string | null;
  duration_ms: number | null;
  source_sha256: string | null;
  created_at: string;
};

export class NotConfigured extends Error {}

async function get<T>(path: string): Promise<T> {
  if (!API_KEY) {
    throw new NotConfigured(
      "CRUCIBLE_API_KEY is not set. Run scripts/bootstrap_org.py to mint one.",
    );
  }
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${API_KEY}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`API ${path} failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export const listDatasets = () => get<Dataset[]>("/v1/datasets");
export const listVersions = (datasetId: string) =>
  get<DatasetVersion[]>(`/v1/datasets/${datasetId}/versions`);
export const listRuns = () => get<Run[]>("/v1/runs?limit=50");
export const getRun = (runId: string) => get<Run>(`/v1/runs/${runId}`);
export const getRunEvents = (runId: string) => get<RunEvent[]>(`/v1/runs/${runId}/events`);
export const getRunAttempts = (runId: string) => get<Attempt[]>(`/v1/runs/${runId}/attempts`);
