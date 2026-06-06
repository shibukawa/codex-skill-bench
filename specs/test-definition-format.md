---
id: "test-definition-format"
type: "data-model"
title: "Test Definition Format"
aliases:
  - "case yaml schema"
  - "test definition schema"
  - "fixture case format"
tags:
  - "yaml"
  - "fixtures"
  - "expectations"
facts:
  lifecycle.status: "accepted"
  data.name: "TestDefinitionFormat"
---

# Test Definition Format

## Summary

The canonical test definition format is a YAML suite rooted at `suite.yaml` and reusable workspace fixtures under `fixtures/<fixture-id>/`. Each fixture has a fixed `workspace/` directory and a `fixture.yaml` file containing a `cases` list. Each case is run against a fresh copy of its fixture workspace for each selected model, skill variant, and attempt.

## Canonical File Layout

```text
suite.yaml
fixtures/
  license-header-basic/
    fixture.yaml
    workspace/
      src/sample.py
      src/sample.go
results/
```

## Suite File

`suite.yaml` is the primary CLI input and controls discovery, model matrix, variant matrix, Codex invocation, stability, and reporting.

```yaml
version: 1
name: license header skill suite

fixtures:
  exclude:
    - experimental-*

skills:
  - name: license-header
    path: demo-skill/license-header

models:
  - gpt-5.5

variants:
  - name: current
    skill: license-header

security:
  sandbox: workspace-write
  auth:
    mode: inherit
    preflight: true
  home:
    mode: inherit

defaults:
  timeout: 10m
  skills:
    - license-header

stability:
  maxAttempts: 3
  retryOn:
    - failed
    - errored
  passPolicy: any

report:
  resultsDir: results
  yaml: true
  html: true
```

## Fixture File

`fixtures/<fixture-id>/fixture.yaml` contains the fixture's case list. The fixture directory name is the fixture ID and human-readable title. The workspace path is fixed to `workspace/`.

```yaml
cases:
  - title: Add MIT license headers to Python and Go files
    description: Uses the license-header skill reference and scripts.
    tags:
      - mutation
      - script
    promptVariants:
      skill: |
        Use the $skill skill to add MIT license headers to src/sample.py and src/sample.go.
        Follow the skill workflow: read only references/mit.txt, run the audit script first,
        then run prepend_license.py. Use year 2026 and owner Example Corp.
      no-skill: |
        Add MIT license headers to src/sample.py and src/sample.go.
        Use year 2026 and owner Example Corp.

    expected:
      - expected: access reference
        skill: license-header
        reference: mit.txt
```

## Case Item

Case definitions live as items under `fixtures/<fixture-id>/fixture.yaml` field `cases`. A case defines an ordered interaction list for the copied fixture workspace. Each list item is either a prompt injection, an expected condition, or an unexpected condition. Expected and unexpected conditions are optional and only the conditions written in the case are evaluated.

```yaml
title: Add MIT license headers to Python and Go files
description: Uses the license-header skill reference and scripts.
tags:
  - mutation
  - script
promptVariants:
  skill: |
    Use the $skill skill to add MIT license headers to src/sample.py and src/sample.go.
    Follow the skill workflow: read only references/mit.txt, run the audit script first,
    then run prepend_license.py. Use year 2026 and owner Example Corp.
  no-skill: |
    Add MIT license headers to src/sample.py and src/sample.go.
    Use year 2026 and owner Example Corp.

expected:
  - expected: access reference
    skill: license-header
    reference: mit.txt

  - expected: execute script
    skill: license-header
    script: list_missing_license.py
    exitCode: 0
    stdoutContains: "missing-license"

  - expected: execute script
    skill: license-header
    script: prepend_license.py
    argvContains:
      - "--year"
      - "2026"
      - "--owner"
      - "Example Corp"
      - "src/sample.py"
      - "src/sample.go"
    exitCode: 0
    stdoutContains: "updated"

  - expected: file contains
    path: src/sample.py
    text: "Copyright (c) 2026 Example Corp"

  - expected: file contains
    path: src/sample.go
    text: "Copyright (c) 2026 Example Corp"

  - expected: reply
    text: "references/mit.txt"

unexpected:
  - unexpected: execute script
    skill: license-header
    script: prepend_license.py
    argvContains:
      - "README.md"
```

