---
id: "python-implementation-policy"
type: "architectural-decision"
title: "Python Implementation Policy"
aliases:
  - "runtime stack"
  - "uv project"
tags:
  - "python"
  - "uv"
facts:
  lifecycle.status: "accepted"
---

# Python Implementation Policy

## Summary

Codex Skill Bench should be implemented as a Python CLI project managed by `uv`. Python is preferred because the runner needs flexible Codex SDK integration, event normalization, YAML schema handling, HTML rendering, filesystem diffing, artifact-usage evaluation, and optional LLM judge orchestration.

## Decision

The implementation language is Python. The project should use `uv` for dependency management, virtual environment creation, command execution, and packaging.

Recommended baseline stack:

| Concern | Recommendation |
| --- | --- |
| Project layout | `src/codex_skill_bench/` |
| Dependency manager | `uv` |
| CLI framework | `typer` or `click` |
| Config schema | `pydantic` |
| YAML | `ruamel.yaml` or `PyYAML` |
| Reports | `jinja2` |
| Testing | `pytest` |
| Lint / format | `ruff` |
| Type checking | `mypy` or `pyright` |

## Package Requirements

- `pyproject.toml` is the canonical project metadata file.
- The CLI entry point should expose `codex-skill-bench`.
- Runtime code should live under `src/codex_skill_bench/`.
- Tests should live under `tests/`.
- The implementation should avoid shelling out when a Python library or SDK API is available.

## Related Documents

- [Codex Skill Bench System](codex-skill-bench-system.md)
- [Codex Runner](codex-runner.md)
- [CLI Interface](cli-interface.md)

## Native-Language Summary

実装はPython + uvを前提とし、Codex SDK連携、YAML/JSONL/HTML、ファイル差分、成果物利用検証、任意のLLM judgeをPythonのライブラリで構成する。
