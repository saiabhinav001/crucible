"""Ports (interfaces) that adapters implement. Transport/infra code depends on
these; this layer never depends on transport/infra."""

from __future__ import annotations

from typing import Protocol

from crucible.domain import ComponentHealth


class HealthProbe(Protocol):
    """Probes one dependency for readiness. Implementations must never raise:
    a failing dependency is reported as ComponentHealth(state=DOWN)."""

    @property
    def name(self) -> str: ...

    async def check(self) -> ComponentHealth: ...
