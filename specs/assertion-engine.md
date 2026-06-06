---
id: "assertion-engine"
type: "server-component"
title: "Assertion Engine"
aliases:
  - "expectation evaluator"
tags:
  - "expectations"
  - "llm-judge"
facts:
  lifecycle.status: "blueprint"
  owner: "tooling"
---

# Assertion Engine

## Summary

The Assertion Engine evaluates `expected` and `unexpected` conditions for each case step using deterministic checks first, artifact-usage structured-output checks when evaluating generated artifacts, and LLM-judged checks only for semantic or heuristic conditions.

## Responsibilities

- Load expected and unexpected conditions from [Test Case Model](test-case-model.md).
- Evaluate deterministic expectations against normalized run data.
- Dispatch LLM expectations to a configured judge model with bounded evidence.
- Dispatch artifact-usage evaluations to the same Codex model under test and validate structured output deterministically.
- Produce per-expectation status, evidence, diagnostics, and confidence.
- Keep deterministic findings separate from LLM advisory judgments.

## Expectation Result Fields

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | no | Expectation ID. Generated when omitted. |
| `event` | string | yes | Expected event or state condition. |
| `polarity` | enum | yes | `expected` or `unexpected`. |
| `status` | enum | yes | `passed`, `failed`, `errored`, `skipped`, or `not_applicable`. |
| `deterministic` | boolean | yes | `false` for LLM-judged expectations. |
| `message` | string | yes | Human-readable outcome. |
| `evidence` | object | no | Paths, snippets, matched events, diffs, or judge rationale. |
| `confidence` | number | no | Required for LLM-judged expectations. |

## Matching Rules

- `expected` passes when at least one normalized event or final state matches the condition.
- `unexpected` passes when no normalized event or final state matches the condition.
- Matching within one prompt observation window is order-insensitive; expectation order in YAML must not be compared to event order unless an explicit future ordering assertion is introduced.
- Observed events not described by `expected` or `unexpected` are allowed.
- `skill_activated` is commonly expected but may be omitted; the runner may report inferred activation without failing when it is not explicitly listed.

## Deterministic Expected Event Types

| Type | Purpose |
| --- | --- |
| `file_exists` | Assert that a relative workspace path exists. |
| `file_not_exists` | Assert that a relative workspace path does not exist. |
| `file_contains` | Assert that a file contains a literal string or regular expression. |
| `file_changed` | Assert that a file was added, modified, or deleted. |
| `final_message_contains` | Assert final assistant message content. |
| `skill_available` | Assert a skill appears in captured prompt input before execution. |
| `skill_activated` | Assert that the target skill's `SKILL.md` was read. |
| `skill_instruction_read` | Assert the skill's `SKILL.md` was read during the run. |
| `reference_accessed` | Assert a named skill reference file was accessed. |
| `script_executed` | Assert a named skill script was executed, optionally with expected parsed arguments. |
| `tool_called` | Assert a Codex tool/function was invoked. |
| `token_usage_max` | Assert token usage is below a configured threshold when usage is available. |
| `event_count_min` | Assert at least N events of a given kind were captured. |

Low-level command start/completion checks are diagnostics only and are not part of the canonical assertion vocabulary. Skill behavior assertions should use `script_executed`, `reference_accessed`, and `skill_activated`.

## Artifact-Usage Assertion Types

| Type | Purpose |
| --- | --- |
| `usage_structured_output_valid` | Assert that the artifact-usage response conforms to the requested schema. |
| `usage_answer_contains` | Assert that a structured output field contains expected text. |
| `usage_citation_contains` | Assert that citations or source fields reference expected artifact paths or terms. |
| `usage_accuracy` | Assert deterministic correctness of structured fields for the usage query. |
| `usage_token_usage_max` | Assert artifact-usage token usage is below a configured threshold. |
| `usage_duration_max` | Assert artifact-usage duration is below a configured threshold. |

Artifact-usage assertions are deterministic because they evaluate structured output produced by the same model under test.

## LLM-Judged Assertion Types

| Type | Purpose |
| --- | --- |
| `llm_final_answer_quality` | Judge whether final response satisfies an expected rubric. |
| `llm_file_semantics` | Judge whether generated or modified files meet semantic expectations. |
| `llm_behavior_trace` | Judge whether the sequence of actions reflects the intended skill workflow. |
| `llm_command_success` | Judge whether a configured command, such as `npm run test`, succeeded and whether its output satisfies a rubric. Exit-code-only checks are deterministic command judge checks. |
| `llm_efficiency_comparison` | Judge whether skill-enabled token or duration savings versus no-skill control are meaningful for the task. |

## LLM Judge Evidence Rules

- Provide only the smallest useful evidence bundle.
- Include expectation rubric, final message, relevant file snippets or diffs, and relevant normalized events.
- Exclude secrets and unbounded raw logs by default.
- Require the judge to return structured JSON with verdict, confidence, and rationale.
- Store judge prompts and responses as artifacts for auditability.
- Record judge model, judge config, evidence hash, and cache hit status with every LLM-judged result.
- Command-based judge checks must record command, exit code, stdout/stderr previews, duration, and working directory.

## Dependencies

- [Event Log Model](event-log-model.md)
- [Test Definition Format](test-definition-format.md)
- [Deterministic And LLM Assertion Policy](deterministic-and-llm-assertion-policy.md)

## Reads

- [Test Case Model](test-case-model.md)
- [Codex Runner](codex-runner.md)

## Writes

- [Report Generator](report-generator.md)

## Related Requirements

- [Codex Skill Bench System](codex-skill-bench-system.md)

## Native-Language Summary

expectationは、ファイル差分、skill script、reference、SKILL.md読み込み、最終応答、token使用量などを決定論で確認し、生成物利用は同じモデルのstructured outputを検証し、意味的な品質だけを必要に応じてLLM judgeで評価する。
