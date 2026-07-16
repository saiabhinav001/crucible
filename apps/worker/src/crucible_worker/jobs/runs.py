"""Run execution job.

Phase 4: the durable data-agent. This job hands the run to the agent graph,
which claims a queued run (or resumes a RUNNING run a prior worker left
mid-flight), plans → generates code → executes it in the sandbox → observes →
repairs (bounded) → verifies → synthesizes an answer with provenance, or
abstains truthfully, or routes to human review.

The graph is the only thing that transitions run status, so `agent_runs` remains
the single source of truth (ADR-008). This job is a thin delegator; the
resume-after-restart logic lives in the orchestrator.
"""

from __future__ import annotations

import logging
from typing import Any

from crucible.agent import resolve_review, run_agent
from crucible_worker.agent_runtime import SqlAgentPersistence

logger = logging.getLogger("crucible.worker.runs")


async def execute_run(ctx: dict[str, Any], run_id: str) -> dict[str, str]:
    persistence = SqlAgentPersistence(ctx["session_factory"], ctx["storage"])
    outcome = await run_agent(
        persistence,
        model=ctx["model"],
        executor=ctx["executor"],
        limits=ctx["limits"],
        run_id=run_id,
    )
    logger.info("execute_run: run %s -> %s", run_id, outcome)
    return {"result": outcome}


async def resolve_run_review(ctx: dict[str, Any], run_id: str, approve: bool) -> dict[str, str]:
    """Resume a run waiting for a reviewer (approve → synthesize, reject →
    abstain). Enqueued by the API when a reviewer acts."""
    persistence = SqlAgentPersistence(ctx["session_factory"], ctx["storage"])
    outcome = await resolve_review(
        persistence,
        model=ctx["model"],
        executor=ctx["executor"],
        limits=ctx["limits"],
        run_id=run_id,
        approve=approve,
    )
    logger.info("resolve_run_review: run %s approve=%s -> %s", run_id, approve, outcome)
    return {"result": outcome}
