# Crucible

**An open-source evaluation and reliability platform for LLM agents**, with a
self-correcting data-analysis agent as its bounded reference workload.

> A language-model agent should be trusted only to the degree that its behavior is
> **measured, reproducible, observable, bounded, and independently checked.**

Crucible's differentiator is not the agent loop — it is the evidence around the loop:
executable offline evaluation, versioned experiment comparisons, production tracing,
constrained execution, regression gates, and a stable failure taxonomy.

## Status: Phase 3 complete (isolated execution boundary + safety canaries)

Phase 0 defined the workload and metric contract; Phase 1 built the reproducible
platform; Phase 2 added the tenant and data foundation. **Phase 3 builds the
execution boundary for model-generated code and proves it** — the highest-risk
phase, deliberately built before any agent exists to run code through it.

- **Fixed protocol, no model-controlled config.** The execution request carries
  only a program and one dataset; it has no field for an image, mount, network
  flag, capability, package, or environment variable.
- **Hardened runner (local dev):** non-root, all Linux capabilities dropped,
  no-new-privileges, read-only root, network disabled (no egress/DNS/metadata),
  no Docker socket, memory/CPU/pids/wall-clock/file-size/output caps, fresh
  container per attempt, force-destroyed.
- **Backends** (ADR-003): `FakeExecutor` (tests, never runs code), `DockerExecutor`
  (dev), `MicroVMExecutor` (staging/prod, deny-by-default with no weaker fallback).
- **20 containment canaries** run real hostile programs against the real runner
  and prove each control holds — network exfiltration, host escape, privilege
  escalation, memory/CPU/fork/output bombs, malicious artifacts, and secret
  disclosure are all contained. See [docs/security/sandbox.md](docs/security/sandbox.md).

```bash
make sandbox-image && make sandbox      # build the runner and run the canaries
```

Earlier phases (identity, dataset ingestion, durable runs) below.

```bash
uv sync --dev && docker compose up -d                       # full local stack
uv run alembic -c packages/db/alembic.ini upgrade head
uv run python scripts/bootstrap_org.py --slug demo          # prints an API key once
pwsh scripts/check.ps1                                      # or: make check
```

- **Identity:** OIDC JWT *or* Argon2id-hashed API keys; five roles, default-deny RBAC
  checked inside every use case. A key can never exceed its creator's permissions.
- **Datasets:** presigned direct-to-storage uploads (file bytes never touch the API),
  immutable **content-addressed** versions, worker-side parsing/profiling with hash
  verification. Identical bytes reuse the existing version.
- **Runs:** durable async jobs with a guarded state machine, append-only event history,
  SSE streaming, `Idempotency-Key` support, and real cancellation.
- **Evidence:** append-only audit log, including denials — written in their own
  transaction so they survive the rolled-back request that produced them.
- **Tests:** 180 passing, including a 20-case tenant-isolation suite proving a second
  organization cannot reach anything by guessed ID.

The agent itself is deliberately absent until Phase 4: a run today is accepted,
claimed, and terminated as `abstained` with an explicit reason rather than
fabricating an answer.

See the [API guide](docs/operations/api-guide.md) and
[local development guide](docs/operations/local-development.md).

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
