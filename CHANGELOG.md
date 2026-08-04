# Changelog

All notable changes to Crucible. Dates are the phase-completion dates.
Format follows [Keep a Changelog](https://keepachangelog.com/); the project is
pre-1.0 and versioned by phase until the v1.0.0 release.

## [Unreleased] — Phase 10: Private beta deployment & reliability operations — 2026-07-21

### Added
- **Beta allowlist / org lifecycle.** Organizations carry a `status`
  (`active`/`suspended`); a suspended org is refused at the authentication
  boundary for both API keys and OIDC. (migration 0006)
- **Data retention.** A daily worker job deletes terminal runs and their
  evidence (and old cache entries) past a window (platform default 90 days,
  per-tenant override via `retention_days`); audit events and datasets are out
  of scope. Dry-run supported.
- **Right-to-erasure.** `purge-org` removes all of a tenant's data and the org
  itself, dry-run first.
- **Operator tooling.** `scripts/admin.py` (list/suspend/activate/set-budget/
  set-retention/retention/purge-org), `scripts/onboard_beta_tenant.py`,
  `scripts/weekly_review.py` (reliability + eval review artifact), and
  `scripts/prod_canary.py` (synthetic production canary).
- **Public edge IaC.** Cloud Armor WAF (rate limiting, OWASP SQLi/XSS/LFI,
  Log4Shell) + global HTTPS load balancer + Google-managed TLS in front of the
  API, with HTTP→HTTPS redirect.
- **Beta ops & legal docs.** Retention policy, beta onboarding, support/
  incident-response/on-call runbooks, and draft Terms of Service + Data-
  Processing Notice.

### Changed
- Cloud SQL hardened: TLS-only, connection/checkpoint/lock/hostname/statement
  logging and pgAudit; deployer `serviceAccountUser` scoped per runtime SA
  (not project-wide); explicit default-deny firewall. IaC passes `tofu validate`
  and Checkov (0 failed).

## Phase 9 — Production CI/CD, staging, load & hardening — 2026-07-20
Federated (OIDC/WIF) keyless deploys; digest-pinned, cosign-signed images with
SBOM; staging deploy + production promotion + rollback workflows; OpenTofu GCP
reference IaC; layered security scanning (CodeQL/Semgrep/Trivy/gitleaks/zizmor);
load/soak harness; provider-outage, queue-loss, and crash-recovery game days; a
non-destructive DR drill with committed evidence.

## Phase 8 — Measured routing, exact cache & budgets — 2026-07-19
Declared two-tier router (identical accuracy at 63% lower cost on the held-out
experiment); exact cache that cannot cross tenant/dataset/config; per-tenant
budget ledger that refuses runs before spending.

## Phase 7 — Product dashboard, review UX & docs — 2026-07-18
Design system (`packages/ui`); the full journey (upload → run → evidence →
compare → review) completable in the UI; report export; demo seeding.

## Phase 6 — Observability, online eval & human review — 2026-07-18
Single redaction boundary for all exported telemetry (threat T8); reliability/
cost/latency/trace-completeness metrics; SLO alerts; human review queue;
calibrated, secondary LLM judge.

## Phases 0–5
Platform bootstrap; identity & data plane; isolated execution sandbox with
containment canaries; durable data-agent; offline evaluation harness with a
paired-bootstrap regression gate. See git history and per-phase commits.
