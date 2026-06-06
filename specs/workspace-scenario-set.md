---
id: "workspace-scenario-set"
type: "data-model"
title: "Workspace Fixture"
aliases:
  - "fixtures directory"
  - "workspace fixture set"
tags:
  - "fixtures"
  - "fixture"
  - "scenario"
facts:
  lifecycle.status: "blueprint"
  data.name: "WorkspaceFixture"
---

# Workspace Fixture

## Summary

A workspace fixture is a directory under `fixtures/` that contains one reusable workspace state and one or more scenario YAML files. Each scenario is executed by copying the workspace state into a fresh run directory, then invoking Codex inside that copy.

## Directory Layout

The canonical layout is:

```text
fixtures/
  .env.skill
  go-sample-project/
    .env.skill
    workspace/
      go.mod
      main.go
      README.md
    cases/
      add-cli-flag.yaml
      analyze-package-structure.yaml
    set.yaml
```

`workspace/` contains the initial project state. `cases/` contains scenario definitions that reuse that initial state. `fixture.yaml` is optional metadata and defaults for every scenario in the fixture. `fixtures/.env.skill` provides common fixture environment variables, and `fixtures/<fixture-id>/.env.skill` provides fixture-specific overrides.

## Required Behavior

- The runner must discover fixtures under the suite config's fixture root, defaulting to `fixtures/<fixture-id>/`.
- Each scenario run must copy `fixtures/<fixture-id>/workspace/` into an isolated run workspace.
- The source `workspace/` directory must never be mutated by a run.
- Multiple scenarios in the same set must be independent even when they start from identical files.
- Reports must group results by fixture, scenario, model, variant, and attempt.

## Fixture Metadata

`fixture.yaml` may define:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | no | Defaults to the directory name. |
| `title` | string | no | Human-readable fixture name. |
| `description` | string | no | Explains the shared workspace state. |
| `defaults` | object | no | Default skills, models, variants, timeout, assertions, or artifacts for scenarios. |
| `workspace` | object | no | Overrides the default `workspace/` path when needed. |

## Scenario Files

Scenario YAML files under `cases/` use [Test Case Model](test-case-model.md), but they may omit `workspace` because the parent fixture supplies it.

## Example Fixture

```yaml
# fixtures/go-sample-project/fixture.yaml
id: go-sample-project
title: Go sample project
defaults:
  skills:
    - spec-compiler
  timeout: 10m
```

```yaml
# fixtures/go-sample-project/cases/add-cli-flag.yaml
id: add-cli-flag
title: Add CLI flag behavior
prompt: |
  Add a --name flag to the sample Go CLI and update tests.
expected:
  - expected: file contains
    path: main.go
    regex: "flag\\.String"
  - expected: file contains
    path: main_test.go
    text: "--name"
```

```yaml
# fixtures/go-sample-project/cases/analyze-package-structure.yaml
id: analyze-package-structure
title: Analyze package structure
prompt: |
  Analyze this Go project and summarize package responsibilities.
expected:
  - expected: reply
    text: "package"
  - expected: file_not_exists
    path: main.go.bak
```

## Rules / Constraints

- A scenario ID must be unique within its fixture.
- The global run identity combines fixture ID and scenario ID.
- Scenario files must not use paths that escape the copied run workspace.
- Fixtures may contain helper files outside `workspace/`, but only files declared as artifacts or case inputs should be copied into runs.
- Optional `.env.skill` files may exist at the fixture root and fixture directory levels. They are read by the runner as environment inputs and are not part of the copied workspace unless explicitly placed under `workspace/`.

## Related Documents

- [Test Definition Format](test-definition-format.md)
- [Test Case Model](test-case-model.md)
- [Codex Runner](codex-runner.md)
- [Report Generator](report-generator.md)
- [Security And Isolation Policy](security-and-isolation-policy.md)

## Native-Language Summary

`fixtures/<fixture>/workspace/` に共通の初期状態を置き、`cases/*.yaml` に複数の挙動テストを書く。同じ状態をケースごとに複製してCodexを実行し、結果をfixture単位で集計する。
