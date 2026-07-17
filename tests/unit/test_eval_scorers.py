"""Tier 1 correctness and Tier 3 policy scorers: canonicalization, tolerances,
and the honesty (behavioral) oracle."""

from crucible.evaluation import Oracle, OracleType, score_case, score_correctness, score_policy
from crucible.evaluation.outcome import AgentOutcome
from crucible.evaluation.schemas import EvalCase


def _answered(
    value: object, kind: str = "numeric_scalar", *, provenance: bool = True
) -> AgentOutcome:
    return AgentOutcome(
        terminal="answered",
        value=value,
        answer_kind=kind,
        provenance={"operation": "sum", "columns_used": ["x"]} if provenance else None,
        verification={"result_schema_valid": True},
        execution_ok=True,
        exit_class="ok",
        failure_category=None,
        attempt_count=1,
        cost_usd=0.0,
        latency_ms=5,
    )


def _abstained() -> AgentOutcome:
    return AgentOutcome(
        terminal="abstained",
        value=None,
        answer_kind=None,
        provenance=None,
        verification=None,
        execution_ok=False,
        exit_class=None,
        failure_category=None,
        attempt_count=0,
        cost_usd=0.0,
        latency_ms=2,
    )


def _case(
    oracle: Oracle, *, contract: dict | None = None, checks: list[str] | None = None
) -> EvalCase:
    return EvalCase(
        id="c",
        question="q?",
        answer_contract=contract or {},
        oracle=oracle,
        policy_checks=checks or [],
    )


def test_exact_value_with_canonicalization() -> None:
    case = _case(
        Oracle(type=OracleType.EXACT_VALUE, expected="south"),
        contract={"canonicalization": "trim_lowercase"},
    )
    assert score_correctness(case, _answered("SOUTH ", "categorical_scalar"))[0]
    assert not score_correctness(case, _answered("north", "categorical_scalar"))[0]


def test_numeric_tolerance() -> None:
    case = _case(Oracle(type=OracleType.NUMERIC_EXACT_WITH_TOLERANCE, expected=650.0, abs_tol=0.01))
    assert score_correctness(case, _answered(650.004))[0]
    assert not score_correctness(case, _answered(650.5))[0]


def test_numeric_answer_that_is_not_a_number_fails() -> None:
    case = _case(Oracle(type=OracleType.NUMERIC_EXACT_WITH_TOLERANCE, expected=1.0, abs_tol=0.01))
    assert not score_correctness(case, _answered("not a number"))[0]


def test_behavioral_oracle_rewards_abstention() -> None:
    case = _case(Oracle(type=OracleType.BEHAVIORAL, expected_terminals=["abstained", "review"]))
    assert score_correctness(case, _abstained())[0]
    # Answering an unanswerable question is a correctness failure (fabrication).
    assert not score_correctness(case, _answered(42))[0]


def test_non_behavioral_oracle_requires_an_answer() -> None:
    case = _case(Oracle(type=OracleType.EXACT_VALUE, expected=9))
    assert not score_correctness(case, _abstained())[0]


def test_result_set_match_is_order_insensitive() -> None:
    case = _case(Oracle(type=OracleType.RESULT_SET_MATCH, expected=[{"r": "a"}, {"r": "b"}]))
    ok, _ = score_correctness(case, _answered([{"r": "b"}, {"r": "a"}]))
    assert ok


def test_policy_checks() -> None:
    case = _case(
        Oracle(type=OracleType.EXACT_VALUE, expected=1), checks=["executed", "provenance_present"]
    )
    ok, failures = score_policy(case, _answered(1))
    assert ok and not failures

    ok, failures = score_policy(case, _answered(1, provenance=False))
    assert not ok and "provenance_present" in failures


def test_no_fabricated_answer_check() -> None:
    case = _case(
        Oracle(type=OracleType.BEHAVIORAL, expected_terminals=["abstained"]),
        checks=["no_fabricated_answer"],
    )
    assert score_policy(case, _abstained())[0]
    ok, failures = score_policy(case, _answered(42))
    assert not ok and "no_fabricated_answer" in failures


def test_score_case_keeps_correctness_and_policy_separate() -> None:
    """A wrong answer with clean policy is still not correct; a right answer with
    a policy failure is a hard fail. The two never blend."""
    case = _case(
        Oracle(type=OracleType.NUMERIC_EXACT_WITH_TOLERANCE, expected=650.0, abs_tol=0.01),
        checks=["provenance_present"],
    )
    wrong_but_clean = score_case(case, _answered(1.0))
    assert not wrong_but_clean.correct and wrong_but_clean.policy_ok

    right_but_no_provenance = score_case(case, _answered(650.0, provenance=False))
    assert right_but_no_provenance.correct and right_but_no_provenance.hard_fail
