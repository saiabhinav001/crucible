# Crucible

**An open-source evaluation and reliability platform for LLM agents**, with a
self-correcting data-analysis agent as its bounded reference workload.

> A language-model agent should be trusted only to the degree that its behavior is
> **measured, reproducible, observable, bounded, and independently checked.**

Crucible's differentiator is not the agent loop — it is the evidence around the loop:
executable offline evaluation, versioned experiment comparisons, production tracing,
constrained execution, regression gates, and a stable failure taxonomy.

## Status: Phase 9 complete (production CI/CD, staging, load, hardening)

Phases 0–8 built the platform, sandbox, durable agent, regression gate,
observability, product UI, and the efficiency layer. **Phase 9 makes delivery
and operations repeatable and safe** before real users arrive — with the
pipeline itself treated as an attack surface.

- **Federated, keyless deploys.** GitHub Actions reaches GCP via OIDC / Workload
  Identity Federation — no long-lived cloud key exists. Images are built
  reproducibly, referenced by digest, cosign-signed with an SBOM; production
  promotion deploys the exact digest that passed staging and verifies its
  signature first. Every third-party action is pinned to a commit SHA and the
  workflows are `zizmor`-clean. ([ADR-009](docs/adr/ADR-009-deployment-security.md))
- **Reproducible infrastructure.** The whole GCP stack is OpenTofu
  (`infra/opentofu`): private Cloud SQL (HA + PITR), Memorystore, GCS, Secret
  Manager, Cloud Run with separate API/worker identities, and the WIF pool — no
  console-clicks.
