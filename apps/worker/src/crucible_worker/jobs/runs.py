"""Run execution job.

**Phase 2 scope.** The durable run lifecycle, event stream, cancellation, and
state-machine guards are real. The agent itself is not — LangGraph, the
planner, the sandbox, and verification arrive in Phase 4 (ADR-004, ADR-003).

Until then this job claims the run, honors cancellation, and terminates
truthfully in `abstained` with an explicit reason. It never fabricates an
answer to look finished: an unimplemented agent that returns a plausible
result is precisely the failure mode this project exists to prevent.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from crucible.db import SqlRunRepository
from crucible.domain import RunEventType, RunStatus

logger = logging.getLogger("crucible.worker.runs")

AGENT_NOT_IMPLEMENTED = (
    "The agent workflow is not implemented yet (planned for Phase 4). The run was "
    "accepted, claimed, and terminated without producing an answer."
)


async def execute_run(ctx: dict[str, Any], run_id: str) -> dict[str, str]:
    factory: async_sessionmaker[Any] = ctx["session_factory"]
    rid = uuid.UUID(run_id)

    async with factory() as session:
        repo = SqlRunRepository(session)
        run = await repo.get_run_unscoped(rid)
        if run is None:
            logger.warning("execute_run: run %s not found", run_id)
            return {"result": "not_found"}

        if run.cancel_requested_at is not None:
            return await _finish(
                session,
                repo,
                rid,
                current=run.status,
                target=RunStatus.CANCELLED,
                detail="Cancelled before execution started.",
            )

        # Compare-and-set claim: if another worker already took this run (or a
        # cancel landed first), we stop rather than force the transition.
        claimed = await repo.transition(
            run_id=rid, expected=RunStatus.QUEUED, target=RunStatus.RUNNING
        )
        if claimed is None:
            await session.rollback()
            logger.info("execute_run: run %s already claimed or terminal", run_id)
            return {"result": "not_claimable"}

        await repo.append_event(
            run_id=rid,
            event_type=RunEventType.CLAIMED,
            payload={"status": RunStatus.RUNNING.value},
        )
        await session.commit()

    # --- Phase 4 replaces this block with the LangGraph workflow. Every node
    # --- will check the cancellation flag at its checkpoint, exactly as here.
    async with factory() as session:
        repo = SqlRunRepository(session)
        run = await repo.get_run_unscoped(rid)
        assert run is not None

        if run.cancel_requested_at is not None:
            return await _finish(
                session,
                repo,
                rid,
                current=RunStatus.RUNNING,
                target=RunStatus.CANCELLED,
                detail="Cancelled while running.",
            )

        return await _finish(
            session,
            repo,
            rid,
            current=RunStatus.RUNNING,
            target=RunStatus.ABSTAINED,
            detail=AGENT_NOT_IMPLEMENTED,
        )


async def _finish(
    session: Any,
    repo: SqlRunRepository,
    run_id: uuid.UUID,
    *,
    current: RunStatus,
    target: RunStatus,
    detail: str,
) -> dict[str, str]:
    updated = await repo.transition(
        run_id=run_id, expected=current, target=target, terminal_detail=detail
    )
    if updated is None:
        await session.rollback()
        return {"result": "lost_race"}
    await repo.append_event(
        run_id=run_id,
        event_type=RunEventType.TERMINAL,
        payload={"status": target.value, "detail": detail},
    )
    await session.commit()
    logger.info("execute_run: run %s -> %s", run_id, target.value)
    return {"result": target.value}
