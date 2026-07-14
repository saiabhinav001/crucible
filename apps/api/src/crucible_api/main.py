"""API application factory.

Run locally:  uv run uvicorn --factory crucible_api.main:create_app --reload
Endpoints (Phase 1 scope — health/config path only):
  GET /healthz  liveness (no dependencies touched)
  GET /readyz   readiness via injected HealthProbes (503 when not ready)
  GET /version  build identity: git SHA, version, profile
Errors render as RFC 9457 application/problem+json.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import asdict

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from crucible.application import GetSystemStatus, HealthProbe
from crucible.db import create_async_engine_from_url
from crucible.domain import ProblemDetail
from crucible_api.probes import DatabaseProbe, RedisProbe
from crucible_api.settings import ApiSettings, resolve_build_info

PROBLEM_CONTENT_TYPE = "application/problem+json"


def create_app(
    settings: ApiSettings | None = None,
    probes: Sequence[HealthProbe] | None = None,
) -> FastAPI:
    cfg = settings or ApiSettings()
    build = resolve_build_info(cfg)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if probes is not None:
            app.state.probes = list(probes)  # test/dev injection
            yield
            return
        engine = create_async_engine_from_url(cfg.database_url)
        redis_client = aioredis.from_url(cfg.redis_url)  # type: ignore[no-untyped-call]
        app.state.probes = [DatabaseProbe(engine), RedisProbe(redis_client)]
        try:
            yield
        finally:
            await redis_client.aclose()
            await engine.dispose()

    app = FastAPI(
        title="Crucible API",
        version=cfg.app_version,
        description="Evaluation and reliability platform for LLM agents.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/readyz", tags=["health"])
    async def readyz(request: Request) -> JSONResponse:
        status = await GetSystemStatus(request.app.state.probes)()
        body = {
            "state": status.state.value,
            "components": [asdict(c) for c in status.components],
        }
        return JSONResponse(body, status_code=200 if status.ready else 503)

    @app.get("/version", tags=["health"])
    async def version() -> dict[str, str]:
        return {k: str(v) for k, v in asdict(build).items()}

    @app.exception_handler(StarletteHTTPException)
    async def http_problem(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        problem = ProblemDetail(
            type="about:blank",
            title=str(exc.detail),
            status=exc.status_code,
            detail=str(exc.detail),
            request_id=request.headers.get("x-request-id", ""),
        )
        return JSONResponse(
            problem.to_dict(), status_code=exc.status_code, media_type=PROBLEM_CONTENT_TYPE
        )

    @app.exception_handler(RequestValidationError)
    async def validation_problem(request: Request, exc: RequestValidationError) -> JSONResponse:
        problem = ProblemDetail(
            type="https://crucible.dev/problems/validation",
            title="Request validation failed",
            status=422,
            detail="One or more request fields are invalid.",
            request_id=request.headers.get("x-request-id", ""),
        )
        return JSONResponse(
            {**problem.to_dict(), "errors": exc.errors()},
            status_code=422,
            media_type=PROBLEM_CONTENT_TYPE,
        )

    return app
