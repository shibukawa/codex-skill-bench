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
  lifecycle.status: "mvp"
  owner: "tooling"
---

# Report Generator

## Summary

The Report Generator writes normalized YAML results and renders an HTML report for humans to inspect suite outcomes, failures, artifacts, and comparisons.

The MVP report is a single static `report.html` file generated beside `summary.yaml`. It embeds the current summary data, selected intermediate artifacts, and pure JavaScript needed for local navigation, so the report can be opened as a standalone CI artifact without a web server.

## Responsibilities

- Write one normalized YAML result file per run.
- Write an aggregate YAML summary for the suite.
- Render an HTML report from aggregate results.
- Embed a normalized report data payload inside `report.html`.
- Link to raw JSONL events, final messages, stderr logs, diffs, usage-evaluation artifacts, and LLM judge artifacts.
- Preview useful intermediate artifacts inline, including `summary.yaml`, per-run result YAML, final messages, stderr logs, and bounded event-log previews.
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

## MVP Single-HTML Report

The first implemented HTML report must be generated as `results/report.html` after `results/summary.yaml` is written. It must not require external CSS, external JavaScript, a build step, or a server. The page may link to raw artifact files by relative path when they are under the result directory.

The embedded data payload must include:

| Field | Notes |
| --- | --- |
| `schemaVersion` | Version for the report payload, starting at `1`. |
| `summary` | Case counts, status counts, and comparison counts. |
| `cases[]` | Flattened fixture/case/model records for list navigation. |
| `cases[].variants` | Variant aggregates, attempts, token usage, durations, preload data, artifact links, and artifact previews. |
| `cases[].comparisons` | Skill/control comparison rows matching the fixture, case, and model. |
| `raw.summaryYaml` | Original aggregate YAML as text for direct inspection. |
| `raw.summaryJson` | Parsed aggregate data for client-side rendering and future export. |

The client-side UI must be pure JavaScript and render from the embedded payload. The default layout is:

- A left sidebar with a searchable test-case list.
- Each list item must show fixture, case, model, and OK/NG-style status at a glance.
- Clicking a list item must replace the detail pane without reloading the page.
- The detail pane must show variant status, generation duration, estimated repeat duration, token usage, preload cost, and no-skill baseline improvement deltas.
- Skill comparison rows must use `no-skill` as the baseline whenever that variant exists, even when multiple skill variants are evaluated in the same fixture/case/model group.
- The primary comparison metric is repeated-run improvement: `no-skill.estimatedRepeatDurationMs - skill.estimatedRepeatDurationMs`. Positive values mean the skill improved repeated-run time.
- Token improvement is `no-skill.usage.totalTokens - skill.usage.totalTokens`. Positive values mean the skill saved generation tokens.
- Preload duration and preload tokens must be shown in parentheses beside repeated-run and token improvements because they are one-time additional costs.
- Clicking a variant or attempt row must scope the artifact, event, and raw-data sections to only that selected result.
- Artifact links should use short action labels such as `Open workspace`, `Open events`, and `Open result YAML`; full paths should remain available in the embedded data but should not be the visible link label.
- The selected result should expose `workspace`, event, final, stderr, result YAML, preload artifacts, and materialized skill links when present; `runRoot` should not be shown as a separate visible artifact link.
- Event JSONL should be formatted as an expandable event list with type, status or phase, compact summary text, and the raw JSON for inspection.

## Current Verification Example

The current `examples/basic-suite/results` run demonstrates the MVP data shape:

| Variant | Status | Duration | Estimated Repeat | Total Tokens | Preload |
| --- | --- | ---: | ---: | ---: | --- |
| `with-skill` | `passed` | `22647ms` | `11627ms` | `69332` | `11020ms`, `32486` tokens |
| `no-skill` | `passed` | `16456ms` | `16456ms` | `64254` | none |

The no-skill baseline comparison for this run is:

| Metric | Value | Interpretation |
| --- | ---: | --- |
| Repeated time improvement | `4829ms` | `with-skill` is estimated 4.829s faster than `no-skill` on repeated runs. |
| Repeated time preload cost | `11020ms` | One-time skill preload duration shown in parentheses. |
| Token improvement | `-5078` | `with-skill` used 5,078 more generation tokens than `no-skill`. |
| Token preload cost | `32486` | One-time skill preload tokens shown in parentheses. |

Both variants are `passed` in the MVP because assertions are not yet deterministically evaluating the exact file content. The report must therefore separate execution status from output-quality evidence and expose final messages, result YAML, and event data for review.

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
- Searchable left-side test case list with status indicators.
- Matrix view by fixture, case, model, and skill variant.
- Skill-enabled versus no-skill control comparison when control variants are present.
- No-skill baseline improvement table for every skill variant in the same fixture/case/model group.
- Artifact-usage evaluation token, duration, structured-output validity, and accuracy summaries.
- Generation versus artifact-usage cost breakdowns.
- Skill-enabled versus no-skill token, duration, and accuracy deltas.
- Command validation status and output previews.
- Optional judge summary for whether observed efficiency deltas are meaningful.
- Separate deterministic and LLM-judged assertion summaries.
- Per-run detail pages or expandable sections.
- Links to raw artifacts.
- Selected-result artifact links with short visible labels.
- Inline previews of bounded intermediate data, with links to full artifacts.
- Expandable formatted event lists for generation and preload events.
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
