"""Read models for the API and dashboard.

Every query takes the principal and scopes to its organization. There is no
"read anything by ID" path in the request lifecycle (threat model T5).
"""

from __future__ import annotations

import uuid
from typing import Protocol

from crucible.application.ports import (
    AgentAttemptRecord,
    ApiKeyRecord,
    DatasetRecord,
    DatasetRepository,
    DatasetVersionRecord,
    IdentityRepository,
    RunEventRecord,
    RunRecord,
    RunRepository,
)
from crucible.domain import NotFound, Permission, PermissionDenied, Principal


class AttemptReader(Protocol):
    async def list_attempts(self, run_id: uuid.UUID) -> list[AgentAttemptRecord]: ...


def _require(principal: Principal, permission: Permission) -> None:
    if not principal.can(permission):
        raise PermissionDenied()


class ListDatasets:
    def __init__(self, *, datasets: DatasetRepository) -> None:
        self._datasets = datasets

    async def __call__(self, principal: Principal) -> list[DatasetRecord]:
        _require(principal, Permission.DATASET_READ)
        return await self._datasets.list_datasets(principal.organization_id)


class ListDatasetVersions:
    def __init__(self, *, datasets: DatasetRepository) -> None:
        self._datasets = datasets

    async def __call__(
        self, principal: Principal, dataset_id: uuid.UUID
    ) -> list[DatasetVersionRecord]:
        _require(principal, Permission.DATASET_READ)
        dataset = await self._datasets.get_dataset(
            organization_id=principal.organization_id, dataset_id=dataset_id
        )
        if dataset is None:
            raise NotFound("Dataset")
        return await self._datasets.list_versions(
            organization_id=principal.organization_id, dataset_id=dataset_id
        )


class GetDatasetVersion:
    def __init__(self, *, datasets: DatasetRepository) -> None:
        self._datasets = datasets

    async def __call__(self, principal: Principal, version_id: uuid.UUID) -> DatasetVersionRecord:
        _require(principal, Permission.DATASET_READ)
        version = await self._datasets.get_version(
            organization_id=principal.organization_id, version_id=version_id
        )
        if version is None:
            raise NotFound("Dataset version")
        return version


class ListRuns:
    def __init__(self, *, runs: RunRepository) -> None:
        self._runs = runs

    async def __call__(
        self, principal: Principal, *, limit: int = 50, offset: int = 0
    ) -> list[RunRecord]:
        _require(principal, Permission.RUN_READ)
        limit = max(1, min(limit, 200))
        return await self._runs.list_runs(
            organization_id=principal.organization_id, limit=limit, offset=max(0, offset)
        )


class GetRun:
    def __init__(self, *, runs: RunRepository) -> None:
        self._runs = runs

    async def __call__(self, principal: Principal, run_id: uuid.UUID) -> RunRecord:
        _require(principal, Permission.RUN_READ)
        run = await self._runs.get_run(organization_id=principal.organization_id, run_id=run_id)
        if run is None:
            raise NotFound("Run")
        return run


class ListRunEvents:
    def __init__(self, *, runs: RunRepository) -> None:
        self._runs = runs

    async def __call__(
        self, principal: Principal, run_id: uuid.UUID, *, after_sequence: int = 0
    ) -> list[RunEventRecord]:
        _require(principal, Permission.RUN_READ)
        # Ownership is proven before events are read: the events table has no
        # organization column of its own.
        run = await self._runs.get_run(organization_id=principal.organization_id, run_id=run_id)
        if run is None:
            raise NotFound("Run")
        return await self._runs.list_events(run_id=run_id, after_sequence=after_sequence)


class ListRunAttempts:
    def __init__(self, *, runs: RunRepository, attempts: AttemptReader) -> None:
        self._runs = runs
        self._attempts = attempts

    async def __call__(self, principal: Principal, run_id: uuid.UUID) -> list[AgentAttemptRecord]:
        _require(principal, Permission.RUN_READ)
        # Ownership is proven through the parent run before attempts are read.
        run = await self._runs.get_run(organization_id=principal.organization_id, run_id=run_id)
        if run is None:
            raise NotFound("Run")
        return await self._attempts.list_attempts(run_id)


class ListApiKeys:
    def __init__(self, *, identity: IdentityRepository) -> None:
        self._identity = identity

    async def __call__(self, principal: Principal) -> list[ApiKeyRecord]:
        _require(principal, Permission.APIKEY_MANAGE)
        return await self._identity.list_api_keys(principal.organization_id)
