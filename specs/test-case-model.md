---
id: "test-case-model"
type: "data-model"
title: "Test Case Model"
aliases:
  - "test case schema"
tags:
  - "yaml"
  - "fixture"
facts:
  lifecycle.status: "blueprint"
  data.name: "TestCase"
---

# Test Case Model

## Summary

A test case defines one Codex skill evaluation scenario: one or more prompt steps, skill under test, execution parameters, expected conditions, and forbidden conditions. The normative YAML schema and examples are defined in [Test Definition Format](test-definition-format.md). The workspace may be supplied directly by the case or inherited from a parent [Workspace Fixture](workspace-scenario-set.md).

## Fields

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | yes | Stable identifier used in paths and report keys. |
| `title` | string | yes | Human-readable case title. |
| `description` | string | no | Purpose and coverage notes. |
| `enabled` | boolean | no | Defaults to `true`. |
| `tags` | array | no | Used for filtering and report grouping. |
| `workspace` | object | no | Fixture source or inline files. Required only when the case is not inside a [Workspace Fixture](workspace-scenario-set.md). |
| `prompt` | string | no | Natural-language instruction for a single-prompt case. |
| `promptFile` | string | no | External prompt file relative to the case file for a single-prompt case. |
| `steps` | array | no | Ordered prompt, expected, and unexpected items. Mutually exclusive with top-level `prompt` or `promptFile`. |
| `skills` | array | no | Skill names or paths expected to be available. |
| `models` | array | no | Optional model override list for this case. |
| `variants` | array | no | Optional skill implementation or no-skill control variants for this case. |
| `timeout` | duration | no | Execution timeout. Suite default applies when omitted. |
| `stability` | object | no | Overrides resolved retry and stability policy for this case. |
| `attempts` | integer | no | Compatibility alias for `stability.maxAttempts`. |
| `setup` | array | no | Deterministic pre-Codex setup commands. |
| `expected` | array | no | Expected conditions for a single-prompt case. |
| `unexpected` | array | no | Forbidden conditions for a single-prompt case. |
| `artifacts` | array | no | Extra files to retain in reports. |

## Workspace Fixture

`workspace` must support at least these forms when specified directly on a case:

| Form | Fields | Behavior |
| --- | --- | --- |
| Directory fixture | `fixturePath` | Copy the fixture directory into an isolated run workspace. |
| Inline files | `files` | Create files from path/content entries. |

All fixture paths are resolved relative to the suite file unless explicitly absolute. Inline file paths must be relative and must not escape the run workspace.

When a case lives under `fixtures/<fixture-id>/cases/`, the default workspace is `fixtures/<fixture-id>/workspace/`. The runner copies that workspace for every case execution.

## Prompt Rules

- `prompt` is passed to the Codex SDK turn as the user input for the benchmark run.
- The prompt may reference files created by the fixture.
- The prompt may instruct Codex to use a skill by name or by path.
- Prompt templates may interpolate run variables such as case ID, model, variant name, and workspace path.

## Example

```yaml
id: add-cli-flag
title: Add CLI flag behavior
prompt: |
  Add a --name flag to the sample Go CLI and update tests.
expected:
  - expected: file contains
    path: main.go
    regex: "flag\\.String"
  - expected: command started
    regex: "go test"
```

## Rules / Constraints

- Test case IDs must be unique within a suite.
- A test case must be executable without relying on previous test cases.
- Test cases in the same [Workspace Fixture](workspace-scenario-set.md) must receive independent copies of the shared workspace.
- The canonical input format is YAML.
- The implementation may support JSON later, but YAML is required first.
- Expected and unexpected conditions must be evaluated against normalized run results, not only raw terminal output.

## Uses Common Details

- [Run Identity](shared/run-identity.md)

## Related Requirements

- [Codex Skill Bench System](codex-skill-bench-system.md)
- [Test Definition Format](test-definition-format.md)
- [Suite Config Model](suite-config-model.md)
- [Workspace Fixture](workspace-scenario-set.md)
- [Assertion Engine](assertion-engine.md)
- [Comparison Matrix](comparison-matrix.md)

## Native-Language Summary

テストケースは、ワークスペース構造、単一または複数stepのCodex指示、対象skill、モデルやvariant、期待条件と禁止条件をYAMLで表現する。