## Multi-Step Case

Use `steps` when a case needs to inject a prompt, observe behavior, then continue with another prompt in the same run thread. `expected` and `unexpected` items apply to the most recent preceding prompt item. Extra observed events are allowed.

Within one prompt observation window, expected and unexpected items are unordered. Their YAML order does not need to match the order of observed Codex events. For example, `expected: activate skill` may be written before or after `expected: execute script`; both pass as long as matching evidence appears somewhere in the same prompt window.

```yaml
id: audit-then-add-mit-header
title: Audit missing headers, then add them
steps:
  - prompt: |
      Use the $license-header skill to audit this project for files missing an MIT license header.
      Use year 2026 and owner Example Corp. Do not modify files yet.

  - expected: activate skill
    skill: license-header

  - expected: execute script
    skill: license-header
    script: list_missing_license.py
    stdoutContains: "missing-license"

  - unexpected: file changed
    path: src/sample.py

  - expected: reply
    text: "missing"

  - prompt: |
      Now add the MIT license header to src/sample.py and src/sample.go.

  - expected: execute script
    skill: license-header
    script: prepend_license.py
    exitCode: 0

  - expected: file contains
    path: src/sample.go
    text: "Copyright (c) 2026 Example Corp"
```

## Case Fields

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | string | yes | Human-readable title. |
| `description` | string | no | Coverage intent and notes. |
| `enabled` | boolean | no | Defaults to `true`. |
| `tags` | array | no | Used for filtering and reporting. |
| `prompt` | string | no | Inline Codex prompt shorthand. Mutually exclusive with `promptVariants`. |
| `promptFile` | string | no | Path relative to the fixture directory for a single-prompt case. |
| `promptVariants` | object | no | Prompt overrides keyed by variant name, `no-skill`, `specific-skill[<skill>]`, or `skill`. Mutually exclusive with `prompt`. |
| `steps` | array | no | Ordered prompt, expected, and unexpected items. Mutually exclusive with top-level `prompt` or `promptFile`. |
| `skills` | array | no | Skill names expected for this case. Defaults from suite. |
| `models` | array | no | Model override list for this case. |
| `variants` | array | no | Variant override list for this case, including optional no-skill control variants. |
| `timeout` | duration | no | Run timeout. |
| `stability` | object | no | Overrides resolved retry and stability policy for this case. |
| `attempts` | integer | no | Compatibility alias for `stability.maxAttempts`. |
| `workspace` | object | no | Standalone case workspace override; normally omitted inside fixtures. |
| `setup` | array | no | Deterministic setup commands run before Codex. |
| `expected` | array | no | Expected conditions for a single-prompt case. |
| `unexpected` | array | no | Forbidden conditions for a single-prompt case. |
| `usageEvaluations` | array | no | Follow-up artifact queries evaluated with the same model under test. |
| `judgeCommands` | array | no | Optional command-based validation checks such as `npm run test`. |
| `artifacts` | array | no | Additional files to retain in report artifacts. |
| `diffIgnore` | array | no | Gitignore-like path patterns excluded from filesystem diff assertions and report previews. |

## Inheritance Rules

Resolved case configuration is built in this order:

1. Suite defaults from [Suite Config Model](suite-config-model.md).
2. Case fields from the fixture's `cases` item.
3. CLI filters and overrides.

Maps are deep-merged. Scalars replace earlier values. Lists replace earlier values unless the field explicitly supports append semantics. `tags` append and de-duplicate. `expected`, `unexpected`, and `steps` never inherit by default; shared expectations must be referenced with `expectRefs` in a later schema version.

