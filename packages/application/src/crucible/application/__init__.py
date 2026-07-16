"""Crucible application layer: use cases and ports.

Boundary rule (ADR-001, enforced by import-linter): may import crucible.domain
and the standard library only. Concrete adapters (SQLAlchemy, Redis, S3, model
providers) are injected by the composing app.
"""

from crucible.application.commands.api_keys import (
    CreateApiKey,
    CreateApiKeyInput,
    CreatedApiKey,
    RevokeApiKey,
)
from crucible.application.commands.datasets import (
    CompleteDatasetUpload,
    CompleteUploadInput,
    CreateDatasetDownloadUrl,
    StartDatasetUpload,
    StartUploadInput,
    StartUploadResult,
)
from crucible.application.commands.runs import (
    CancelRun,
    CreateRun,
    CreateRunInput,
    ResolveRunReview,
    request_hash,
)
from crucible.application.ports import (
    AgentAttemptRecord,
    ApiKeyRecord,
    AuditEntry,
    AuditSink,
    Clock,
    DatasetRecord,
    DatasetRepository,
    DatasetVersionRecord,
    HealthProbe,
    IdentityRepository,
    JobQueue,
    MembershipRecord,
    ObjectStore,
    RateLimiter,
    RunEventRecord,
    RunRecord,
    RunRepository,
    UserRecord,
)
from crucible.application.queries.reads import (
    AttemptReader,
    GetDatasetVersion,
    GetRun,
    ListApiKeys,
    ListDatasets,
    ListDatasetVersions,
    ListRunAttempts,
    ListRunEvents,
    ListRuns,
)
from crucible.application.queries.system_status import GetSystemStatus
from crucible.application.services.authenticate import (
    ResolveApiKeyPrincipal,
    ResolveUserPrincipal,
    VerifiedIdentity,
)

__all__ = [
    "AgentAttemptRecord",
    "ApiKeyRecord",
    "AttemptReader",
    "AuditEntry",
    "AuditSink",
    "CancelRun",
    "Clock",
    "CompleteDatasetUpload",
    "CompleteUploadInput",
    "CreateApiKey",
    "CreateApiKeyInput",
    "CreateDatasetDownloadUrl",
    "CreateRun",
    "CreateRunInput",
    "CreatedApiKey",
    "DatasetRecord",
    "DatasetRepository",
    "DatasetVersionRecord",
    "GetDatasetVersion",
    "GetRun",
    "GetSystemStatus",
    "HealthProbe",
    "IdentityRepository",
    "JobQueue",
    "ListApiKeys",
    "ListDatasetVersions",
    "ListDatasets",
    "ListRunAttempts",
    "ListRunEvents",
    "ListRuns",
    "MembershipRecord",
    "ObjectStore",
    "RateLimiter",
    "ResolveApiKeyPrincipal",
    "ResolveRunReview",
    "ResolveUserPrincipal",
    "RevokeApiKey",
    "RunEventRecord",
    "RunRecord",
    "RunRepository",
    "StartDatasetUpload",
    "StartUploadInput",
    "StartUploadResult",
    "UserRecord",
    "VerifiedIdentity",
    "request_hash",
]
