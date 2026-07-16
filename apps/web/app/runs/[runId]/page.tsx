// Run detail (server component): the answer with provenance, the verification
// vector, the node timeline, and the per-step attempts. This is the page that
// makes the agent's reasoning legible — every claim is backed by evidence.
import { getRun, getRunAttempts, getRunEvents, NotConfigured } from "@/lib/api";
import { Mono, Panel, StatusBadge, Table } from "../../ui";

export const dynamic = "force-dynamic";

export default async function RunDetail({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  let run, events, attempts;
  try {
    [run, events, attempts] = await Promise.all([
      getRun(runId),
      getRunEvents(runId),
      getRunAttempts(runId),
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

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <a href="/runs" style={{ color: "#58a6ff", fontSize: "0.85rem" }}>
        ← all runs
      </a>
      <h1 style={{ fontSize: "1.4rem", marginBottom: 4, marginTop: "0.75rem" }}>{run.question}</h1>
      <p style={{ marginTop: 0 }}>
        <StatusBadge status={run.status} /> <Mono>{run.id.slice(0, 8)}</Mono>
      </p>

      {run.answer ? (
        <Panel title="Answer">
          <div style={{ padding: "1rem 1.25rem" }}>
            <p style={{ fontSize: "1.1rem", margin: "0 0 0.5rem" }}>{run.answer.text}</p>
            <p style={{ color: "#8b949e", fontSize: "0.85rem", margin: 0 }}>
              {run.answer.limitations}
            </p>
            <dl style={{ color: "#8b949e", fontSize: "0.85rem", marginTop: "1rem" }}>
              <div>operation: <Mono>{run.answer.provenance.operation}</Mono></div>
              <div>columns used: <Mono>{run.answer.provenance.columns_used.join(", ") || "—"}</Mono></div>
              <div>code sha256: <Mono>{run.answer.provenance.code_sha256.slice(0, 16)}</Mono></div>
              <div>attempts: {run.answer.provenance.attempt_count}</div>
              <div>executor: <Mono>{run.answer.provenance.executor_backend}</Mono> {run.answer.provenance.image_ref && <Mono>({run.answer.provenance.image_ref})</Mono>}</div>
            </dl>
          </div>
        </Panel>
      ) : (
        <Panel title="Outcome">
          <p style={{ padding: "1rem 1.25rem", margin: 0, color: "#8b949e" }}>
            {run.terminal_detail ?? "No answer was produced."}
          </p>
        </Panel>
      )}

      {run.verification && (
        <Panel title="Verification">
          <Table
            headers={["check", "result"]}
            empty="—"
            rows={Object.entries(run.verification)
              .filter(([k]) => k !== "reasons")
              .map(([k, v]) => [k, <Mono key={k}>{String(v)}</Mono>])}
          />
        </Panel>
      )}

      <Panel title="Node timeline">
        <Table
          headers={["#", "event", "node"]}
          empty="No events yet."
          rows={events.map((e) => [
            e.sequence_no,
            e.event_type,
            <Mono key="n">{String(e.payload.node ?? e.payload.status ?? "")}</Mono>,
          ])}
        />
      </Panel>

      <Panel title="Attempts">
        <Table
          headers={["#", "kind", "model", "exit", "ms", "code"]}
          empty="No attempts."
          rows={attempts.map((a) => [
            a.attempt_no,
            a.kind,
            <Mono key="m">{a.model_id ?? "—"}</Mono>,
            a.exit_class ?? "—",
            a.duration_ms ?? "—",
            <Mono key="c">{a.source_sha256?.slice(0, 12) ?? "—"}</Mono>,
          ])}
        />
      </Panel>
    </main>
  );
}
