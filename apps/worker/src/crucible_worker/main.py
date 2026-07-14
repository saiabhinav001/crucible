"""arq worker entry point.

Run:           uv run arq crucible_worker.main.WorkerSettings
Health check:  uv run arq --check crucible_worker.main.WorkerSettings
(arq writes a heartbeat key to Redis; --check exits nonzero when stale —
used as the container healthcheck in compose.yaml.)

Phase 1 ships only a `ping` heartbeat job; the durable agent workflow is a
Phase 4 deliverable.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, ClassVar

from arq.connections import RedisSettings

from crucible_worker.settings import WorkerAppSettings

logger = logging.getLogger("crucible.worker")

_settings = WorkerAppSettings()


async def ping(ctx: dict[str, Any]) -> dict[str, str]:
    """Round-trip liveness job used by smoke tests."""
    return {
        "pong": datetime.now(UTC).isoformat(),
        "git_sha": _settings.git_sha,
    }


async def on_startup(ctx: dict[str, Any]) -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info(
        "crucible worker started profile=%s git_sha=%s concurrency=%s",
        _settings.profile,
        _settings.git_sha,
        _settings.job_concurrency,
    )


class WorkerSettings:
    """arq configuration object (arq reads class attributes)."""

    functions: ClassVar[list[Any]] = [ping]
    on_startup = on_startup
    redis_settings: ClassVar[RedisSettings] = RedisSettings.from_dsn(_settings.redis_url)
    max_jobs: ClassVar[int] = _settings.job_concurrency
    health_check_interval: ClassVar[int] = 30