## Prompt Variant Rules

- `title` is required. `id` is not part of the case schema; the runner derives a stable ID from title.
- `prompt` and `promptVariants` are mutually exclusive.
- A string `prompt` is shorthand for the same prompt under `skill` and `no-skill`.
- `promptVariants` keys may be variant names for exact matching.
- `no-skill` is the control fallback key.
- `skill` is the generic skill fallback key.
- `specific-skill[<skill-name>]` targets only variants using the named root skill.
- Skill prompts replace `$skill` with the selected skill reference, for example `$license-header`.
- If a skill prompt does not mention the selected skill reference, the runner adds an instruction to use that skill.

## Path Rules

- `suite.yaml` relative paths resolve relative to the suite file.
- `fixture.yaml` case `promptFile` paths resolve relative to the fixture directory.
- Assertion `path` values resolve relative to the copied run workspace.
- Assertion paths must not be absolute and must not escape the run workspace.
- Skill paths in root suite `skills` resolve relative to the suite file.
- `kind: skill` variants select a configured root skill by `skill`, unless the suite has exactly one configured skill.
- `kind: control` variants do not require `skill` and must not materialize the target skill.
- `diffIgnore` patterns are evaluated relative to the copied run workspace and use gitignore-like matching.

## Prompt Template Variables

The runner may expand these variables in `prompt`, `promptFile`, and step prompts:

| Variable | Meaning |
| --- | --- |
| `{{fixture_id}}` | Fixture ID. |
| `{{case_id}}` | Case ID. |
| `{{run_id}}` | Full run ID. |
| `{{model}}` | Selected model name. |
| `{{variant}}` | Selected variant name. |
| `{{variant_kind}}` | Selected variant kind, such as `skill` or `control`. |
| `{{workspace}}` | Absolute copied run workspace path. |
| `{{skill_root}}` | Project-local skill root, normally `.agents/skills`. |

Template expansion is optional in the first implementation. When implemented, unresolved variables must fail validation.

## Step Item

Each `steps` item must contain exactly one of `prompt`, `promptFile`, `expected`, or `unexpected`.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | no | Optional stable item ID. Generated from order when omitted. |
| `prompt` | string | no | Inline prompt injected into Codex. |
| `promptFile` | string | no | External prompt file relative to the fixture directory. |
| `promptVariants` | object | no | Prompt overrides keyed by variant name, `no-skill`, `specific-skill[<skill>]`, or `skill`. |
| `expected` | string | no | Expected event alias or canonical event name. |
| `unexpected` | string | no | Forbidden event alias or canonical event name. |
| `timeout` | duration | no | Optional step timeout. |

Prompt items create Codex turns. Expected and unexpected items are evaluated against the observation window after the nearest preceding prompt item and before the next prompt item. A case may contain prompt items with no expected or unexpected items; this is useful for logging probes and exploratory fixtures.

Expected and unexpected items in the same observation window are matched order-insensitively. The runner should evaluate each condition against the full set of normalized events and final states in that window, not by walking events in lockstep with YAML order.

For a single-prompt case, top-level `prompt`, `expected`, and `unexpected` are normalized as one prompt item followed by expectation items.

## Expected Object

Every expected or unexpected condition uses this common shape:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | no | Stable expectation ID. Generated from step and order when omitted. |
| `expected` | string | yes for expected items | Expected event alias or canonical event name. |
| `unexpected` | string | yes for unexpected items | Forbidden event alias or canonical event name. |
| `required` | boolean | no | Defaults to `true`. Non-required failures are warnings. |
| `message` | string | no | Human-readable intent. |
| `when` | object | no | Optional condition for applying the expectation. |

`expected` passes when at least one normalized event or final state in the observation window matches every specified field. Extra observed events are ignored. `unexpected` passes when no normalized event or final state in the observation window matches the condition. Matching is order-insensitive unless a future schema explicitly adds an ordering constraint.

