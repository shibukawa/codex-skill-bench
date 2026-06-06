---
id: "report-generator"
type: "batch-component"
title: "Report Generator"
aliases:
  - "yaml report"
  - "html report"
tags:
  - "reporting"
  - "html"
  - "yaml"
facts:
  lifecycle.status: "blueprint"
  owner: "tooling"
---

# Report Generator

## Summary

The Report Generator writes normalized YAML results and renders an HTML report for humans to inspect suite outcomes, failures, artifacts, and comparisons.

## Responsibilities

- Write one normalized YAML result file per run.
- Write an aggregate YAML summary for the suite.
- Render an HTML report from aggregate results.
- Link to raw JSONL events, final messages, stderr logs, diffs, usage-evaluation artifacts, and LLM judge artifacts.
- Highlight failures, errored runs, skipped assertions, and missing telemetry.
- Apply configured artifact redaction to report previews and HTML.

## YAML Result Requirements

The per-run YAML result must include:

| Field | Notes |
| --- | --- |
| `run` | Run identity, fixture, model, variant, variant kind, attempt, start/end timestamps. |
| `case` | Scenario set ID, case ID, and title. |
| `codex` | Command, exit code, duration, sandbox, binary path. |
| `artifacts` | Paths to events JSONL, final message, stderr, diffs, judge outputs. |
| `security` | Resolved env policy, network policy, approval policy, redaction status, and cleanup policy. |
| `stability` | Resolved retry policy, attempt outcomes, flaky classification, and aggregate status. |
| `summary` | Assertion counts and final status. |
| `assertions` | Per-assertion results from [Assertion Engine](assertion-engine.md). |
| `usage` | Token usage when available. |
| `usageEvaluations` | Follow-up artifact-query results, structured output validity, accuracy, token usage, and duration. |
| `judgeCommands` | Optional command validation results, exit codes, output previews, duration, and judge status when rubric-based. |

## Aggregate Result Hierarchy

The aggregate result schema should mirror the conceptual test hierarchy:

```yaml
fixtures:
  <fixture-id>:
    cases:
      <case-id>:
        models:
          <model-id>:
            variants:
              <variant-id>:
                variantKind: skill
                attempts:
                  - attempt: 1
                    status: passed
                    resultPath: results/<run-id>.result.yaml
                aggregate:
                  status: passed
                  attempts: 1
                  durationMs: 12345
                  usage:
                    inputTokens: 1000
                    outputTokens: 200
                  usageEvaluations:
                    status: passed
                    durationMs: 2345
                    inputTokens: 500
                    outputTokens: 80
                    accuracy:
                      passed: 1
                      failed: 0
                    controlComparison:
                      generationTokenDelta: 120
                      generationDurationDeltaMs: 900
                      usageTokenDelta: 80
                      usageDurationDeltaMs: 300
                      accuracyDelta: 0.25
```

Rules:

- The root is `fixtures`.
- Each fixture contains `cases`.
- Each case contains `models`.
- Each model contains `variants`, including skill-enabled and no-skill control variants.
- Each variant contains one or more retry `attempts`.
- Aggregates must keep generation cost, artifact-usage evaluation cost, command validation cost, and LLM-judge cost separate.
- Skill-enabled variants with matching no-skill controls should include token, duration, and accuracy deltas when comparable data is available.
- Usage-evaluation workspace mutations should be reported separately from generation diffs.
- HTML reports may render this hierarchy as tables, trees, or matrices, but machine-readable YAML should preserve it.

## Artifact Retention

The initial retention policy is full retention. The runner should retain raw SDK events, normalized events, final messages, stderr or diagnostics, generation diffs, usage-evaluation diffs, structured outputs, judge prompts and responses, command outputs, and copied run workspaces according to cleanup policy. Later versions may add summary-only retention modes.

## Failure Taxonomy

Every failed or errored run must include a primary `failureKind`.

| Failure Kind | Meaning |
| --- | --- |
| `setup_failed` | Fixture copy, setup command, skill materialization, or control preflight failed. |
| `preflight_failed` | Codex SDK preflight failed, including missing skill for skill variant or visible target skill for control variant. |
| `codex_failed` | Codex SDK run failed before assertions could be evaluated. |
| `timeout` | Run or step exceeded timeout. |
| `normalization_failed` | Raw events could not be normalized enough for required assertions. |
| `assertion_failed` | One or more required deterministic assertions failed. |
| `judge_failed` | LLM judge could not evaluate a required semantic assertion. |
| `usage_evaluation_failed` | Artifact-usage evaluation did not produce valid structured output or failed deterministic usage checks. |
| `command_judge_failed` | A configured command validation failed by exit code, timeout, or rubric-based judge result. |
| `report_failed` | Result artifact or report generation failed. |

Retry policy may use `failureKind` to decide whether a failure is retryable.

## HTML Report Requirements

The HTML report must include:

- Suite summary with total pass/fail/error counts.
- Matrix view by fixture, case, model, and skill variant.
- Skill-enabled versus no-skill control comparison when control variants are present.
- Artifact-usage evaluation token, duration, structured-output validity, and accuracy summaries.
- Generation versus artifact-usage cost breakdowns.
- Skill-enabled versus no-skill token, duration, and accuracy deltas.
- Command validation status and output previews.
- Optional judge summary for whether observed efficiency deltas are meaningful.
- Separate deterministic and LLM-judged assertion summaries.
- Per-run detail pages or expandable sections.
- Links to raw artifacts.
- Failure diagnostics with compact evidence.

## Status Rules

| Status | Meaning |
| --- | --- |
| `passed` | All required assertions passed. |
| `failed` | At least one required assertion failed. |
| `flaky` | Aggregated policy allows success, but one or more attempts failed or errored before a later pass. |
| `errored` | Runner or evaluator could not complete. |
| `skipped` | Run was intentionally skipped by filter or unmet precondition. |

## Dependencies

- [Assertion Engine](assertion-engine.md)
- [Comparison Matrix](comparison-matrix.md)

## Writes

- `results/<run-id>.result.yaml`
- `results/summary.yaml`
- `results/report.html`

## Related Requirements

- [Codex Skill Bench System](codex-skill-bench-system.md)
- [Suite Config Model](suite-config-model.md)
- [Workspace Fixture](workspace-scenario-set.md)
- [Security And Isolation Policy](security-and-isolation-policy.md)
- [Retry And Stability Policy](retry-and-stability-policy.md)

## Native-Language Summary

評価結果はYAMLで機械処理できる形に保存し、HTMLでfixture/case/model/variantごとの比較、skillあり/なしcontrol比較、成果物利用検証の精度・token・時間、失敗理由を見やすく表示する。
