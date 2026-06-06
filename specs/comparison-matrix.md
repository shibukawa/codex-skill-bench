---
id: "comparison-matrix"
type: "requirement"
title: "Comparison Matrix"
aliases:
  - "model comparison"
  - "skill variant comparison"
tags:
  - "comparison"
  - "matrix"
facts:
  lifecycle.status: "blueprint"
---

# Comparison Matrix

## Summary

The tool must run the same test cases across multiple Codex models and multiple skill implementation variants, then compare results in reports.

## Model Comparison

Suite configuration may define a list of models. Each selected test case runs once per model unless the case overrides the model list or the CLI filters it.

Model comparison must show:

- Overall pass/fail/error rate per model.
- Per-case status per model.
- Token usage by model when available.
- Duration by model.
- Assertion differences between models.

## Skill Variant Comparison

Suite configuration may define multiple skill implementation variants. A variant represents a different skill directory, generated skill package, patched skill implementation, or an explicit no-skill control condition.

A no-skill control variant runs the same fixture, prompt, model, and assertions without materializing the target skill. It is used to measure whether the skill changes behavior compared with plain Codex behavior.

Variant comparison must show:

- Overall pass/fail/error rate per variant.
- Per-case status per variant.
- Behavioral differences from JSONL events and assertions.
- Generated file differences where assertions expose them.
- Skill lift or regression by comparing skill-enabled variants against no-skill control variants.

## No-Skill Control Comparison

When a suite defines a no-skill control variant, reports should show:

- Cases where the skill-enabled variant passes but the no-skill control fails.
- Cases where both pass, suggesting the skill may not be necessary for that prompt.
- Cases where the no-skill control outperforms the skill-enabled variant.
- Differences in command/tool behavior, file changes, final response, token usage, and duration.

The no-skill control must not materialize the target skill into the run workspace. The runner should preflight that the target skill is not visible to Codex for that run. If it is visible through inherited user configuration, fixture content, or another project-local path, the run should be marked as a setup failure unless the suite explicitly allows ambient skills.

## Matrix Dimensions

The primary matrix dimensions are:

| Dimension | Source |
| --- | --- |
| Fixture | [Workspace Fixture](workspace-scenario-set.md) |
| Case | [Test Case Model](test-case-model.md) |
| Model | Suite config or case override |
| Variant | Suite config or case override |
| Attempt | Retry or repeat index |

## CLI Filtering Requirements

The CLI should allow filtering by:

- Case ID or glob.
- Fixture ID or glob.
- Model.
- Variant.
- Assertion type.
- Deterministic-only mode.
- Failed-only report rendering from existing results.

## Related Documents

- [Codex Skill Bench System](codex-skill-bench-system.md)
- [Suite Config Model](suite-config-model.md)
- [Workspace Fixture](workspace-scenario-set.md)
- [Report Generator](report-generator.md)
- [Codex Runner](codex-runner.md)
- [Project Local Skill Materialization Policy](project-local-skill-materialization-policy.md)

## Native-Language Summary

同じテストケースを複数モデル・複数skill実装variantで実行し、pass率、token、時間、assertion差分、成果物差分を比較できる必要がある。
