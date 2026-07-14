# Crucible — C4 Level 1 Context (with plane separation)

Status: Phase 0 baseline · Date: 2026-07-14

## System context

```mermaid
flowchart LR
  subgraph People
    AE[Applied AI engineer]
    PE[Platform engineer]
    RV[Reviewer]
    DU[Demo user]
  end

  AE & PE & RV & DU --> CR[Crucible platform<br/>evaluates and operates the<br/>data-analysis reference agent]

  CR --> IDP[OIDC identity provider]
  CR --> MP[LLM model providers<br/>provider-neutral gateway]
  CR --> SBX[Managed microVM sandbox<br/>untrusted code boundary]
  CR --> OST[(Object storage<br/>datasets + artifacts)]
  CR --> OBS[Langfuse + OTel backends<br/>redacted telemetry only]
  GH[GitHub Actions CI/CD] --> CR
```

## Plane separation (the core architectural claim)

```mermaid
flowchart TB
  subgraph Serving[Serving plane — must stay available and bounded]
    API[API + auth + quotas] --> Job[Durable job]
    Job --> Agent[Agent workflow: profile→plan→code→execute→observe→repair→verify→synthesize]
    Agent --> Sandbox[Constrained execution]
    Agent --> Answer[Answer / abstain / review]
  end

  subgraph Evaluation[Evaluation plane — async, expensive, evidence-preserving]
    Cases[Versioned cases + references] --> Runner[Experiment runner]
    Runner --> Scorers[Tier 1 oracle → policy → calibrated judge]
    Scorers --> Metrics[Immutable comparison results]
    Metrics --> Gate[CI release gate]
  end

  Agent -. sampled redacted traces .-> Runner
  Agent -. versions, cost, latency .-> Tele[Observability plane]
  Runner -. scores .-> Tele
```

Rules encoded by this diagram:

1. The serving plane answers a request; the evaluation plane judges *changes to the
   agent*. They fail independently — analytics delay never degrades serving.
2. The evaluation plane never silently rewrites baselines.
3. The sandbox is outside the API/worker trust boundary (see ADR-003 and the threat model).
4. Only redacted, hashed, access-controlled content crosses into observability providers.

Container- and component-level diagrams (C4 L2/L3) are Phase 1–4 deliverables, created
as the corresponding services come into existence — not speculated here.
