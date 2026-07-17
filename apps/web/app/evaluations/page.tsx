// Evaluations: versioned suites and the latest committed experiment comparison.
import { listSuites, loadExampleReport } from "@/lib/evals";
import { Mono, Panel, StatusBadge, Table } from "../ui";

export const dynamic = "force-dynamic";

const GATE_COLORS: Record<string, string> = { pass: "#3fb950", flag: "#d29922", block: "#f85149" };

export default function EvaluationsPage() {
  const suites = listSuites();
  const report = loadExampleReport();

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: 4 }}>Evaluations</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        Versioned suites scored against trusted oracles; candidates gated against a frozen baseline
        with a paired bootstrap confidence interval.
      </p>

      <Panel title="Suites">
        <Table
          headers={["suite", "version", "purpose", "fixture", "cases", "smoke"]}
          empty="No suites found."
          rows={suites.map((s) => [
            s.id,
            s.version,
            <StatusBadge key="p" status={s.purpose} />,
            <Mono key="f">{s.fixture}</Mono>,
            s.case_count,
            s.smoke_count,
          ])}
        />
      </Panel>

      {report ? (
        <ExperimentComparison report={report} />
      ) : (
        <Panel title="Latest comparison">
          <p style={{ padding: "1rem 1.25rem", margin: 0, color: "#8b949e" }}>
            No committed report found. Generate one with{" "}
            <Mono>python -m crucible.evaluation run --suite … --baseline …</Mono>.
          </p>
        </Panel>
      )}
    </main>
  );
}

function ExperimentComparison({ report }: { report: ReturnType<typeof loadExampleReport> }) {
  if (!report) return null;
  const gate = report.gate;
  const color = GATE_COLORS[gate.status] ?? "#8b949e";
  return (
    <>
      <section
        style={{
          marginTop: "2rem",
          border: `1px solid ${color}55`,
          background: `${color}14`,
          borderRadius: 8,
          padding: "1rem 1.25rem",
        }}
      >
        <h2 style={{ margin: "0 0 0.5rem", fontSize: "1.05rem" }}>
          Experiment comparison — gate <span style={{ color }}>{gate.status.toUpperCase()}</span>
        </h2>
        <p style={{ margin: 0, color: "#8b949e", fontSize: "0.9rem" }}>
          candidate <Mono>{report.candidate.config_id}</Mono> (acc {report.candidate.accuracy}) vs
          baseline <Mono>{report.baseline.config_id}</Mono> (acc {report.baseline.accuracy}) · paired
          Δ <strong>{gate.delta}</strong>, 95% CI [{gate.ci_lo}, {gate.ci_hi}], tolerance{" "}
          {gate.tolerance}
        </p>
        <p style={{ margin: "0.5rem 0 0", color: "#8b949e", fontSize: "0.8rem" }}>
          git <Mono>{report.git_sha}</Mono> · scorer <Mono>{report.scorer_version}</Mono> · report{" "}
          <Mono>{report.content_sha256.slice(0, 16)}</Mono>
        </p>
      </section>

      <Panel title="Per-case deltas">
        <Table
          headers={["case", "tags", "base", "cand", "Δ", "terminal", "value", "ms", "policy"]}
          empty="No cases."
          rows={report.cases.map((c) => [
            <Mono key="id">{c.id}</Mono>,
            c.tags.join(", "),
            mark(c.baseline_correct),
            mark(c.candidate_correct),
            c.delta ?? "·",
            c.candidate.terminal,
            String(c.candidate.value ?? "—"),
            c.candidate.latency_ms,
            c.policy_ok ? "ok" : `FAIL:${c.policy_failures.join(",")}`,
          ])}
        />
      </Panel>
    </>
  );
}

function mark(v: boolean | null): string {
  return v === null ? "·" : v ? "✓" : "✗";
}
