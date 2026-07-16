import { listRuns, NotConfigured } from "@/lib/api";
import { Mono, Panel, StatusBadge, Table } from "../ui";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  let runs;
  try {
    runs = await listRuns();
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

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: 4 }}>Runs</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        Durable async jobs. The agent workflow itself lands in Phase 4 — until then a run is
        claimed and terminates as <em>abstained</em> rather than inventing an answer.
      </p>

      <Panel title={`${runs.length} run${runs.length === 1 ? "" : "s"}`}>
        <Table
          headers={["Run", "Question", "Status", "Outcome", "Created"]}
          empty="No runs yet. POST /v1/runs with a ready dataset version."
          rows={runs.map((run) => [
            <a key="id" href={`/runs/${run.id}`} style={{ color: "#58a6ff" }}>
              <Mono>{run.id.slice(0, 8)}</Mono>
            </a>,
            <span key="q" style={{ display: "block", maxWidth: 320 }}>
              {run.question}
            </span>,
            <StatusBadge key="s" status={run.status} />,
            <span key="d" style={{ color: "#8b949e" }}>
              {run.failure_category ?? run.terminal_detail?.slice(0, 60) ?? "—"}
            </span>,
            <span key="c" style={{ color: "#8b949e", whiteSpace: "nowrap" }}>
              {new Date(run.created_at).toLocaleString()}
            </span>,
          ])}
        />
      </Panel>
    </main>
  );
}
