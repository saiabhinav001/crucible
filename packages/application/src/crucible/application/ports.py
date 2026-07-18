"""Ports (interfaces) that adapters implement. Transport/infra code depends on
these; this layer never depends on transport/infra (ADR-001).

Every repository method that reads tenant-owned data takes `organization_id`
explicitly. There is no "current tenant" ambient state to forget — a missing
argument is a type error, not a silent cross-tenant read (threat model T5).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from crucible.domain import (
    ActorType,
    AuditAction,
    AuditResult,
    ComponentHealth,
    DatasetProfile,
    DatasetVersionStatus,
    Permission,
    Role,
    RunEventType,
    RunStatus,
)


class HealthProbe(Protocol):
    """Probes one dependency for readiness. Implementations must never raise:
    a failing dependency is reported as ComponentHealth(state=DOWN)."""

    @property
    def name(self) -> str: ...

    async def check(self) -> ComponentHealth: ...


# --------------------------------------------------------------------- records
# Read models returned by repositories. These are plain data, not ORM rows:
# the application layer must not depend on SQLAlchemy session semantics.


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: uuid.UUID
    subject: str
    email: str | None
    display_name: str | None


@dataclass(frozen=True, slots=True)
class MembershipRecord:
    organization_id: uuid.UUID
    organization_slug: str
    organization_name: str
    user_id: uuid.UUID
    role: Role


@dataclass(frozen=True, slots=True)
class ApiKeyRecord:
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    prefix: str
    secret_hash: str
    role: Role
    scopes: tuple[Permission, ...] | None
    expires_at: datetime | None
    revoked_at: datetime | None

    def is_usable(self, now: datetime) -> bool:
        if self.revoked_at is not None:
            return False
        return not (self.expires_at is not None and self.expires_at <= now)


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    created_at: datetime
    latest_version_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class DatasetVersionRecord:
    id: uuid.UUID
    dataset_id: uuid.UUID
    organization_id: uuid.UUID
    version_no: int
    status: DatasetVersionStatus
    object_key: str
    content_type: str
    declared_size_bytes: int
    size_bytes: int | None = None
    content_sha256: str | None = None
    schema_hash: str | None = None
    row_count: int | None = None
    column_count: int | None = None
    profile: dict[str, Any] | None = None
    invalid_reason: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RunRecord:
    id: uuid.UUID
    organization_id: uuid.UUID
    dataset_version_id: uuid.UUID
    question: str
    status: RunStatus
    config_manifest: dict[str, Any]
    idempotency_key: str | None
    request_hash: str | None
    terminal_detail: str | None
    failure_category: str | None
    cancel_requested_at: datetime | None
    created_at: datetime
    updated_at: datetime
    answer: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ScoreInput:
    definition_key: str
    score_type: str
    source: str
    target_type: str
    target_id: str
    evaluator_version: str
    value_num: float | None = None
    value_bool: bool | None = None
    value_categorical: str | None = None
    value_text: str | None = None
    created_by: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class ScoreRecord:
    definition_key: str
    score_type: str
    source: str
    target_type: str
    target_id: str
    evaluator_version: str
    value_num: float | None
    value_bool: bool | None
    value_categorical: str | None
    value_text: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    id: uuid.UUID
    organization_id: uuid.UUID
    run_id: uuid.UUID
    status: str
    rubric_version: str
    claimed_by: uuid.UUID | None
    claim_expires_at: datetime | None
    decision: str | None
    lock_version: int


@dataclass(frozen=True, slots=True)
class ReviewQueueItem:
    run_id: uuid.UUID
    question: str
    created_at: datetime
    review_status: str | None
    verification: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class RunTelemetryRow:
    run_id: uuid.UUID
    status: str
    failure_category: str | None
    cost_usd: float
    latency_ms: int
    attempt_count: int
    trace_complete: bool


@dataclass(frozen=True, slots=True)
class AgentAttemptRecord:
    run_id: uuid.UUID
    attempt_no: int
    kind: str
    sequence_no: int
    payload: dict[str, Any]
    model_provider: str | None
    model_id: str | None
    exit_class: str | None
    failure_category: str | None
    duration_ms: int | None
    cost_usd: float | None
    source_sha256: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RunEventRecord:
    run_id: uuid.UUID
    sequence_no: int
    event_type: RunEventType
    payload: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AuditEntry:
    organization_id: uuid.UUID | None
    actor_type: ActorType
    actor_id: uuid.UUID | None
    action: AuditAction
    result: AuditResult
    target_type: str
    target_id: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ----------------------------------------------------------------- repositories


class IdentityRepository(Protocol):
    async def upsert_user(
        self, *, subject: str, email: str | None, display_name: str | None
    ) -> UserRecord: ...

    async def memberships_for_user(self, user_id: uuid.UUID) -> list[MembershipRecord]: ...

    async def membership(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> MembershipRecord | None: ...

    async def api_key_by_prefix(self, prefix: str) -> ApiKeyRecord | None: ...

    async def touch_api_key(self, key_id: uuid.UUID) -> None: ...

    async def create_api_key(
        self,
        *,
        organization_id: uuid.UUID,
        created_by: uuid.UUID | None,
        name: str,
        prefix: str,
        secret_hash: str,
        role: Role,
        scopes: tuple[Permission, ...] | None,
        expires_at: datetime | None,
    ) -> ApiKeyRecord: ...

    async def list_api_keys(self, organization_id: uuid.UUID) -> list[ApiKeyRecord]: ...

    async def revoke_api_key(self, *, organization_id: uuid.UUID, key_id: uuid.UUID) -> bool: ...


class DatasetRepository(Protocol):
    async def create_dataset(self, *, organization_id: uuid.UUID, name: str) -> DatasetRecord: ...

    async def dataset_by_name(
        self, *, organization_id: uuid.UUID, name: str
    ) -> DatasetRecord | None: ...

    async def get_dataset(
        self, *, organization_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> DatasetRecord | None: ...

    async def list_datasets(self, organization_id: uuid.UUID) -> list[DatasetRecord]: ...

    async def create_version(
        self,
        *,
        organization_id: uuid.UUID,
        dataset_id: uuid.UUID,
        version_id: uuid.UUID,
        object_key: str,
        content_type: str,
        declared_size_bytes: int,
        filename: str,
    ) -> DatasetVersionRecord: ...

    async def get_version(
        self, *, organization_id: uuid.UUID, version_id: uuid.UUID
    ) -> DatasetVersionRecord | None: ...

    async def list_versions(
        self, *, organization_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> list[DatasetVersionRecord]: ...

    async def version_by_content_hash(
        self, *, dataset_id: uuid.UUID, content_sha256: str
    ) -> DatasetVersionRecord | None: ...

    async def mark_version_uploaded(
        self,
        *,
        version_id: uuid.UUID,
        size_bytes: int,
        content_sha256: str,
    ) -> DatasetVersionRecord: ...

    async def mark_version_ready(
        self, *, version_id: uuid.UUID, profile: DatasetProfile
    ) -> DatasetVersionRecord: ...

    async def mark_version_invalid(
        self, *, version_id: uuid.UUID, reason: str, detail: str
    ) -> DatasetVersionRecord: ...

    async def delete_version(self, version_id: uuid.UUID) -> None: ...


class RunRepository(Protocol):
    async def create_run(
        self,
        *,
        organization_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        question: str,
        config_manifest: dict[str, Any],
        idempotency_key: str | None,
        request_hash: str | None,
        created_by: uuid.UUID | None,
    ) -> RunRecord: ...

    async def get_run(
        self, *, organization_id: uuid.UUID, run_id: uuid.UUID
    ) -> RunRecord | None: ...

    async def get_run_unscoped(self, run_id: uuid.UUID) -> RunRecord | None:
        """Worker-only: the worker holds no principal, so it reads by run ID.
        Never call this from a request path."""
        ...

    async def list_runs(
        self, *, organization_id: uuid.UUID, limit: int, offset: int
    ) -> list[RunRecord]: ...

    async def run_by_idempotency_key(
        self, *, organization_id: uuid.UUID, idempotency_key: str
    ) -> RunRecord | None: ...

    async def transition(
        self,
        *,
        run_id: uuid.UUID,
        expected: RunStatus,
        target: RunStatus,
        terminal_detail: str | None = None,
        failure_category: str | None = None,
    ) -> RunRecord | None:
        """Compare-and-set on status. Returns None when the run has moved on —
        the caller must not force the write (optimistic concurrency)."""
        ...

    async def request_cancel(self, run_id: uuid.UUID) -> None: ...

    async def append_event(
        self,
        *,
        run_id: uuid.UUID,
        event_type: RunEventType,
        payload: dict[str, Any],
    ) -> RunEventRecord: ...

    async def list_events(
        self, *, run_id: uuid.UUID, after_sequence: int = 0
    ) -> list[RunEventRecord]: ...


class AuditSink(Protocol):
    async def record(self, entry: AuditEntry) -> None: ...


class ScoreStore(Protocol):
    async def add_score(self, *, organization_id: uuid.UUID, score: ScoreInput) -> None: ...

    async def list_scores(
        self, *, organization_id: uuid.UUID, target_type: str, target_id: str
    ) -> list[ScoreRecord]: ...


class ReviewRepository(Protocol):
    async def list_queue(
        self, *, organization_id: uuid.UUID, limit: int = 50
    ) -> list[ReviewQueueItem]: ...

    async def get_review(
        self, *, organization_id: uuid.UUID, run_id: uuid.UUID
    ) -> ReviewRecord | None: ...

    async def claim(
        self,
        *,
        organization_id: uuid.UUID,
        run_id: uuid.UUID,
        reviewer: uuid.UUID,
        rubric_version: str,
        ttl_seconds: int,
    ) -> ReviewRecord | None: ...

    async def submit(
        self, *, organization_id: uuid.UUID, run_id: uuid.UUID, reviewer: uuid.UUID, decision: str
    ) -> ReviewRecord | None: ...


class MetricsRepository(Protocol):
    async def run_telemetry(
        self, *, organization_id: uuid.UUID, limit: int = 200
    ) -> list[RunTelemetryRow]: ...


# --------------------------------------------------------------- infrastructure


class ObjectStore(Protocol):
    def presign_put(self, key: str, *, content_type: str, expires_seconds: int = 900) -> str: ...

    def presign_get(self, key: str, *, expires_seconds: int = 300) -> str: ...

    def head(self, key: str) -> Any: ...

    def get_bytes(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


class JobQueue(Protocol):
    async def enqueue(self, job: str, *args: Any) -> str: ...


class RateLimiter(Protocol):
    async def check(self, key: str, *, limit: int, window_seconds: int) -> Any: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
