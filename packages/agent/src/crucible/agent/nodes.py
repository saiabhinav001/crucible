"""Graph nodes implementing the master plan §8.2 node contract.

Each node is a small async function over the shared AgentState that returns the
next Node to run (or Node.DONE when it has set a terminal reason, or a review
interrupt). Nodes read inputs and record evidence through the injected context;
they hold no infrastructure references of their own.
"""

from __future__ import annotations

from dataclasses import dataclass

from crucible.agent import policy
from crucible.agent.models.codegen import generate_source  # noqa: F401 (referenced in prompts)
from crucible.agent.ports import (
    AgentPersistence,
    AttemptRecord,
    DatasetView,
    ModelGateway,
)
from crucible.agent.provenance import build_answer, output_guard
from crucible.agent.schemas import Provenance, VerificationDecision, VerificationVector
from crucible.agent.state import AgentState, ExecutionEvidence, Node, TerminalReason
from crucible.domain import FailureCategory
from crucible.execution import (
    DatasetInput,
    ExecutionLimits,
    ExecutionProgram,
    ExecutionRequest,
    Executor,
)


@dataclass(frozen=True, slots=True)
class NodeResult:
    next: Node
    interrupt: bool = False  # True => waiting for a reviewer; persist and stop


@dataclass(slots=True)
class AgentContext:
    persistence: AgentPersistence
    model: ModelGateway
    executor: Executor
    dataset: DatasetView
    dataset_bytes: bytes
    limits: ExecutionLimits


