"""arq worker entry point.

Run:           uv run arq crucible_worker.main.WorkerSettings
Health check:  uv run arq --check crucible_worker.main.WorkerSettings
(arq writes a heartbeat key to Redis; --check exits nonzero when stale — used
as the container healthcheck in compose.yaml.)

Jobs: `profile_dataset_version` (Phase 2) and `execute_run` (durable lifecycle
now, real agent in Phase 4).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, ClassVar

from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import async_sessionmaker

from crucible.db import create_async_engine_from_url, install_selector_event_loop_policy
from crucible.storage import S3ObjectStorage
from crucible_worker.agent_runtime import build_limits, build_model
from crucible_worker.executor import build_executor
from crucible_worker.jobs.datasets import profile_dataset_version
from crucible_worker.jobs.runs import execute_run, resolve_run_review
from crucible_worker.jobs.sandbox import sandbox_selfcheck
from crucible_worker.settings import WorkerAppSettings

install_selector_event_loop_policy()  # Windows dev only; no-op elsewhere

logger = logging.getLogger("crucible.worker")

_settings = WorkerAppSettings()


async def ping(ctx: dict[str, Any]) -> dict[str, str]:
    """Round-trip liveness job used by smoke tests."""
    return {"pong": datetime.now(UTC).isoformat(), "git_sha": _settings.git_sha}


async def on_startup(ctx: dict[str, Any]) -> None:
    logging.basicConfig(level=logging.INFO)
    engine = create_async_engine_from_url(_settings.database_url)
    ctx["engine"] = engine
    ctx["session_factory"] = async_sessionmaker(engine, expire_on_commit=False)
    ctx["storage"] = S3ObjectStorage(
        bucket=_settings.s3_bucket,
        endpoint_url=_settings.s3_endpoint_url,
        region=_settings.s3_region,
        access_key=_settings.s3_access_key,
        secret_key=_settings.s3_secret_key,
    )
    executor = build_executor(_settings)
    ctx["executor"] = executor
    ctx["model"] = build_model(_settings)
    ctx["limits"] = build_limits(_settings)
    logger.info(
        "crucible worker started profile=%s git_sha=%s concurrency=%s executor=%s model=%s",
        _settings.profile,
        _settings.git_sha,
        _settings.job_concurrency,
        executor.backend,
        _settings.model_backend,
    )


async def on_shutdown(ctx: dict[str, Any]) -> None:
    engine = ctx.get("engine")
    if engine is not None:
        await engine.dispose()


class WorkerSettings:
    """arq configuration object (arq reads class attributes)."""

    functions: ClassVar[list[Any]] = [
        ping,
        profile_dataset_version,
        execute_run,
        resolve_run_review,
        sandbox_selfcheck,
    ]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings: ClassVar[RedisSettings] = RedisSettings.from_dsn(_settings.redis_url)
    max_jobs: ClassVar[int] = _settings.job_concurrency
    health_check_interval: ClassVar[int] = 30
    # A job that dies mid-flight must not leave a run stuck: arq retries, and
    # the compare-and-set transitions make re-delivery safe.
    max_tries: ClassVar[int] = 3
