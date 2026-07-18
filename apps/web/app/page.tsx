"use client";

// Phase 1 shell: proves the web workspace builds and can reach the API's
// health path. The product dashboard is a Phase 7 deliverable.

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100";

type VersionInfo = {
  git_sha: string;
  version: string;
  profile: string;
  built_at: string;
};

export default function Home() {
  const [alive, setAlive] = useState<"checking" | "up" | "down">("checking");
  const [version, setVersion] = useState<VersionInfo | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function probe() {
      try {
        const health = await fetch(`${API_URL}/healthz`, { cache: "no-store" });
        if (cancelled) return;
        setAlive(health.ok ? "up" : "down");
        if (health.ok) {
          const v = await fetch(`${API_URL}/version`, { cache: "no-store" });
          if (!cancelled && v.ok) setVersion((await v.json()) as VersionInfo);
        }
      } catch {
        if (!cancelled) setAlive("down");
      }
    }
    void probe();
    return () => {
      cancelled = true;
    };
  }, []);

  const dot =
    alive === "up" ? "#3fb950" : alive === "down" ? "#f85149" : "#d29922";

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "4rem 1.5rem" }}>
      <h1 style={{ fontSize: "1.75rem", marginBottom: "0.25rem" }}>Crucible</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        Evaluation and reliability platform for LLM agents — Phase 1 shell.
      </p>

      <section
        style={{
          border: "1px solid #30363d",
          borderRadius: 8,
          padding: "1rem 1.25rem",
          marginTop: "2rem",
        }}
      >
        <p style={{ margin: 0 }}>
          <span
            aria-hidden
            style={{
              display: "inline-block",
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: dot,
              marginRight: 8,
            }}
          />
          API ({API_URL}):{" "}
          {alive === "checking" ? "checking…" : alive === "up" ? "alive" : "unreachable"}
        </p>
        {version && (
          <dl style={{ color: "#8b949e", fontSize: "0.9rem", marginBottom: 0 }}>
            <div>
              <dt style={{ display: "inline" }}>build&nbsp;</dt>
              <dd style={{ display: "inline", margin: 0 }}>
                {version.git_sha} · v{version.version} · {version.profile}
              </dd>
            </div>
          </dl>
        )}
      </section>

      <nav style={{ marginTop: "2rem", display: "flex", gap: "1.25rem", flexWrap: "wrap" }}>
        <a style={{ color: "#58a6ff" }} href="/dashboard">
          Reliability
        </a>
        <a style={{ color: "#58a6ff" }} href="/datasets">
          Datasets
        </a>
        <a style={{ color: "#58a6ff" }} href="/runs">
          Runs
        </a>
        <a style={{ color: "#58a6ff" }} href="/reviews">
          Reviews
        </a>
        <a style={{ color: "#58a6ff" }} href="/evaluations">
          Evaluations
        </a>
        <a style={{ color: "#58a6ff" }} href={`${API_URL}/docs`}>
          API docs
        </a>
      </nav>
    </main>
  );
}
