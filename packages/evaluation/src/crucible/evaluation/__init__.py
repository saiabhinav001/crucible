"""Crucible offline evaluation harness.

Boundary rule (import-linter): imports domain, execution, and agent (to run the
real graph) plus pydantic/pyyaml. It never imports db/api/worker/application —
the evaluation plane is decoupled from the serving plane.
"""

from crucible.evaluation.comparator import (
    GateDecision,
    GateStatus,
    evaluate_gate,
    paired_bootstrap_ci,
)
from crucible.evaluation.config import EvalConfig
from crucible.evaluation.governance import (
    Baseline,
    baseline_from_result,
    load_baseline,
    write_baseline,
)
from crucible.evaluation.loader import (
    FixtureIntegrityError,
    load_fixture,
    load_suite,
    repo_evals_dir,
)
from crucible.evaluation.outcome import AgentOutcome, outcome_from_trace
from crucible.evaluation.report import build_report, render_markdown
from crucible.evaluation.runner import ExperimentResult, ExperimentRunner
from crucible.evaluation.schemas import (
    EvalCase,
    EvalFixture,
    EvalSuite,
    Oracle,
    OracleType,
)
from crucible.evaluation.scorers import (
    SCORER_VERSION,
    CaseScore,
    score_case,
    score_correctness,
    score_policy,
)

__all__ = [
    "SCORER_VERSION",
    "AgentOutcome",
    "Baseline",
    "CaseScore",
    "EvalCase",
    "EvalConfig",
    "EvalFixture",
    "EvalSuite",
    "ExperimentResult",
    "ExperimentRunner",
    "FixtureIntegrityError",
    "GateDecision",
    "GateStatus",
    "Oracle",
    "OracleType",
    "baseline_from_result",
    "build_report",
    "evaluate_gate",
    "load_baseline",
    "load_fixture",
    "load_suite",
    "outcome_from_trace",
    "paired_bootstrap_ci",
    "render_markdown",
    "repo_evals_dir",
    "score_case",
    "score_correctness",
    "score_policy",
    "write_baseline",
]
