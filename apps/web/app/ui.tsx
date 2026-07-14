// Minimal shared primitives. The real design system arrives in Phase 7;
// these exist so Phase 2's pages can show real data without inventing one.
import type { ReactNode } from "react";

const STATUS_COLORS: Record<string, string> = {
  ready: "#3fb950",
  answered: "#3fb950",
  pending_profile: "#d29922",
  awaiting_upload: "#8b949e",
  queued: "#8b949e",
  running: "#58a6ff",
  waiting_review: "#d29922",
  abstained: "#d29922",
  needs_human_review: "#d29922",
  invalid: "#f85149",
  policy_denied: "#f85149",
  budget_exhausted: "#f85149",
  cancelled: "#8b949e",
};

export function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] ?? "#8b949e";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        border: `1px solid ${color}55`,
        background: `${color}18`,
        color,
        borderRadius: 999,
        padding: "2px 10px",
        fontSize: "0.8rem",
        whiteSpace: "nowrap",
      }}
    >
      {/* Status is never conveyed by color alone (WCAG 1.4.1). */}
      <span aria-hidden style={{ width: 6, height: 6, borderRadius: 999, background: color }} />
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={{ marginTop: "2rem" }}>
      <h2 style={{ fontSize: "1.05rem", marginBottom: "0.75rem" }}>{title}</h2>
      <div
        style={{
          border: "1px solid #30363d",
          borderRadius: 8,
          overflowX: "auto", // wide tables scroll inside the panel, not the page
        }}
      >
        {children}
      </div>
    </section>
  );
}

export function Table({
  headers,
  rows,
  empty,
}: {
  headers: string[];
  rows: ReactNode[][];
  empty: string;
}) {
  if (rows.length === 0) {
    return <p style={{ padding: "1.25rem", color: "#8b949e", margin: 0 }}>{empty}</p>;
  }
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
      <thead>
        <tr>
          {headers.map((h) => (
            <th
              key={h}
              scope="col"
              style={{
                textAlign: "left",
                padding: "0.7rem 1rem",
                borderBottom: "1px solid #30363d",
                color: "#8b949e",
                fontWeight: 500,
                whiteSpace: "nowrap",
              }}
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((cells, i) => (
          <tr key={i}>
            {cells.map((cell, j) => (
              <td
                key={j}
                style={{
                  padding: "0.7rem 1rem",
                  borderBottom: i === rows.length - 1 ? "none" : "1px solid #21262d",
                }}
              >
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Mono({ children }: { children: ReactNode }) {
  return (
    <code style={{ fontFamily: "ui-monospace, monospace", fontSize: "0.85em", color: "#8b949e" }}>
      {children}
    </code>
  );
}
