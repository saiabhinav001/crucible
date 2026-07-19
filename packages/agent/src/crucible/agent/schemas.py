"""Typed structured outputs and evidence for the agent graph.

These are the contracts at the boundaries between nodes. Model output (plan,
code) is untrusted until it validates against these schemas, and the verifier
records a structured vector rather than a single opaque "confidence" number.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Operation(StrEnum):
    """The bounded set of analyses the v1 workload supports. Anything outside
    this set becomes an honest abstention, never a guess."""

    SUM = "sum"
    MEAN = "mean"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    MISSING_COUNT = "missing_count"
    MAX_BY_GROUP = "max_by_group"
    MIN_BY_GROUP = "min_by_group"
    ABSTAIN = "abstain"  # the model's honest "I cannot answer this over this data"


class AnswerKind(StrEnum):
    NUMERIC_SCALAR = "numeric_scalar"
    INTEGER_SCALAR = "integer_scalar"
    CATEGORICAL_SCALAR = "categorical_scalar"
    ABSTAIN = "abstain"


class Filter(BaseModel):
    column: str
    op: str = Field(default="==", pattern=r"^(==|!=|>|>=|<|<=)$")
    value: str


class AnalysisPlan(BaseModel):
    """A reviewable plan, not free-form reasoning (master plan §8.3)."""

    operation: Operation
    answer_kind: AnswerKind
    target_column: str | None = None
    group_column: str | None = None
    filter: Filter | None = None
    referenced_columns: list[str] = Field(default_factory=list)
    rationale: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @property
    def is_abstain(self) -> bool:
        return self.operation is Operation.ABSTAIN or self.answer_kind is AnswerKind.ABSTAIN


class GeneratedCode(BaseModel):
    """Untrusted Python source produced by the coder role."""

    source: str
    explanation: str = ""


class VerificationDecision(StrEnum):
    ANSWER = "answer"
    REVIEW = "review"
    ABSTAIN = "abstain"


class VerificationVector(BaseModel):
    """Structured evidence combined into an answer/review/abstain decision.

    This is *online serving* verification: it establishes execution success,
    schema/provenance consistency, and policy compliance. It deliberately does
    not claim the answer is mathematically correct just because code ran
    (master plan §8.3) — that certainty only exists offline against a known
    reference (Phase 5).
    """

    plan_valid: bool = False
    columns_exist: bool = False
    execution_ok: bool = False
    result_schema_valid: bool = False
    provenance_present: bool = False
    policy_ok: bool = False
    ambiguous: bool = False  # e.g. a tie in a max-by-group — the data is unclear
    decision: VerificationDecision = VerificationDecision.ABSTAIN
    reasons: list[str] = Field(default_factory=list)


class Provenance(BaseModel):
    """Points the answer at the actual computed result and how it was produced."""

    dataset_version_id: str
    dataset_sha256: str | None = None
    operation: str = ""
    columns_used: list[str] = Field(default_factory=list)
    code_sha256: str = ""
    attempt_count: int = 0
    executor_backend: str = ""
    image_ref: str = ""


class Answer(BaseModel):
    answer_kind: AnswerKind
    value: object = None
    text: str = ""
    provenance: Provenance
    limitations: str = ""
    # True when this answer was replayed from the exact cache (Phase 8). The
    # provenance still points at the original computation's evidence.
    cached: bool = False


class JudgeRubricScore(BaseModel):
    """The LLM judge's narrow, ordinal assessment of *explanation quality* only
    (master plan §10.5). Each dimension is 0/1/2. The judge never scores the
    numeric answer — that has a deterministic oracle — and can never override it.
    """

    groundedness: int = Field(ge=0, le=2)
    provenance: int = Field(ge=0, le=2)
    usefulness: int = Field(ge=0, le=2)
    uncertainty: int = Field(ge=0, le=2)
    rationale: str = ""

    @property
    def total(self) -> int:
        return self.groundedness + self.provenance + self.usefulness + self.uncertainty

    def dimension(self, name: str) -> int:
        return int(getattr(self, name))


JUDGE_DIMENSIONS = ("groundedness", "provenance", "usefulness", "uncertainty")
