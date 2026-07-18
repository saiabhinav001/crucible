// A KPI tile for the dashboard. Kept separate so the dashboard imports one
// primitive; the full design system arrives in Phase 7.
export function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        border: "1px solid #30363d",
        borderRadius: 8,
        padding: "0.9rem 1.1rem",
        minWidth: 150,
        flex: "1 1 150px",
      }}
    >
      <div style={{ color: "#8b949e", fontSize: "0.8rem" }}>{label}</div>
      <div style={{ fontSize: "1.5rem", fontWeight: 600, marginTop: 4 }}>{value}</div>
    </div>
  );
}