The legacy fields `expect`, `not_expected`, `assertions[*].type`, and `negate` are not part of the canonical schema. The runner may support them as compatibility aliases by mapping `expect` to `expected`, `not_expected` to `unexpected`, `type` to `expected`, and `negate: true` to `unexpected`.

## Event Aliases

Human-readable aliases are allowed and normalized before evaluation:

| Alias | Canonical Event |
| --- | --- |
| `activate skill` | `skill_activated` |
| `read skill` | `skill_instruction_read` |
| `access reference` | `reference_accessed` |
| `execute script` | `script_executed` |
| `file changed` | `file_changed` |
| `file contains` | `file_contains` |
| `reply` | `assistant_response` |

Canonical event names such as `script_executed` are also allowed.

## Deterministic Expected Events

| Event | Required Fields | Optional Fields | Evaluation Target |
| --- | --- | --- | --- |
| `skill_available` | `skill` | `path` | `codex debug prompt-input` skill list. |
| `skill_activated` | `skill` | `minConfidence`, `evidence` | Derived `skill_activated` event. |
| `skill_instruction_read` | `skill` | `path` | Derived `skill_instruction_read` event. |
| `reference_accessed` | `skill`, `reference` | `path`, `exitCode` | Derived `reference_accessed` event. |
| `script_executed` | `skill`, `script` | `argvContains`, `exitCode`, `stdoutContains`, `stdoutRegex` | Derived `script_executed` event. |
| `file_exists` | `path` | none | Final run workspace. |
| `file_not_exists` | `path` | none | Final run workspace. |
| `file_contains` | `path`, one of `text` or `regex` | `count`, `minCount`, `maxCount` | Final file content. |
| `file_changed` | `path` | `status` | Captured filesystem diff. |
| `final_message_contains` | one of `text` or `regex` | none | Final assistant message. |
| `event_count_min` | `eventType`, `min` | `itemType` | Raw or normalized event log. |
| `token_usage_max` | `field`, `max` | none | `turn.completed.usage`. |

`skill_available` is evaluated from SDK-visible skill context captured before execution. `skill_activated` is satisfied by reading the target `SKILL.md`. `reference_accessed` and `script_executed` are derived from SDK events or diagnostic command evidence plus skill metadata.

`skill_activated` may be omitted from `expected`. When a case or suite declares a required skill, the runner should infer an implicit non-failing activation check for reporting. A missing explicit `skill_activated` expectation does not fail the case by itself.

## LLM-Judged Expected Events

## Usage Evaluation

`usageEvaluations` define follow-up turns that run prompts in the generated workspace after the main run. They are useful for documentation and spec-generation skills where artifact searchability, answerability, and downstream task usefulness are key outcomes.

Usage evaluations run after the main Codex task and file diff capture. They use the same model, fixture, variant, attempt, and run workspace as the main run by default. They may modify the workspace; such changes are captured separately from generation diffs.

```yaml
usageEvaluations:
  - id: retry-policy-query
    prompt: |
      Use this workspace's generated documentation and answer:
      What is the default maximum retry attempt count?
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

Usage evaluation fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | yes | Stable usage evaluation ID. |
| `prompt` | string | yes unless `promptFile` | Follow-up prompt executed in the generated workspace. |
| `promptFile` | string | yes unless `prompt` | Prompt file relative to the case file. |
| `outputSchema` | object | yes | Structured output schema expected from the model. |
| `expected` | object | no | Deterministic checks against structured output. |
| `timeout` | duration | no | Overrides suite usage evaluation timeout. |
| `sameModel` | boolean | `true` | Must default to using the same model as the main run. |

Usage evaluation metrics are recorded separately from the main run: input tokens, output tokens, duration, structured output validity, and deterministic accuracy status.

Recommended structured output fields:

| Field | Type | Notes |
| --- | --- | --- |
| `valid` | boolean | Whether the model considers the answer valid for the requested task. |
| `answer` | string/object | Main answer. Object is allowed for task-specific schemas. |
| `citations` | array | Referenced files, sections, commands, or evidence. |
| `confidence` | number | Optional confidence score. |
| `errors` | array | Optional list of problems encountered. |

## Command Judge Checks

`judgeCommands` define optional validation commands run in the generated workspace. They are useful for checks such as `npm run test`, `pytest`, or build commands.

```yaml
judgeCommands:
  - id: npm-test
    command: npm run test
    expectedExitCode: 0
    timeout: 2m
    rubric: |
      Passing tests indicate the generated documentation helper still builds.
