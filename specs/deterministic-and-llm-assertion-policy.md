---
id: "deterministic-and-llm-assertion-policy"
type: "architectural-decision"
title: "Deterministic And LLM Assertion Policy"
aliases:
  - "LLM judge policy"
tags:
  - "decision"
  - "quality"
facts:
  lifecycle.status: "accepted"
---

# Deterministic And LLM Assertion Policy

## Summary

Assertions must be deterministic by default. LLM judging is allowed only when the expected behavior cannot be reliably expressed as file, event, command, tool, token, text, or structured-output matching logic.

## Decision

The evaluator separates assertions into deterministic assertions, optional artifact-usage evaluations, and optional LLM-judged assertions. Deterministic assertions are preferred because they are reproducible, cheap, and easier to debug. Artifact-usage evaluations use the same model under test to query produced artifacts and then validate structured output deterministically. LLM-judged assertions are reserved for semantic quality, workflow appropriateness, efficiency interpretation, and other heuristic judgments that are important for skill evaluation but not structurally checkable.

## Rationale

- Skill behavior has both observable structural outputs and qualitative intent-following behavior.
- Codex JSONL logs and filesystem diffs make many checks deterministic.
- Some checks, such as whether a generated spec is "usefully organized", require language judgment.
- For documentation skills, downstream artifact usability is a measurable behavior and should use the same model being tested.
- Mixing deterministic and LLM outcomes without labeling would make reports hard to trust.

## Consequences

- Reports must show deterministic and LLM-judged pass rates separately.
- Reports must show artifact-usage evaluation metrics separately from generation metrics and LLM judge metrics when usage evaluation is enabled.
- LLM judge configuration must be explicit in suite or CLI configuration and is disabled by default.
- Artifact-usage evaluation configuration must be explicit in suite or case configuration and is disabled by default.
- Artifact-usage evaluation uses the same Codex model under test by default.
- Optional LLM judge configuration may remain explicit and independent when heuristic judging is still needed.
- Optional LLM judge may evaluate whether skill-enabled runs saved meaningful token count or processing time compared with no-skill controls.
- LLM judge prompts and responses must be retained as artifacts.
- CI should be able to run deterministic-only mode.
- LLM-judged failures should include confidence and rationale.

## Related Documents

- [Assertion Engine](assertion-engine.md)
- [Report Generator](report-generator.md)
- [Artifact Usage Evaluation Policy](artifact-usage-evaluation-policy.md)

## Native-Language Summary

構造的に検証できるものは決定論で評価し、生成物の利用性は任意で同じ対象モデルのstructured output検証で測り、意味品質・作業手順・tokenや時間節約の意味づけなどだけを必要に応じてLLM judgeで評価する方針である。
