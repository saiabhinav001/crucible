"""Composition of the agent's ports over the concrete infrastructure.

`SqlAgentPersistence` implements the agent's `AgentPersistence` protocol on top
of the SQL repositories and object storage. Each method uses its own short
transaction and commits, so every checkpoint, event, and attempt is durable
before the next node runs — that is what makes a worker restart resume cleanly.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from crucible.agent import (
    AgentPersistence,
    AttemptRecord,
    ColumnView,
    DatasetView,
    FakeModel,
    ModelGateway,
    OpenAICompatModel,
    RunView,
)
from crucible.db import SqlAgentStore, SqlDatasetRepository, SqlRunRepository
from crucible.domain import RunEventType, RunStatus
from crucible.execution import ExecutionLimits
from crucible.storage import S3ObjectStorage
from crucible_worker.settings import WorkerAppSettings


class SqlAgentPersistence(AgentPersistence):
    def __init__(self, session_factory: async_sessionmaker[Any], storage: S3ObjectStorage) -> None:
        self._factory = session_factory
        self._storage = storage

    async def load_run(self, run_id: str) -> RunView | None:
        import uuid

        async with self._factory() as s:
            run = await SqlRunRepository(s).get_run_unscoped(uuid.UUID(run_id))
        if run is None:
            return None
        return RunView(
            run_id=str(run.id),
            organization_id=str(run.organization_id),
            dataset_version_id=str(run.dataset_version_id),
            question=run.question,
            status=run.status.value,
            cancel_requested=run.cancel_requested_at is not None,
        )

    async def load_dataset(self, version_id: str) -> DatasetView | None:
        import uuid

        async with self._factory() as s:
            version = await SqlDatasetRepository(s).get_version_unscoped(uuid.UUID(version_id))
        if version is None:
            return None
        columns = []
        profile = version.profile or {}
        for col in profile.get("columns", []):
            columns.append(ColumnView(name=col["name"], dtype=col["dtype"]))
        return DatasetView(
            version_id=version_id,
            object_key=version.object_key,
            content_sha256=version.content_sha256,
            media_type=version.content_type,
            filename=Path(version.object_key).name,
            profile=columns,
        )

    async def load_dataset_bytes(self, object_key: str) -> bytes:
        return await asyncio.to_thread(self._storage.get_bytes, object_key)

    async def is_cancel_requested(self, run_id: str) -> bool:
        import uuid

        async with self._factory() as s:
            return await SqlRunRepository(s).is_cancel_requested(uuid.UUID(run_id))

    async def emit_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        import uuid

        async with self._factory() as s:
            await SqlRunRepository(s).append_event(
                run_id=uuid.UUID(run_id), event_type=RunEventType(event_type), payload=payload
            )
            await s.commit()

    async def append_attempt(self, run_id: str, org_id: str, attempt: AttemptRecord) -> None:
        import uuid

        async with self._factory() as s:
            await SqlAgentStore(s).append_attempt(
                run_id=uuid.UUID(run_id),
                organization_id=uuid.UUID(org_id),
                kind=attempt.kind,
                sequence_no=attempt.sequence_no,
                payload=attempt.payload,
                model_provider=attempt.model_provider,
                model_id=attempt.model_id,
                exit_class=attempt.exit_class,
                failure_category=attempt.failure_category,
                duration_ms=attempt.duration_ms,
                cost_usd=attempt.cost_usd,
                source_sha256=attempt.source_sha256,
            )
            await s.commit()

    async def save_checkpoint(self, run_id: str, node: str, state_json: str) -> None:
        import uuid

        async with self._factory() as s:
            await SqlAgentStore(s).save_checkpoint(
                run_id=uuid.UUID(run_id), node=node, state=json.loads(state_json)
            )
            await s.commit()

    async def load_checkpoint(self, run_id: str) -> tuple[str, str] | None:
        import uuid

        async with self._factory() as s:
            row = await SqlAgentStore(s).load_checkpoint(uuid.UUID(run_id))
        return None if row is None else (row[0], json.dumps(row[1]))

    async def transition(
        self,
        run_id: str,
        *,
        expected: str,
        target: str,
        detail: str | None = None,
        failure_category: str | None = None,
    ) -> bool:
        import uuid

        async with self._factory() as s:
            record = await SqlRunRepository(s).transition(
                run_id=uuid.UUID(run_id),
                expected=RunStatus(expected),
                target=RunStatus(target),
                terminal_detail=detail,
                failure_category=failure_category,
            )
            await s.commit()
        return record is not None

    async def set_result(
        self, run_id: str, *, answer: dict[str, Any] | None, verification: dict[str, Any] | None
    ) -> None:
        import uuid

        async with self._factory() as s:
            await SqlRunRepository(s).set_result(
                run_id=uuid.UUID(run_id), answer=answer, verification=verification
            )
            await s.commit()


def build_model(settings: WorkerAppSettings) -> ModelGateway:
    if settings.model_backend == "openai_compat":
        return OpenAICompatModel(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    return FakeModel()


def build_limits(settings: WorkerAppSettings) -> ExecutionLimits:
    return ExecutionLimits(wall_seconds=settings.execution_wall_seconds)
