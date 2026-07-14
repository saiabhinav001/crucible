"""Crucible domain layer: pure types only.

Boundary rule (ADR-001, enforced by import-linter): this package imports
nothing but the standard library. No FastAPI, SQLAlchemy, Pydantic, Redis,
or sibling layers.
"""

from crucible.domain.errors import DomainError, ProblemDetail
from crucible.domain.health import BuildInfo, ComponentHealth, HealthState, SystemStatus
from crucible.domain.runs import TERMINAL_RUN_STATES, FailureCategory, RunStatus

__all__ = [
    "TERMINAL_RUN_STATES",
    "BuildInfo",
    "ComponentHealth",
    "DomainError",
    "FailureCategory",
    "HealthState",
    "ProblemDetail",
    "RunStatus",
    "SystemStatus",
]