```

Command judge fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | yes | Stable command check ID. |
| `command` | string/array | yes | Command to execute in the generated workspace. |
| `cwd` | string | no | Relative working directory inside the generated workspace. |
| `expectedExitCode` | integer | no | Defaults to `0`. |
| `timeout` | duration | no | Per-command timeout. |
| `rubric` | string | no | Optional LLM judge rubric for interpreting output beyond exit code. |

Command output, exit code, duration, and stdout/stderr previews must be retained as artifacts. A command check can be deterministic by exit code alone or LLM-judged when a rubric is provided.

| Type | Required Fields | Optional Fields | Evaluation Target |
| --- | --- | --- | --- |
| `llm_final_answer_quality` | `rubric` | `minScore` | Final message plus selected evidence. |
| `llm_file_semantics` | `path`, `rubric` | `minScore` | File content or diff. |
| `llm_behavior_trace` | `rubric` | `minScore`, `includeEvents` | Normalized events and final message. |

LLM expectations must be clearly marked as non-deterministic in reports and must retain judge prompt and response artifacts.

## Setup Commands

`setup` commands are deterministic commands executed before Codex starts. They are intended for local fixture preparation, not for testing Codex behavior.

```yaml
setup:
  - command: go mod tidy
    timeout: 30s
```

Setup command output is recorded separately from Codex SDK events and must not satisfy `script_executed`, `reference_accessed`, or `skill_activated` expectations.

## Validation Rules

- `id` fields must match `[a-z0-9][a-z0-9._-]*`.
- A single-prompt case may define exactly one of `prompt` or `promptFile`.
- A multi-step case must define `steps` and must not define top-level `prompt` or `promptFile`.
- A `steps` item must define exactly one of `prompt`, `promptFile`, `expected`, or `unexpected`.
- A fixture case normally omits `workspace`; standalone cases may define it.
- `expected` and `unexpected` are optional. A prompt-only case is valid and is treated as an observation/logging case.
- Unknown expected event names are validation errors.
- Unknown fields are validation warnings by default and errors in strict mode.
- A referenced skill must exist in the selected variant matrix or project-local skill root after materialization.

## Related Documents

- [Suite Config Model](suite-config-model.md)
- [Workspace Fixture](workspace-scenario-set.md)
- [Test Case Model](test-case-model.md)
- [Assertion Engine](assertion-engine.md)
- [Event Log Model](event-log-model.md)
- [Retry And Stability Policy](retry-and-stability-policy.md)

## Native-Language Summary

テスト定義は `suite.yaml` と `fixtures/<fixture>/fixture.yaml` の2層YAMLで表す。fixtureディレクトリ名をid/titleとし、`workspace/` は固定、caseは `fixture.yaml` の `cases` 配列に書く。caseは `title` だけを必須とし、idはtitleから生成する。promptは `promptVariants` でvariant名、`no-skill`、`skill`、`specific-skill[<skill>]` を切り替えられる。caseは `steps` に prompt、expected、unexpected を順番に並べられる。prompt間のexpected/unexpectedは順不同で評価し、書かれた期待だけを検証し、余分な観測イベントは許容する。
