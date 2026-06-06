---
id: "artifact-usage-evaluation-policy"
type: "architectural-decision"
title: "Artifact Usage Evaluation Policy"
aliases:
  - "verification turn"
  - "artifact query evaluation"
  - "same model verification"
tags:
  - "evaluation"
  - "artifacts"
  - "structured-output"
facts:
  lifecycle.status: "accepted"
---

# Artifact Usage Evaluation Policy

## Summary

Some skills, especially documentation and specification tools, may need to be evaluated not only by the files they produce but also by whether the resulting workspace is useful to the same model in a follow-up task. The benchmark should support optional artifact-usage evaluation turns that use the same Codex model under test and produce structured output for deterministic scoring.

## Decision

Artifact-usage evaluation is optional and distinct from LLM judge scoring.

- The Codex run creates or modifies artifacts.
- When configured, a follow-up evaluation prompt is executed in the same run workspace and asks the same model under test to use the generated artifacts.
- The evaluation response must use structured output.
- Deterministic assertions evaluate whether the structured output is valid, complete, and accurate.
- Token usage, duration, and accuracy from this evaluation turn are reported separately from the original Codex run.

## Rationale

- For documentation tools, successful generation is only half of the workflow. Searchability, answerability, and compactness matter.
- Using the same model keeps model comparisons fair: a model is evaluated on both producing artifacts and later using them.
- Structured output makes the verification result machine-checkable instead of relying only on a separate judge model.
- Evaluation token usage and duration reveal whether the skill improves downstream efficiency.

## Evaluation Prompt Shape

Artifact-usage prompts should define a concrete task to run in the generated workspace and require structured output. Searching documentation is one example, but the prompt can ask the model to inspect, query, execute, summarize, or otherwise use the workspace artifacts. The runner does not need to pass artifact paths explicitly; prompt authors are responsible for describing the task fairly.

Example:

```yaml
usageEvaluations:
  - id: query-generated-spec
    prompt: |
      Use this workspace's generated spec artifacts to answer:
      Which files define the retry policy, and what is the default max attempt count?
      Return structured output only.
    outputSchema:
      type: object
      required:
        - valid
        - answer
        - citations
      properties:
        valid:
          type: boolean
        answer:
          type: string
        citations:
          type: array
          items:
            type: string
    expected:
      valid: true
      answerContains:
        - "3"
      citationContains:
        - "retry"
```

## Metrics

Artifact-usage evaluation must collect:

| Metric | Notes |
| --- | --- |
| `usageInputTokens` | Input tokens for the follow-up artifact query. |
| `usageOutputTokens` | Output tokens for the follow-up artifact query. |
| `usageTotalTokens` | Total tokens when available. |
| `usageDurationMs` | Wall-clock duration for the follow-up artifact query. |
| `structuredOutputValid` | Whether the response conforms to the requested schema. |
| `accuracyStatus` | Deterministic status from expected structured fields. |

Reports must keep these metrics separate from the original run's generation tokens and duration.

## Skill-Control Efficiency Comparison

When both skill-enabled and no-skill control variants are present, reports should compute deterministic deltas for generation and artifact-usage metrics:

| Metric | Notes |
| --- | --- |
| `generationTokenDelta` | Control generation total tokens minus skill generation total tokens. Positive means skill saved tokens. |
| `generationDurationDeltaMs` | Control generation duration minus skill generation duration. Positive means skill was faster. |
| `usageTokenDelta` | Control artifact-usage total tokens minus skill artifact-usage total tokens. Positive means skill artifacts were cheaper to use. |
| `usageDurationDeltaMs` | Control artifact-usage duration minus skill artifact-usage duration. Positive means skill artifacts were faster to use. |
| `accuracyDelta` | Skill usage-evaluation accuracy minus control usage-evaluation accuracy. Positive means skill improved accuracy. |

Suites may define deterministic thresholds for what counts as a meaningful improvement. In addition, an optional LLM judge may review these deltas and the task context to classify whether token or duration savings are meaningful enough to count as an improvement.

## Same-Model Rule

When enabled, artifact-usage evaluation uses the same Codex model, variant, fixture, case, and attempt context as the generation run by default. It must not use the independent LLM judge model unless the case explicitly defines an LLM-judged assertion.

## Workspace Mutation

Artifact-usage evaluation runs in the generated run workspace and may modify files. The runner should capture a separate post-usage filesystem snapshot so reports can distinguish generation diffs from usage-evaluation diffs. Mutation during usage evaluation is not a failure by itself.

## Related Documents

- [Assertion Engine](assertion-engine.md)
- [Report Generator](report-generator.md)
- [Suite Config Model](suite-config-model.md)
- [Test Definition Format](test-definition-format.md)

## Native-Language Summary

ドキュメント生成系skillなどでは、任意で生成済みworkspaceに対する後続タスクを同じ対象モデルに実行させ、structured output、token、時間、正確性を元の実行とは別に評価する。
