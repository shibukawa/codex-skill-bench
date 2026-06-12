#!/usr/bin/env python3
"""Aggregate a SQLite table value column as JSON."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db_path", type=Path, help="SQLite database file to aggregate")
    parser.add_argument("--table", default="measurements", help="Table to aggregate")
    parser.add_argument("--value-column", default="value", help="Numeric column to sum and average")
    return parser.parse_args()


def sql_identifier(value: str) -> str:
    if not IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"unsupported identifier: {value!r}")
    return '"' + value.replace('"', '""') + '"'


def aggregate(db_path: Path, table: str, value_column: str) -> dict[str, float | int]:
    table_sql = sql_identifier(table)
    column_sql = sql_identifier(value_column)
    query = f"""
SELECT
  COUNT(*) AS row_count,
  SUM({column_sql}) AS total_value,
  AVG({column_sql}) AS average_value
FROM {table_sql}
""".strip()
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(query).fetchone()
    if row is None:
        raise RuntimeError("aggregate query returned no rows")
    return {
        "row_count": int(row[0]),
        "total_value": float(row[1]),
        "average_value": float(row[2]),
    }


def main() -> int:
    args = parse_args()
    try:
        result = aggregate(args.db_path, args.table, args.value_column)
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as exc:
        print(f"failed to aggregate SQLite database: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
