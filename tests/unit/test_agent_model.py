"""FakeModel planner intent parsing, deterministic codegen, and the OpenAI-
compatible adapter's pure parsing + deny-by-default behavior."""

import asyncio

import pytest

from crucible.agent import AnswerKind, ColumnView, FakeModel, ModelNotConfigured, Operation
from crucible.agent.models.codegen import generate_source
from crucible.agent.models.openai_compat import OpenAICompatModel, parse_plan

PROFILE = [
    ColumnView(name="region", dtype="String"),
    ColumnView(name="product", dtype="String"),
    ColumnView(name="amount", dtype="Float64"),
    ColumnView(name="quantity", dtype="Int64"),
    ColumnView(name="customer_id", dtype="String"),
]


def _plan(question: str):
    return asyncio.run(FakeModel().plan(question=question, profile=PROFILE))[0]


def test_planner_detects_sum() -> None:
    plan = _plan("What is the total amount?")
    assert plan.operation is Operation.SUM
    assert plan.target_column == "amount"
    assert plan.answer_kind is AnswerKind.NUMERIC_SCALAR


def test_planner_detects_mean() -> None:
    plan = _plan("What is the average amount?")
    assert plan.operation is Operation.MEAN
    assert plan.target_column == "amount"


def test_planner_detects_distinct_with_plural() -> None:
    plan = _plan("How many distinct customers are there?")
    assert plan.operation is Operation.COUNT_DISTINCT
    assert plan.target_column == "customer_id"


def test_planner_detects_missing() -> None:
    plan = _plan("How many rows are missing a region?")
    assert plan.operation is Operation.MISSING_COUNT
    assert plan.target_column == "region"


def test_planner_detects_max_by_group() -> None:
    plan = _plan("Which region had the highest total amount?")
    assert plan.operation is Operation.MAX_BY_GROUP
    assert plan.group_column == "region"
    assert plan.target_column == "amount"


def test_planner_detects_group_count_without_numeric_target() -> None:
    plan = _plan("Which product appears the most?")
    assert plan.operation is Operation.MAX_BY_GROUP
    assert plan.group_column == "product"
    assert plan.target_column is None


def test_planner_plain_count() -> None:
    plan = _plan("How many orders are there?")
    assert plan.operation is Operation.COUNT
    assert plan.answer_kind is AnswerKind.INTEGER_SCALAR


def test_planner_abstains_on_unsupported_question() -> None:
    plan = _plan("Predict next quarter's revenue and explain why.")
    assert plan.is_abstain


def test_planner_abstains_when_no_column_matches() -> None:
    plan = _plan("What is the total elevation?")
    assert plan.is_abstain


@pytest.mark.parametrize(
    "question",
    [
        "What is the total amount?",
        "How many distinct customers?",
        "Which region had the highest amount?",
        "How many orders?",
        "average quantity",
        "how many rows are missing amount",
    ],
)
def test_generated_code_compiles(question: str) -> None:
    """Every plan the fake model can produce must compile to valid Python."""
    plan = _plan(question)
    source = generate_source(plan)
    compile(source, "<generated>", "exec")  # raises SyntaxError on bad codegen
    assert "CRUCIBLE_RESULT_PATH" in source


def test_codegen_escapes_hostile_column_names() -> None:
    """A malicious column name cannot break out of the generated string literal
    (repr neutralizes it; the sandbox contains anything anyway)."""
    hostile = [ColumnView(name="'); import os; os.system('x", dtype="Float64")]
    plan = asyncio.run(FakeModel().plan(question="total amount", profile=PROFILE))[0]
    plan.target_column = hostile[0].name
    plan.operation = Operation.SUM
    source = generate_source(plan)
    compile(source, "<generated>", "exec")  # still valid Python
    assert "os.system" not in source.replace(repr(hostile[0].name), "")


# ------------------------------------------------------- openai-compatible path


def test_parse_plan_validates_into_schema() -> None:
    plan = parse_plan(
        '{"operation": "sum", "answer_kind": "numeric_scalar", "target_column": "amount"}'
    )
    assert plan.operation is Operation.SUM


def test_parse_plan_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        parse_plan("[1, 2, 3]")


def test_openai_model_is_deny_by_default() -> None:
    model = OpenAICompatModel()  # unconfigured
    assert not model.configured
    with pytest.raises(ModelNotConfigured):
        asyncio.run(model.plan(question="total amount", profile=PROFILE))