class AgentNodes:
    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx

    # ------------------------------------------------------------------ helpers
    def _abstain(self, state: AgentState, reason: str) -> NodeResult:
        state.terminal_reason = TerminalReason.ABSTAINED
        state.detail = reason
        return NodeResult(Node.DONE)

    async def _attempt(self, state: AgentState, attempt: AttemptRecord) -> None:
        await self.ctx.persistence.append_attempt(state.run_id, state.organization_id, attempt)

    # -------------------------------------------------------------------- nodes
    async def validate(self, state: AgentState) -> NodeResult:
        if not state.question.strip():
            state.terminal_reason = TerminalReason.POLICY_DENIED
            state.detail = "empty question"
            return NodeResult(Node.DONE)
        return NodeResult(Node.PROFILE)

    async def profile(self, state: AgentState) -> NodeResult:
        state.profile = list(self.ctx.dataset.profile)
        state.dataset_sha256 = self.ctx.dataset.content_sha256
        if not state.profile:
            return self._abstain(state, "the dataset has no readable schema")
        return NodeResult(Node.EXACT_CACHE)

    async def exact_cache(self, state: AgentState) -> NodeResult:
        # Seam only in Phase 4: no cache during baseline-correctness work
        # (master plan §12.3). The exact cache is a Phase 8 deliverable.
        state.cache_key = None
        return NodeResult(Node.ROUTE)

    async def route(self, state: AgentState) -> NodeResult:
        # Static single-policy routing; the measured router is Phase 8.
        return NodeResult(Node.PLAN)

    async def plan(self, state: AgentState) -> NodeResult:
        plan, usage = await self.ctx.model.plan(question=state.question, profile=state.profile)
        await self._attempt(
            state,
            AttemptRecord(
                kind="plan",
                sequence_no=0,
                payload=plan.model_dump(),
                model_provider=usage.provider,
                model_id=usage.model_id,
                cost_usd=usage.cost_usd,
            ),
        )
        if plan.is_abstain:
            return self._abstain(state, plan.rationale or "the question is not supported")

        known = {c.name for c in state.profile}
        missing = [c for c in plan.referenced_columns if c not in known]
        if missing:
            # A plan that references a non-existent column is invalid. One
            # structured-output retry, then abstain (never invent a column).
            if not state.plan_retry_used:
                state.plan_retry_used = True
                return NodeResult(Node.PLAN)
            return self._abstain(state, f"plan referenced unknown columns: {missing}")

        state.plan = plan
        return NodeResult(Node.CODE)

    async def code(self, state: AgentState) -> NodeResult:
        assert state.plan is not None
        code, usage = await self.ctx.model.code(plan=state.plan, profile=state.profile)
        state.code_source = code.source
        state.code_sha256 = ExecutionProgram(code.source).sha256
        await self._attempt(
            state,
            AttemptRecord(
                kind="code",
                sequence_no=0,
                payload={"explanation": code.explanation},
                model_provider=usage.provider,
                model_id=usage.model_id,
                cost_usd=usage.cost_usd,
                source_sha256=state.code_sha256,
            ),
        )
        return NodeResult(Node.EXECUTE)

    async def execute(self, state: AgentState) -> NodeResult:
        assert state.code_source is not None
        request = ExecutionRequest(
            run_id=state.run_id,
            attempt_id=str(state.repair_count + 1),
            program=ExecutionProgram(state.code_source),
            dataset=DatasetInput(
                filename=self.ctx.dataset.filename,
                media_type=self.ctx.dataset.media_type,
                sha256=self.ctx.dataset.content_sha256 or "",
                content=self.ctx.dataset_bytes,
            ),
            limits=self.ctx.limits,
        )
        result = await self.ctx.executor.execute(request)
        category = result.failure_category
        state.last_execution = ExecutionEvidence(
            exit_class=result.exit_class.value,
            ok=result.ok,
            failure_category=category.value if category else None,
            result=result.result,
            stderr_excerpt=result.stderr[:500],
            error_detail=result.error_detail,
            image_ref=result.image_ref,
            backend=self.ctx.executor.backend,
            code_sha256=state.code_sha256 or "",
        )
        await self._attempt(
            state,
            AttemptRecord(
                kind="execute",
                sequence_no=state.repair_count + 1,
                payload={"span": result.span_attributes()},
                exit_class=result.exit_class.value,
                failure_category=category.value if category else None,
                duration_ms=result.usage.wall_ms,
                source_sha256=state.code_sha256,
            ),
        )
        return NodeResult(Node.OBSERVE)

    async def observe(self, state: AgentState) -> NodeResult:
        ev = state.last_execution
        assert ev is not None
        if ev.ok and ev.result is not None:
            return NodeResult(Node.VERIFY)

        category = FailureCategory(ev.failure_category) if ev.failure_category else None
        fp = policy.fingerprint(ev.code_sha256, ev.failure_category, ev.error_detail)
        seen_before = fp in state.fingerprints
        state.fingerprints.append(fp)

        if (
            policy.is_repairable(category)
            and state.repair_count < policy.MAX_REPAIRS
            and not seen_before
        ):
            return NodeResult(Node.REFLECT)

        reason = self._abstain_reason(ev, category, seen_before)
        return self._abstain(state, reason)

    @staticmethod
    def _abstain_reason(
        ev: ExecutionEvidence, category: FailureCategory | None, seen_before: bool
    ) -> str:
        if seen_before:
            return "the same failure recurred after repair; stopping to avoid an oscillation"
        if not policy.is_repairable(category):
            return f"non-repairable failure: {ev.exit_class}"
        return f"repair budget exhausted after {policy.MAX_REPAIRS} attempts ({ev.exit_class})"

    async def reflect(self, state: AgentState) -> NodeResult:
        assert state.plan is not None and state.code_source is not None and state.last_execution
        ev = state.last_execution
        repaired, usage = await self.ctx.model.repair(
            plan=state.plan,
            profile=state.profile,
            prior_code=state.code_source,
            error=ev.error_detail or ev.stderr_excerpt or ev.exit_class,
        )
        state.repair_count += 1
        state.code_source = repaired.source
        state.code_sha256 = ExecutionProgram(repaired.source).sha256
        await self._attempt(
            state,
            AttemptRecord(
                kind="repair",
                sequence_no=state.repair_count,
                payload={"explanation": repaired.explanation},
                model_provider=usage.provider,
                model_id=usage.model_id,
                cost_usd=usage.cost_usd,
                source_sha256=state.code_sha256,
            ),
        )
        # The repaired program is the next attempt: go straight to Execute.
        return NodeResult(Node.EXECUTE)

    async def verify(self, state: AgentState) -> NodeResult:
        assert state.plan is not None and state.last_execution is not None
        ev = state.last_execution
        result = ev.result or {}
        known = {c.name for c in state.profile}

        vector = VerificationVector(
            plan_valid=not state.plan.is_abstain,
            columns_exist=all(c in known for c in state.plan.referenced_columns),
            execution_ok=ev.ok,
            result_schema_valid="value" in result and result.get("value") is not None,
            # A full-table operation (e.g. a row count) legitimately uses no
            # columns; its provenance is the operation itself over the dataset.
            provenance_present=bool(
                result.get("operation")
                or result.get("columns_used")
                or state.plan.referenced_columns
            ),
            policy_ok=ev.exit_class != "policy_violation",
            ambiguous=bool(result.get("ambiguous")),
        )
        vector.decision = policy.decide(vector)
        state.verification = vector
        await self._attempt(
            state, AttemptRecord(kind="verify", sequence_no=0, payload=vector.model_dump())
        )

        if vector.decision is VerificationDecision.ANSWER:
            return NodeResult(Node.SYNTHESIZE)
        if vector.decision is VerificationDecision.REVIEW:
            return NodeResult(Node.HUMAN_REVIEW)
        return self._abstain(state, "verification did not meet the answer threshold")

    async def human_review(self, state: AgentState) -> NodeResult:
        if state.review_decision is None:
            # Interrupt: the run waits for a reviewer. The runner persists at
            # this node and stops without finalizing.
            return NodeResult(Node.HUMAN_REVIEW, interrupt=True)
        if state.review_decision == "approve":
            return NodeResult(Node.SYNTHESIZE)
        return self._abstain(state, "a reviewer rejected the answer")

    async def synthesize(self, state: AgentState) -> NodeResult:
        assert state.plan is not None and state.last_execution is not None
        ev = state.last_execution
        result = ev.result or {}
        raw_cols = result.get("columns_used")
        source_cols = raw_cols if isinstance(raw_cols, list) else state.plan.referenced_columns
        columns = [str(c) for c in source_cols]
        provenance = Provenance(
            dataset_version_id=state.dataset_version_id,
            dataset_sha256=state.dataset_sha256,
            operation=state.plan.operation.value,
            columns_used=columns,
            code_sha256=state.code_sha256 or "",
            attempt_count=state.repair_count + 1,
            executor_backend=ev.backend,
            image_ref=ev.image_ref,
        )
        state.answer = build_answer(plan=state.plan, result=result, provenance=provenance)
        return NodeResult(Node.OUTPUT_GUARD)

    async def output_guard(self, state: AgentState) -> NodeResult:
        assert state.answer is not None
        ok, reason = output_guard(state.answer)
        if not ok:
            state.answer = None
            return self._abstain(state, f"output guard rejected the answer: {reason}")
        state.terminal_reason = TerminalReason.ANSWERED
        return NodeResult(Node.DONE)


DISPATCH = {
    Node.VALIDATE: "validate",
    Node.PROFILE: "profile",
    Node.EXACT_CACHE: "exact_cache",
    Node.ROUTE: "route",
    Node.PLAN: "plan",
    Node.CODE: "code",
    Node.EXECUTE: "execute",
    Node.OBSERVE: "observe",
    Node.REFLECT: "reflect",
    Node.VERIFY: "verify",
    Node.HUMAN_REVIEW: "human_review",
    Node.SYNTHESIZE: "synthesize",
    Node.OUTPUT_GUARD: "output_guard",
}
