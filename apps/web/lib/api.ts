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
  created_at: string;
  updated_at: string;
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
