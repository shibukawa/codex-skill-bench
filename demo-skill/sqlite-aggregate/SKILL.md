---
name: sqlite-aggregate
description: Aggregate values from SQLite database files with a bundled script. Use when Codex needs exact row counts, totals, or averages from a SQLite binary database.
---

# SQLite Aggregate

Use this skill for deterministic aggregation from SQLite database files. Prefer the bundled script over manual binary inspection when the task asks for row counts, sums, or averages.

## Aggregate A SQLite Database

From the workspace root, run:

```bash
python3 .agents/skills/sqlite-aggregate/scripts/aggregate_sqlite.py data/measurements.sqlite
```

The script reads table `measurements`, aggregates column `value`, and prints a JSON object:

```json
{
  "row_count": 1000,
  "total_value": 499750.0,
  "average_value": 499.75
}
```

Use the script output as the source of truth. If the user requests structured output, return the same object shape in the final answer.
