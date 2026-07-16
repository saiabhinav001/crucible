"""Deterministic polars code generation from a validated plan.

Shared by the fake model (which uses it directly) and available as a reference
for the real-model path's few-shot prompt. Column names and filter values come
from untrusted uploaded data, so every embedded string uses `repr()` — a
hostile column name cannot break out of the generated source. (And even if it
could, the sandbox contains it: this is defense in depth, not the boundary.)

The generated program obeys the sandbox contract: read the dataset from
CRUCIBLE_DATASET_PATH, write a JSON object with a `value` field to
CRUCIBLE_RESULT_PATH. For grouped operations it also reports `ambiguous` when the
top two groups tie, so the verifier can route a genuinely unclear answer to
human review instead of picking arbitrarily.
"""

from __future__ import annotations

from crucible.agent.schemas import AnalysisPlan, Operation

_HEADER = (
    "import json, os\n"
    "import polars as pl\n"
    "df = pl.read_csv(os.environ['CRUCIBLE_DATASET_PATH'], infer_schema_length=10000)\n"
)


def _emit(body: str) -> str:
    return (
        _HEADER + body + "\nwith open(os.environ['CRUCIBLE_RESULT_PATH'], 'w') as _fh:\n"
        "    json.dump(result, _fh, default=str)\n"
    )


def generate_source(plan: AnalysisPlan) -> str:
    op = plan.operation
    col = plan.target_column
    group = plan.group_column

    if op is Operation.SUM and col:
        return _emit(
            f"value = float(df[{col!r}].sum())\n"
            f"result = {{'value': value, 'operation': 'sum', 'columns_used': [{col!r}]}}\n"
        )
    if op is Operation.MEAN and col:
        return _emit(
            f"value = float(df[{col!r}].mean())\n"
            f"result = {{'value': value, 'operation': 'mean', 'columns_used': [{col!r}]}}\n"
        )
    if op is Operation.COUNT_DISTINCT and col:
        return _emit(
            f"value = int(df[{col!r}].n_unique())\n"
            f"result = {{'value': value, 'operation': 'count_distinct', 'columns_used': [{col!r}]}}\n"
        )
    if op is Operation.MISSING_COUNT and col:
        return _emit(
            f"s = df[{col!r}]\n"
            "missing = int((s.is_null() | (s.cast(pl.Utf8, strict=False) == '')).sum())\n"
            f"result = {{'value': missing, 'operation': 'missing_count', 'columns_used': [{col!r}]}}\n"
        )
    if op is Operation.COUNT:
        if plan.filter is not None:
            f = plan.filter
            expr = _filter_expr(f.column, f.op, f.value)
            return _emit(
                f"value = int(df.filter({expr}).height)\n"
                f"result = {{'value': value, 'operation': 'count', 'columns_used': [{f.column!r}]}}\n"
            )
        return _emit(
            "value = int(df.height)\n"
            "result = {'value': value, 'operation': 'count', 'columns_used': []}\n"
        )
    if op in (Operation.MAX_BY_GROUP, Operation.MIN_BY_GROUP) and group:
        descending = "True" if op is Operation.MAX_BY_GROUP else "False"
        used = [group] + ([col] if col else [])
        agg = f"pl.col({col!r}).sum()" if col else "pl.len()"
        return _emit(
            "g = (\n"
            f"    df.group_by({group!r})\n"
            f"    .agg({agg}.alias('m'))\n"
            f"    .sort('m', descending={descending})\n"
            ")\n"
            "top = g.row(0)\n"
            "tie = g.height > 1 and g.row(1)[1] == top[1]\n"
            "result = {\n"
            "    'value': top[0],\n"
            "    'metric': float(top[1]),\n"
            "    'ambiguous': bool(tie),\n"
            f"    'operation': {op.value!r},\n"
            f"    'columns_used': {used!r},\n"
            "}\n"
        )

    # No supported template matched: emit a program that produces no value, so
    # verification abstains rather than the agent inventing an answer.
    return _emit("result = {'unsupported': True}\n")


def _filter_expr(column: str, op: str, value: str) -> str:
    # Compare as strings to avoid dtype surprises on uploaded data.
    return f"pl.col({column!r}).cast(pl.Utf8, strict=False) {op} {value!r}"
