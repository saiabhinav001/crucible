# Crucible

**An open-source evaluation and reliability platform for LLM agents**, with a
self-correcting data-analysis agent as its bounded reference workload.

> A language-model agent should be trusted only to the degree that its behavior is
> **measured, reproducible, observable, bounded, and independently checked.**

Crucible's differentiator is not the agent loop — it is the evidence around the loop:
executable offline evaluation, versioned experiment comparisons, production tracing,
constrained execution, regression gates, and a stable failure taxonomy.

## Status: Phase 1 complete (repository foundation + reproducible local platform)

Phase 0 defined the workload, threat boundary, and metric contract; Phase 1 delivers
the deterministic developer platform (see the [backlog](docs/product/backlog.md) for
the six-month plan).

```bash
uv sync --dev && docker compose up -d          # full local stack
uv run alembic -c packages/db/alembic.ini upgrade head
make check                                     # or: pwsh scripts/check.ps1
```

- **Monorepo:** uv + pnpm workspaces with locked dependencies; `packages/domain` and
  `packages/application` are framework-free, enforced by import-linter contracts in CI.
- **Services:** FastAPI gateway (`/healthz`, `/readyz`, `/version`, OpenAPI) and an arq
  worker, both containerized from `uv.lock`; typed settings fail fast on unsafe
  staging/production configuration.
- **Local stack:** Postgres 17 + pgvector, Redis, MinIO, OTel collector via Compose
  (host ports offset: API 8100, Postgres 55432, web 3100).
- **First migration:** Alembic `0001` with offline-SQL and live-database tests.
- **CI:** `pr-validate` (format/lint/mypy/import-boundaries/unit/integration/web/docker)
  and `security` (Gitleaks + pip-audit) workflows.

See [docs/operations/local-development.md](docs/operations/local-development.md).

| Artifact | Location |
|---|---|
| Product charter (workload, non-goals, first release gate) | [docs/product/prd.md](docs/product/prd.md) |
| Metric contract (scorer hierarchy, gates vs trends, δ policy) | [docs/evaluation/metric-contract.md](docs/evaluation/metric-contract.md) |
| Failure taxonomy | [docs/evaluation/failure-taxonomy.md](docs/evaluation/failure-taxonomy.md) |
| Threat model (boundary × control × test matrix) | [docs/security/threat-model.md](docs/security/threat-model.md) |
| C4 context + plane separation | [docs/architecture/c4-context.md](docs/architecture/c4-context.md) |
| ADR-001 … ADR-007 | [docs/adr/](docs/adr/) |
| Risk register | [docs/product/risk-register.md](docs/product/risk-register.md) |
| Six-month backlog | [docs/product/backlog.md](docs/product/backlog.md) |
| **10-case hand-verified seed suite** | [evals/](evals/README.md) |

## Try the seed suite now

```bash
python evals/references/run_all.py
```

Ten reference calculators (pure stdlib, no dependencies) compute golden answers over a
fully synthetic 40-row retail fixture, including deliberate edge cases: missing
discounts, an unknown region, tie-margin checks, and an unanswerable question whose
correct outcome is abstention. High-value cases carry an independently written second
calculation. Every case pins the fixture's SHA-256 and its canonicalization contract.

## Non-negotiable principles

1. Correctness is not a vibe — executable ground truth first.
2. The serving plane and evaluation plane are different products.
3. No model certifies itself.
4. Generated code is hostile until contained.
5. Version every behavior-changing input.
6. Do not overbuild before the scorecard works.

## License & security

License and `SECURITY.md` land in Phase 1 with the repository foundation. All fixture
data is synthetic; no real persons, prices, or transactions.
