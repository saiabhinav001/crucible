"""Retry and confidence policy — a finite-state policy, not an optimistic loop.

Reflection is bounded (master plan §8.3): repair only correctable classes, cap
attempts, and stop on a repeated code/error fingerprint so the loop cannot
oscillate. The confidence policy combines the verification vector into an
answer / review / abstain decision without ever claiming certainty from the mere
fact that code ran.
"""

from __future__ import annotations

import hashlib

from crucible.agent.schemas import VerificationDecision, VerificationVector
from crucible.domain import FailureCategory

MAX_REPAIRS = 2  # after the initial attempt

# Failure categories a repair may address. Everything else is terminal: a policy
# denial, injection suspicion, or exhausted budget is never retried with more
# access (master plan §8.3, failure taxonomy).
_REPAIRABLE: frozenset[FailureCategory] = frozenset(
    {
        FailureCategory.CODE_SYNTAX_ERROR,
        FailureCategory.CODE_RUNTIME_ERROR,
        FailureCategory.SCHEMA_MISMATCH,
        FailureCategory.RESULT_SERIALIZATION_ERROR,
    }
)


def is_repairable(category: FailureCategory | None) -> bool:
    return category in _REPAIRABLE


def fingerprint(code_sha256: str, failure_category: str | None, error_detail: str | None) -> str:
    """A stable signature for an attempt outcome. If the same code produces the
    same error class twice, repairing again is pointless — abstain instead."""
    basis = f"{code_sha256}|{failure_category}|{(error_detail or '')[:200]}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def decide(vector: VerificationVector) -> VerificationDecision:
    """The online confidence policy. Hard requirements gate an answer; a genuine
    ambiguity in the data routes to a human; anything short of the requirements
    abstains rather than guesses."""
    hard_ok = (
        vector.plan_valid
        and vector.columns_exist
        and vector.execution_ok
        and vector.result_schema_valid
        and vector.provenance_present
        and vector.policy_ok
    )
    if not hard_ok:
        return VerificationDecision.ABSTAIN
    if vector.ambiguous:
        return VerificationDecision.REVIEW
    return VerificationDecision.ANSWER
