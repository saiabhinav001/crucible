// Server Component: tenant-scoped data is fetched with the server-side
// credential and rendered to HTML. No API key ever reaches the browser.
import { listDatasets, listVersions, NotConfigured } from "@/lib/api";
import { Mono, Panel, StatusBadge, Table } from "../ui";

export const dynamic = "force-dynamic";

export default async function DatasetsPage() {
  let datasets;
  try {
    datasets = await listDatasets();
  } catch (error) {
    if (error instanceof NotConfigured) {
      return <Setup message={error.message} />;
    }
    throw error;
  }

  const withVersions = await Promise.all(
    datasets.map(async (dataset) => ({
      dataset,
      versions: await listVersions(dataset.id),
    })),
  );

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: 4 }}>Datasets</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        Every version is immutable and identified by the SHA-256 of its bytes.
      </p>

      {withVersions.length === 0 && (
        <Panel title="No datasets yet">
          <Table headers={[]} rows={[]} empty="Upload a CSV through POST /v1/datasets/uploads." />
        </Panel>
      )}

      {withVersions.map(({ dataset, versions }) => (
        <Panel key={dataset.id} title={dataset.name}>
          <Table
            headers={["Version", "Status", "Rows", "Cols", "Content SHA-256", "Schema hash"]}
            empty="No versions."
            rows={versions.map((v) => [
              `v${v.version_no}`,
              <StatusBadge key="s" status={v.status} />,
              v.row_count ?? "—",
              v.column_count ?? "—",
              <Mono key="c">{v.content_sha256?.slice(0, 16) ?? "—"}</Mono>,
              <Mono key="h">{v.schema_hash?.slice(0, 16) ?? "—"}</Mono>,
            ])}
          />
        </Panel>
      ))}
    </main>
  );
}

function Setup({ message }: { message: string }) {
  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1 style={{ fontSize: "1.5rem" }}>Setup required</h1>
      <p style={{ color: "#8b949e" }}>{message}</p>
      <pre
        style={{
          background: "#161b22",
          border: "1px solid #30363d",
          borderRadius: 8,
          padding: "1rem",
          overflowX: "auto",
        }}
      >
        uv run python scripts/bootstrap_org.py --slug demo{"\n"}
        # then set CRUCIBLE_API_KEY in apps/web/.env.local
      </pre>
    </main>
  );
}