- **Layered security scanning, enforced on PRs.** gitleaks, pip-audit, CodeQL,
  Semgrep (registry packs **plus** the repo's own guardrail rules), Trivy, and
  Checkov for IaC.
- **Reversible by design.** Expand/contract migrations run as an explicit deploy
  step (never on startup); a rollback is a traffic shift to the prior,
  schema-compatible revision — so a code rollback never needs a data rollback.
- **Resilience proven, not asserted.** A load/soak harness with hard latency +
  error-budget gates, three executable game days (provider outage, queue loss,
  worker crash), and a non-destructive DR drill that produces
  [committed evidence](docs/operations/disaster-recovery.md). See the
  [deployment runbook](docs/operations/deployment-runbook.md).

<details><summary>Earlier: Phase 8 — measured routing, exact cache, budgets</summary>

Every efficiency lever is declared, evidence-gated, and reversible with one
setting: a two-tier router (identical accuracy at 63% less cost on the held-out
experiment), an exact cache that cannot cross tenant/dataset/config, and a
budget ledger that refuses runs before spending. See
[docs/operations/efficiency.md](docs/operations/efficiency.md).

</details>

<details><summary>Earlier: Phase 7 — product dashboard, review UX, and docs</summary>

The whole user journey — upload → run → evidence → compare → review — is
completable in the UI, with no internal tools.

- **A real design system** (`packages/ui`): theme-aware tokens (light/dark), and
  reusable `StatusBadge` / `DataTable` / `Trace` / `ConfigView` / `MetricCard`
  components, shipped as source and transpiled into the app.
- **The full journey in the browser.** Upload straight to storage (bytes never
  touch the API or the web server), start runs, inspect the redacted trace and
  provenance behind every answer, compare a candidate against the baseline, and
  claim → grade → resolve a review — each an authenticated, tenant-scoped action.
- **The credential is the session.** The web app authenticates with a
  server-side, org-scoped API key that never reaches the browser; the UI mirrors
  the API's authorization (see `/settings`) rather than inventing its own, so it
  cannot leak another tenant's data.
- **Accessible and responsive.** Semantic landmarks, a skip link, keyboard-first
  controls with visible focus, status never by colour alone, fluid layouts, and
  tables that scroll inside their panel — light and dark.
- **Report export + demo seeding.** Download a comparison as JSON (the exact
  CI-gated bytes) or Markdown; `scripts/seed_demo.py` populates a demo org so the
  dashboard has real content in one command.

See the [product tour](docs/operations/product-tour.md) and the
[web architecture](docs/architecture/web-frontend.md).

```bash
uv run python scripts/seed_demo.py --slug demo   # populate a demo org
pnpm --filter web dev                            # http://localhost:3100
```

</details>

<details><summary>Earlier: Phase 6 — observability, online eval, and human review</summary>

Every terminal run shows a redacted trace, cost, latency, versions, and a failure
taxonomy; a reviewer can safely score a run; the judge is calibrated against
held-out human labels and confined to secondary criteria; reliability alerts are
exercised. One redaction boundary (`crucible.observability.redaction`) gates
everything that leaves the trust boundary (threat T8); trace completeness is the
DoD metric. See [docs/operations/observability.md](docs/operations/observability.md).

</details>

<details><summary>Earlier: Phase 5 — offline evaluation harness + regression gate</summary>

Phase 5 is an executable regression gate. It runs the real agent over versioned
cases, scores against trusted oracles, and compares a candidate to a frozen
baseline with a paired bootstrap confidence interval.

- **Versioned suites, verified gold.** Every gold answer in the core suite is
  cross-checked against an independent, executable reference calculator; fixtures
  are pinned by SHA-256; released cases are immutable (the baseline pins the
  suite hash, so an edit fails the lineage test).
- **Scorer hierarchy, kept separate.** Tier 1 correctness (exact / numeric-
  tolerance / result-set / behavioral-abstention) is the gate; Tier 3 policy
  checks are hard gates. They never blend — a wrong answer is never rescued by a
  clean policy check, and code running is never mistaken for a correct answer.
- **Paired comparison + gate.** The gate BLOCKs a material regression (upper CI
  bound below tolerance) or any policy failure, FLAGs an inconclusive regression
  for review, and never calls a change an improvement when the interval spans
  zero. The bootstrap uses a fixed seed, so the interval is reproducible.
- **It catches real regressions.** Building it surfaced two genuine agent bugs
  (fixed); a deliberately injected regression is blocked end-to-end through the
  real sandbox.

```bash
make sandbox-image                          # build the runner
make eval-run                               # score the core suite vs the frozen baseline, gate
```

</details>

<details><summary>Earlier: Phase 4 — durable data-agent MVP</summary>

The agent plans an analysis, generates code, runs it in the Phase 3 sandbox,
verifies, and either answers with provenance, abstains truthfully, or routes to
human review.

- **Explicit durable graph** (ADR-008): validate → profile → plan → code →
  execute → observe → repair (bounded, max 2) → verify → synthesize. It
  checkpoints after every node, so a worker restart resumes from where it left
  off rather than re-running model calls and sandbox executions.
- **Provider-neutral model gateway**: a deterministic `fake` backend (template
  planner/coder — offline, no cloud LLM) and an OpenAI-compatible contract. The
  fake produces *real, correct* answers because the generated code runs for real
  in the sandbox.
- **Honest terminal states**: `answered` (with provenance pointing at the
  computed result), `abstained` (unsupported question, or a failure that repair
  can't fix), `waiting_review` (an ambiguous result, e.g. a tie), `cancelled`.
  The answer text is synthesized mechanically from the verified result, so it
  can never claim more than the number.
- **Proven end to end**: the agent computes real sums, distinct counts, and
  group-maxima through the actual Docker sandbox; the durable resume, bounded
  repair, oscillation guard, and review flow are all tested.

```bash
make sandbox-image                    # build the runner
uv run pytest -m sandbox              # agent computes real answers in the sandbox
```

</details>

<details><summary>Earlier: Phase 3 — isolated execution boundary + safety canaries</summary>

The highest-risk phase, deliberately built before any agent existed to run code
through it.

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

</details>

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
