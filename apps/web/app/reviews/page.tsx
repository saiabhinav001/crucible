// Human review queue: runs the agent routed to a human (an ambiguous result).
// Reviewers claim, apply the rubric, and approve/reject via the API.
import { getReviewQueue, NotConfigured } from "@/lib/api";
import { Mono, Panel, StatusBadge, Table } from "../ui";

export const dynamic = "force-dynamic";

export default async function ReviewsPage() {
  let queue;
  try {
    queue = await getReviewQueue();
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
      <h1 style={{ fontSize: "1.5rem", marginBottom: 4 }}>Review queue</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        Runs the agent routed to a human because verification was ambiguous. Claim one, apply the
        rubric (groundedness / provenance / usefulness / uncertainty), then approve or reject.
      </p>

      <Panel title={`${queue.length} awaiting review`}>
        <Table
          headers={["run", "question", "state", "created"]}
          empty="Nothing awaiting review."
          rows={queue.map((item) => [
            <a key="id" href={`/runs/${item.run_id}`} style={{ color: "#58a6ff" }}>
              <Mono>{item.run_id.slice(0, 8)}</Mono>
            </a>,
            <span key="q" style={{ display: "block", maxWidth: 360 }}>
              {item.question}
            </span>,
            <StatusBadge key="s" status={item.review_status ?? "waiting_review"} />,
            <span key="c" style={{ color: "#8b949e", whiteSpace: "nowrap" }}>
              {new Date(item.created_at).toLocaleString()}
            </span>,
          ])}
        />
      </Panel>
    </main>
  );
}
