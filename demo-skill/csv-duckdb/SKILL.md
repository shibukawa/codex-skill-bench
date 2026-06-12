---
name: csv-duckdb
description: Aggregate CSV files with DuckDB through a bundled script. Use when Codex needs exact row counts, totals, or averages from CSV data and DuckDB is available on PATH.
---

# CSV DuckDB

Use this skill for deterministic CSV aggregation. Prefer the bundled script over manual CSV inspection when the task asks for row counts, sums, or averages.

## Aggregate A CSV

From the workspace root, run:

```bash
python3 .agents/skills/csv-duckdb/scripts/aggregate_csv.py data/measurements.csv
```

The script uses the installed `duckdb` CLI and prints a JSON object:

```json
{
  "row_count": 1000,
  "total_value": 499750.0,
  "average_value": 499.75
}
```

Use the script output as the source of truth. If the user requests structured output, return the same object shape in the final answer.
