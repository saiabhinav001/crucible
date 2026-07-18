"""Crucible durable data-agent graph.

Boundary rule (import-linter): imports domain + execution + pydantic only. It
defines its own persistence and model-gateway ports; the worker injects concrete
adapters.
"""

from crucible.agent.errors import AgentError, ModelNotConfigured, ModelUnavailable
from crucible.agent.evaluate import EphemeralPersistence, EvalTrace, run_to_completion
from crucible.agent.graph import GraphRunner
from crucible.agent.models import (
    JUDGE_RUBRIC_VERSION,
    FakeJudge,
    FakeModel,
    Judge,
    OpenAICompatJudge,
    OpenAICompatModel,
)
from crucible.agent.nodes import AgentContext, AgentNodes
from crucible.agent.orchestrator import resolve_review, run_agent
from crucible.agent.ports import (
    AgentPersistence,
    AttemptRecord,
    DatasetView,
    ModelConfig,
    ModelGateway,
    ModelRole,
    ModelUsage,
    RunView,
)
from crucible.agent.schemas import (
    JUDGE_DIMENSIONS,
    AnalysisPlan,
    Answer,
    AnswerKind,
    GeneratedCode,
    JudgeRubricScore,
    Operation,
    Provenance,
    VerificationDecision,
    VerificationVector,
)
from crucible.agent.state import (
    AgentState,
    ColumnView,
    ExecutionEvidence,
    Node,
    TerminalReason,
)

__all__ = [
    "JUDGE_DIMENSIONS",
    "JUDGE_RUBRIC_VERSION",
    "AgentContext",
    "AgentError",
    "AgentNodes",
    "AgentPersistence",
    "AgentState",
    "AnalysisPlan",
    "Answer",
    "AnswerKind",
    "AttemptRecord",
    "ColumnView",
    "DatasetView",
    "EphemeralPersistence",
    "EvalTrace",
    "ExecutionEvidence",
    "FakeJudge",
    "FakeModel",
    "GeneratedCode",
    "GraphRunner",
    "Judge",
    "JudgeRubricScore",
    "ModelConfig",
    "ModelGateway",
    "ModelNotConfigured",
    "ModelRole",
    "ModelUnavailable",
    "ModelUsage",
    "Node",
    "OpenAICompatJudge",
    "OpenAICompatModel",
    "Operation",
    "Provenance",
    "RunView",
    "TerminalReason",
    "VerificationDecision",
    "VerificationVector",
    "resolve_review",
    "run_agent",
    "run_to_completion",
]
