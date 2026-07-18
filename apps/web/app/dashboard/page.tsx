// Reliability dashboard: terminal-state distribution, failure taxonomy, trace
// completeness, cost/latency, and firing alerts — the operating view for the
// agent's health (master plan §11.2).
import {
  getAlerts,
  getCostLatency,
  getReliability,
  NotConfigured,
  type AlertRow,
} from "@/lib/api";
import { MetricCard } from "../ui-metrics";
import { Mono, Panel, StatusBadge, Table } from "../ui";

export const dynamic = "force-dynamic";

const SEV_COLOR: Record<string, string> = { sev1: "#f85149", sev2: "#d29922", sev3: "#8b949e" };

export default async function DashboardPage() {
  let reliability, cost, alerts;
  try {
    [reliability, cost, alerts] = await Promise.all([
      getReliability(),
      getCostLatency(),
      getAlerts(),
    ]);
  } catch (error) {
    if (error instanceof NotConfigured) {
      return (
        <main style={{ maxWidth: 720, margin: "0 auto", padding: "3rem 1.5rem" }}>
          <h1 style={{ fontSize: "1.5rem" }}>Setup required</h1>
          <p style={{ color: "#8b949e" }}>{error.message}</p>
        </main>
      );
    }
    throw error;
  }

  const firing = alerts.filter((a) => a.firing);

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: 4 }}>Reliability</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        Every terminal run contributes its trace, cost, latency, versions, and failure category.
      </p>

      {firing.length > 0 && (
        <Panel title={`Firing alerts (${firing.length})`}>
          <Table
            headers={["severity", "rule", "detail", "runbook"]}
            empty=""
            rows={firing.map((a: AlertRow) => [
              <span key="s" style={{ color: SEV_COLOR[a.severity] ?? "#8b949e", fontWeight: 600 }}>
                {a.severity.toUpperCase()}
              </span>,
              a.rule_id,
              a.detail,
              <Mono key="r">{a.runbook}</Mono>,
            ])}
          />
        </Panel>
      )}

      <section style={{ display: "flex", flexWrap: "wrap", gap: "1rem", marginTop: "2rem" }}>
        <MetricCard label="Terminal runs" value={String(reliability.terminal)} />
        <MetricCard
          label="Technical completion"
          value={pct(reliability.technical_completion_rate)}
        />
        <MetricCard label="Trace completeness" value={pct(reliability.trace_completeness)} />
        <MetricCard label="Answered" value={String(reliability.answered)} />
        <MetricCard label="Abstained" value={String(reliability.abstained)} />
        <MetricCard label="p95 latency" value={`${cost.latency_p95_ms} ms`} />
        <MetricCard label="Total cost" value={`$${cost.total_cost_usd}`} />
        <MetricCard
          label="Cost attribution"
          value={pct(cost.cost_attribution_completeness)}
        />
      </section>

      <Panel title="Terminal states">
        <Table
          headers={["state", "count"]}
          empty="No terminal runs yet."
          rows={Object.entries(reliability.terminal_states).map(([s, n]) => [
            <StatusBadge key="s" status={s} />,
            n,
          ])}
        />
      </Panel>

      <Panel title="Failure taxonomy">
        <Table
          headers={["category", "count"]}
          empty="No failures recorded."
          rows={Object.entries(reliability.failure_taxonomy).map(([c, n]) => [
            <Mono key="c">{c}</Mono>,
            n,
          ])}
        />
      </Panel>
    </main>
  );
}

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}
