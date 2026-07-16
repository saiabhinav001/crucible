"""Crucible durable data-agent graph.

Boundary rule (import-linter): imports domain + execution + pydantic only. It
defines its own persistence and model-gateway ports; the worker injects concrete
adapters.
"""

from crucible.agent.errors import AgentError, ModelNotConfigured, ModelUnavailable
from crucible.agent.graph import GraphRunner
from crucible.agent.models import FakeModel, OpenAICompatModel
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
    AnalysisPlan,
    Answer,
    AnswerKind,
    GeneratedCode,
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
    "ExecutionEvidence",
    "FakeModel",
    "GeneratedCode",
    "GraphRunner",
    "ModelConfig",
    "ModelGateway",
    "ModelNotConfigured",
    "ModelRole",
    "ModelUnavailable",
    "ModelUsage",
    "Node",
    "OpenAICompatModel",
    "Operation",
    "Provenance",
    "RunView",
    "TerminalReason",
    "VerificationDecision",
    "VerificationVector",
    "resolve_review",
    "run_agent",
]
