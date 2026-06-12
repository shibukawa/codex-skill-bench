#!/usr/bin/env python3
"""Aggregate a CSV value column using the installed DuckDB CLI."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="CSV file to aggregate")
    parser.add_argument("--value-column", default="value", help="Numeric column to sum and average")
    return parser.parse_args()


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_identifier(value: str) -> str:
    if not IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"unsupported column name: {value!r}")
    return '"' + value.replace('"', '""') + '"'


def run_duckdb(csv_path: Path, value_column: str) -> dict[str, float | int]:
    path = csv_path.expanduser().resolve()
    column = sql_identifier(value_column)
    query = f"""
SELECT
  COUNT(*)::BIGINT AS row_count,
  SUM({column})::DOUBLE AS total_value,
  AVG({column})::DOUBLE AS average_value
FROM read_csv_auto({sql_string(str(path))}, header = true);
""".strip()
    completed = subprocess.run(
        ["duckdb", "-json", "-c", query],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = json.loads(completed.stdout)
    if len(rows) != 1:
        raise RuntimeError(f"expected one aggregate row, got {len(rows)}")
    row = rows[0]
    return {
        "row_count": int(row["row_count"]),
        "total_value": float(row["total_value"]),
        "average_value": float(row["average_value"]),
    }


def main() -> int:
    args = parse_args()
    try:
        result = run_duckdb(args.csv_path, args.value_column)
    except FileNotFoundError as exc:
        print(f"duckdb executable not found: {exc}", file=sys.stderr)
        return 127
    except (subprocess.CalledProcessError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"failed to aggregate CSV: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
