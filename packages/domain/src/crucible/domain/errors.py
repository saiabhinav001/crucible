"""Error contracts: RFC 9457-style problem details as a pure value object."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ProblemDetail:
    """Transport-agnostic problem description; apps render it as
    application/problem+json. `detail` must always be safe to show a user."""

    type: str
    title: str
    status: int
    detail: str
    request_id: str = ""
    retryable: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class DomainError(Exception):
    """Base for errors that carry a user-safe problem detail."""

    def __init__(self, problem: ProblemDetail) -> None:
        super().__init__(problem.title)
        self.problem = problem
