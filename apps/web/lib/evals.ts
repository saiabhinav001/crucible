// Server-only readers for committed evaluation evidence.
//
// Phase 5 exposes the file-based report (the CI-gated artifact). The live eval
// service + score DB is a Phase 7 dashboard deliverable; here we read the
// committed example report and suite manifests from the repo so the pages show
// real evidence in local development.
import "server-only";

import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import yaml from "js-yaml";

function repoRoot(): string {
  // `pnpm --filter web dev` runs from apps/web; the repo root is two levels up.
  return join(process.cwd(), "..", "..");
}

export type EvalReport = {
  generated_at: string;
  git_sha: string;
  scorer_version: string;
  suite: { id: string; version: string; hash: string };
  baseline: { config_id: string; config_hash: string; accuracy: number };
  candidate: { config_id: string; config_hash: string; accuracy: number };
  gate: {
    status: string;
    delta: number;
    ci_lo: number;
    ci_hi: number;
    tolerance: number;
    reasons: string[];
    correctness_regressions: string[];
    policy_regressions: string[];
  };
  efficiency: { candidate_total_latency_ms: number; candidate_total_cost_usd: number; cases: number };
  failure_taxonomy: Record<string, number>;
  cases: Array<{
    id: string;
    tags: string[];
    baseline_correct: boolean | null;
    candidate_correct: boolean;
    delta: number | null;
    policy_ok: boolean;
    policy_failures: string[];
    candidate: { terminal: string; value: unknown; latency_ms: number; exit_class: string | null };
    detail: string;
  }>;
  content_sha256: string;
};

export type SuiteSummary = {
  id: string;
  version: string;
  purpose: string;
  status: string;
  fixture: string;
  case_count: number;
  smoke_count: number;
};

export function loadExampleReport(): EvalReport | null {
  try {
    const path = join(repoRoot(), "evals", "reports", "examples", "core-comparison.json");
    return JSON.parse(readFileSync(path, "utf-8")) as EvalReport;
  } catch {
    return null;
  }
}

export function listSuites(): SuiteSummary[] {
  try {
    const dir = join(repoRoot(), "evals", "suites");
    return readdirSync(dir)
      .filter((f) => f.endsWith(".yaml") || f.endsWith(".yml"))
      .map((f) => {
        const doc = yaml.load(readFileSync(join(dir, f), "utf-8")) as Record<string, unknown>;
        const cases = (doc.cases as unknown[]) ?? [];
        const smoke = (doc.smoke as unknown[]) ?? [];
        return {
          id: String(doc.id ?? f),
          version: String(doc.version ?? ""),
          purpose: String(doc.purpose ?? ""),
          status: String(doc.status ?? ""),
          fixture: String(doc.fixture ?? ""),
          case_count: cases.length,
          smoke_count: smoke.length,
        };
      });
  } catch {
    return [];
  }
}
