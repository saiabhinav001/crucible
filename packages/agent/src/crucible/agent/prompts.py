"""Versioned prompt templates for the real-model path.

Kept as immutable, versioned strings (plan principle 5). The planner and coder
are asked for strict JSON matching the AnalysisPlan / GeneratedCode schemas; the
gateway validates the response against those schemas before a node ever sees it.

The dataset **schema** (column names and dtypes) is placed in the prompt, never
raw cell contents — an uploaded cell is untrusted data and must not become part
of the instruction (threat T2, indirect prompt injection).
"""

from __future__ import annotations

from crucible.agent.state import ColumnView

PLANNER_PROMPT_VERSION = "planner@1"
CODER_PROMPT_VERSION = "coder@1"

_SUPPORTED_OPS = (
    "sum, mean, count, count_distinct, missing_count, max_by_group, min_by_group, abstain"
)

PLANNER_SYSTEM = (
    "You plan a single analysis over a tabular dataset. You may ONLY use these "
    f"operations: {_SUPPORTED_OPS}. If the question cannot be answered by one of "
    "these over the given columns, choose 'abstain' — never invent a column or a "
    "capability. Respond with strict JSON matching the AnalysisPlan schema."
)

CODER_SYSTEM = (
    "You write a single Python program using polars. It must read the dataset "
    "from the path in the CRUCIBLE_DATASET_PATH environment variable, compute the "
    "requested value, and write a JSON object with a 'value' field to the path in "
    "CRUCIBLE_RESULT_PATH. Use no network, no subprocess, and no filesystem access "
    "beyond those two paths. Respond with strict JSON matching the GeneratedCode "
    "schema."
)


def _schema_block(profile: list[ColumnView]) -> str:
    return "\n".join(f"- {c.name}: {c.dtype}" for c in profile)


def render_planner(question: str, profile: list[ColumnView]) -> str:
    return (
        f"{PLANNER_SYSTEM}\n\nDataset columns:\n{_schema_block(profile)}\n\n"
        f"Question: {question}\n\nReturn only the JSON plan."
    )


def render_coder(plan_json: str, profile: list[ColumnView]) -> str:
    return (
        f"{CODER_SYSTEM}\n\nDataset columns:\n{_schema_block(profile)}\n\n"
        f"Plan:\n{plan_json}\n\nReturn only the JSON with the program source."
    )


def render_repair(prior_code: str, error: str) -> str:
    return (
        "The previous program failed. Fix it. Keep the same contract (read "
        "CRUCIBLE_DATASET_PATH, write a JSON object with 'value' to "
        "CRUCIBLE_RESULT_PATH).\n\n"
        f"Previous program:\n{prior_code}\n\nError:\n{error}\n\n"
        "Return only the JSON with the corrected program source."
    )
