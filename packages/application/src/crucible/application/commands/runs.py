"""Run lifecycle use cases: create (idempotent) and cancel.

Phase 2 creates durable runs and drives the state machine; the agent workflow
that fills them with real work arrives in Phase 4 (ADR-004).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any

from crucible.application.ports import (
    AuditEntry,
    AuditSink,
    DatasetRepository,
    JobQueue,
    RunRecord,
    RunRepository,
)
from crucible.domain import (
    MAX_QUESTION_CHARS,
    AuditAction,
    AuditResult,
    Conflict,
    DatasetVersionStatus,
    NotFound,
    Permission,
    PermissionDenied,
    Principal,
    RunEventType,
    RunStatus,
    ValidationFailed,
)


def _require(principal: Principal, permission: Permission) -> None:
    if not principal.can(permission):
        raise PermissionDenied()


def request_hash(payload: dict[str, Any]) -> str:
    """Stable hash of the request body, used to detect an Idempotency-Key that
    is replayed with a *different* payload (plan §5.5: reject, never merge)."""
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CreateRunInput:
    dataset_version_id: uuid.UUID
    question: str
    idempotency_key: str | None = None


class CreateRun:
    def __init__(
        self,
        *,
        runs: RunRepository,
        datasets: DatasetRepository,
        queue: JobQueue,
        audit: AuditSink,
        release_id: str = "unknown",
    ) -> None:
        self._runs = runs
        self._datasets = datasets
        self._queue = queue
        self._audit = audit
        self._release_id = release_id

    async def __call__(
        self, principal: Principal, data: CreateRunInput, *, request_id: str = ""
    ) -> tuple[RunRecord, bool]:
        """Returns (run, created). `created=False` means an idempotent replay."""
        _require(principal, Permission.RUN_CREATE)
        org = principal.organization_id

        question = data.question.strip()
        if not question:
            raise ValidationFailed("Question must not be empty.", code="empty-question")
        if len(question) > MAX_QUESTION_CHARS:
            raise ValidationFailed(
                f"Question must be at most {MAX_QUESTION_CHARS} characters.",
                code="question-too-long",
            )

        payload_hash = request_hash(
            {"dataset_version_id": str(data.dataset_version_id), "question": question}
        )

        if data.idempotency_key:
            prior = await self._runs.run_by_idempotency_key(
                organization_id=org, idempotency_key=data.idempotency_key
            )
            if prior is not None:
                if prior.request_hash != payload_hash:
                    raise Conflict(
                        "This Idempotency-Key was already used with a different request body.",
                        code="idempotency-key-reuse",
                    )
                return prior, False

        version = await self._datasets.get_version(
            organization_id=org, version_id=data.dataset_version_id
        )
        if version is None:
            raise NotFound("Dataset version")
        if version.status is not DatasetVersionStatus.READY:
            raise Conflict(
                f"Dataset version is '{version.status.value}'; runs require a 'ready' version.",
                code="dataset-not-ready",
            )

        # The config manifest freezes every behavior-changing input known at
        # creation time (plan principle 5). Agent/model/prompt versions join it
        # in Phase 4 when the workflow exists to have them.
        manifest: dict[str, Any] = {
            "manifest_version": 1,
            "release_id": self._release_id,
            "dataset_version_id": str(version.id),
            "dataset_content_sha256": version.content_sha256,
            "dataset_schema_hash": version.schema_hash,
            "agent": {"status": "not_implemented", "phase": "P4"},
        }

        run = await self._runs.create_run(
            organization_id=org,
            dataset_version_id=version.id,
            question=question,
            config_manifest=manifest,
            idempotency_key=data.idempotency_key,
            request_hash=payload_hash,
            created_by=principal.user_id,  # None for API-key callers; audit has the full actor
        )
        await self._runs.append_event(
            run_id=run.id,
            event_type=RunEventType.CREATED,
            payload={"status": RunStatus.QUEUED.value},
        )
        await self._queue.enqueue("execute_run", str(run.id))
        await self._audit.record(
            AuditEntry(
                organization_id=org,
                actor_type=principal.actor_type,
                actor_id=principal.actor_id,
                action=AuditAction.RUN_CREATED,
                result=AuditResult.ALLOWED,
                target_type="run",
                target_id=str(run.id),
                request_id=request_id,
                metadata={"dataset_version_id": str(version.id)},
            )
        )
        return run, True


class CancelRun:
    """Cancels a run.

    A queued run is cancelled synchronously (no worker has claimed it). A
    running run gets a cancellation request that the worker observes at its
    next checkpoint — cancellation propagates, it is never faked (plan §17).
    """

    def __init__(self, *, runs: RunRepository, audit: AuditSink) -> None:
        self._runs = runs
        self._audit = audit

    async def __call__(
        self, principal: Principal, run_id: uuid.UUID, *, request_id: str = ""
    ) -> RunRecord:
        _require(principal, Permission.RUN_CANCEL)
        org = principal.organization_id

        run = await self._runs.get_run(organization_id=org, run_id=run_id)
        if run is None:
            raise NotFound("Run")

        if run.status is RunStatus.QUEUED:
            cancelled = await self._runs.transition(
                run_id=run.id,
                expected=RunStatus.QUEUED,
                target=RunStatus.CANCELLED,
                terminal_detail="Cancelled before a worker claimed the run.",
            )
            if cancelled is None:
                # The worker claimed it between our read and write: fall through
                # to a cancellation request rather than forcing the state.
                run = await self._runs.get_run(organization_id=org, run_id=run_id) or run
            else:
                await self._runs.append_event(
                    run_id=run.id,
                    event_type=RunEventType.TERMINAL,
                    payload={"status": RunStatus.CANCELLED.value},
                )
                await self._record(principal, run.id, request_id, "cancelled")
                return cancelled

        if run.status in (RunStatus.RUNNING, RunStatus.WAITING_REVIEW):
            await self._runs.request_cancel(run.id)
            await self._runs.append_event(
                run_id=run.id,
                event_type=RunEventType.CANCEL_REQUESTED,
                payload={"requested_by": str(principal.actor_id)},
            )
            await self._record(principal, run.id, request_id, "cancel_requested")
            return await self._runs.get_run(organization_id=org, run_id=run_id) or run

        raise Conflict(
            f"Run is already terminal ('{run.status.value}') and cannot be cancelled.",
            code="run-terminal",
        )

    async def _record(
        self, principal: Principal, run_id: uuid.UUID, request_id: str, outcome: str
    ) -> None:
        await self._audit.record(
            AuditEntry(
                organization_id=principal.organization_id,
                actor_type=principal.actor_type,
                actor_id=principal.actor_id,
                action=AuditAction.RUN_CANCELLED,
                result=AuditResult.ALLOWED,
                target_type="run",
                target_id=str(run_id),
                request_id=request_id,
                metadata={"outcome": outcome},
            )
        )
