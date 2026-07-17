"""Trusted reference calculator for the eval_sales_v1 core suite.

Computes every gold answer with the SAME semantics the agent's code generator
uses (polars; sum/mean ignore nulls; missing = null or empty), so the eval suite
is grounded in an independent, executable oracle — not hand arithmetic alone.

Run:  python evals/references/eval_sales_v1_reference.py
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "eval_sales_v1.csv"


def compute() -> dict[str, object]:
    df = pl.read_csv(FIXTURE, infer_schema_length=10000)

    def group_top(group: str, target: str | None, descending: bool) -> str:
        agg = pl.col(target).sum() if target else pl.len()
        g = df.group_by(group).agg(agg.alias("m")).sort("m", descending=descending)
        return str(g.row(0)[0])

    def missing(col: str) -> int:
        s = df[col]
        return int((s.is_null() | (s.cast(pl.Utf8, strict=False) == "")).sum())

    return {
        "sum_price": round(float(df["price"].sum()), 4),
        "sum_units": int(df["units"].sum()),
        "mean_price": round(float(df["price"].mean()), 4),
        "mean_units": round(float(df["units"].mean()), 4),
        "row_count": int(df.height),
        "distinct_region": int(df["region"].n_unique()),
        "distinct_rep": int(df["rep"].n_unique()),
        "missing_price": missing("price"),
        "missing_units": missing("units"),
        "max_region_price": group_top("region", "price", descending=True),
        "max_category_units": group_top("category", "units", descending=True),
        "min_region_price": group_top("region", "price", descending=False),
        "top_rep_count": group_top("rep", None, descending=True),
    }


if __name__ == "__main__":
    print(json.dumps(compute(), indent=2))
