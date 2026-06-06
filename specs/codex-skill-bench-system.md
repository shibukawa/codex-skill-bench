---
id: "codex-skill-bench-system"
type: "system"
title: "Codex Skill Bench System"
aliases:
  - "skill evaluation tool"
  - "Codex skill verification tool"
tags:
  - "python"
  - "cli"
  - "codex"
facts:
  lifecycle.status: "blueprint"
  owner: "tooling"
---

# Codex Skill Bench System

## Summary

Codex Skill Bench is a Python CLI tool for verifying whether Codex skills behave as expected in controlled test cases. It executes Codex in isolated copied workspaces through the Codex SDK, materializes skill variants as project-local skills, captures structured event logs, inspects workspace changes and command/tool activity, evaluates assertions, and emits machine-readable and human-readable reports.

## Goals

- Run repeatable skill behavior tests from declarative test case definitions.
- Provide each scenario with a workspace fixture, usually from `fixtures/<fixture-id>/workspace/`, and a natural-language instruction prompt.
- Capture Codex execution as structured events through the Codex SDK, retaining `codex exec --json` only as a diagnostics compatibility path.
- Evaluate deterministic assertions without an LLM when the expected condition is structurally checkable.
- Evaluate produced artifacts with same-model structured-output usage queries when artifact usability is part of the skill's value.
- Evaluate heuristic or semantic assertions with an LLM judge only when deterministic checks are insufficient.
- Compare results across Codex models and across multiple skill implementation variants.
- Produce YAML result data and an HTML report suitable for local inspection and CI artifacts.

## Non-Goals

- The tool does not replace Codex itself or reimplement Codex planning behavior.
- The tool does not require every assertion to be LLM judged.
- The first implementation does not need a distributed runner; local sequential or bounded-parallel execution is sufficient.
- The first implementation does not need to support every possible Codex event shape if raw events are preserved for later analysis.

## Core Workflow

1. Load suite configuration, workspace fixtures, and test case definitions.
2. Materialize the workspace fixture for each case into an isolated run directory, copying the parent fixture workspace when present.
3. Materialize the target skill implementation variant into the copied run workspace, defaulting to `.agents/skills/<skill-name>/`.
4. Execute Codex through the configured execution backend with `workspace-write` sandbox plus resolved approval and network settings.
5. Save raw events to `results/<run-id>.events.jsonl` and the final assistant message to `results/<run-id>.final.md`.
6. Capture filesystem diff and selected run metadata.
7. Evaluate assertions from the test case.
8. Write a normalized YAML result file.
9. Render or update the HTML report.

## Required Codex Execution Contract

The runner must support a backend-neutral execution contract:

| Field | Required | Notes |
| --- | --- | --- |
| `prompt` | yes | User instruction for the current step. |
| `cwd` | yes | Copied run workspace. |
| `model` | no | Model selected by suite matrix. |
| `sandbox` | yes | Defaults to `workspace-write`. |
| `approvalPolicy` | yes | Resolved suite approval policy. |
| `config` | no | Backend-specific Codex config overrides, including network policy. |
| `ephemeral` | yes | Runs should avoid polluting persistent Codex thread history where supported. |
| `events` | yes | Raw SDK events or diagnostics compatibility JSONL stream must be preserved. |
| `finalMessage` | yes | Final assistant message must be written to result artifacts. |

The required implementation path is the Codex SDK backend. It must call Codex directly and convert returned events into the shared event model. A compatibility CLI backend may support this command shape for diagnostics and comparison:

```bash
codex -a "$APPROVAL" \
  -c "sandbox_workspace_write.network_access=$NETWORK" \
  exec --json \
  --sandbox workspace-write \
  --cd "runs/$CASE_ID/workspace" \
  --output-last-message "results/$CASE_ID.final.md" \
  "$PROMPT" \
  > "results/$CASE_ID.events.jsonl"
```

The actual implementation may add model, approval, timeout, and config options, but it must preserve structured event capture, final-message capture, and project-local skill discovery from the copied run workspace. The default implementation must not replace `CODEX_HOME`.

## Components

- [Test Case Model](test-case-model.md)
- [Suite Config Model](suite-config-model.md)
- [Workspace Fixture](workspace-scenario-set.md)
- [Codex Runner](codex-runner.md)
- [Event Log Model](event-log-model.md)
- [Assertion Engine](assertion-engine.md)
- [Report Generator](report-generator.md)
- [Comparison Matrix](comparison-matrix.md)

## Decisions

- [Deterministic And LLM Assertion Policy](deterministic-and-llm-assertion-policy.md)
- [Project Local Skill Materialization Policy](project-local-skill-materialization-policy.md)
- [Python Implementation Policy](python-implementation-policy.md)

## Native-Language Summary

Codex上でskillが期待通り動くかを、fixture、prompt、Codex SDK実行イベント、ファイル差分、assertion、レポートで検証するPython製CLIツールの仕様である。
