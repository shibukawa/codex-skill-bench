---
id: "suite-config-model"
type: "data-model"
title: "Suite Config Model"
aliases:
  - "suite.yaml"
  - "root test configuration"
tags:
  - "yaml"
  - "suite"
  - "fixtures"
facts:
  lifecycle.status: "blueprint"
  data.name: "SuiteConfig"
---

# Suite Config Model

## Summary

The suite config is the root YAML file that controls a complete evaluation run. It lives above `fixtures/`, defines which fixtures and cases to discover, which models and skill variants to run, how Codex is invoked, and how stability and reporting are handled.

## Canonical Layout

```text
suite.yaml
fixtures/
  go-sample-project/
    workspace/
    fixture.yaml
results/
```

## Fields

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `version` | integer | yes | Suite schema version. Initial value is `1`. |
| `name` | string | yes | Human-readable suite name. |
| `fixtures` | object | no | Discovery root and exclude filters. Defaults to `fixtures/`. |
| `skills` | array | no | Explicit skill source directories available to skill variants. |
| `models` | array | yes | Codex model names or model configs to evaluate. |
| `variants` | array | no | Skill implementation variants and optional no-skill control variants. Defaults to one `default` variant. |
| `security` | object | no | Environment, network, approval, redaction, and cleanup policy. |
| `usageEvaluation` | object | no | Artifact-usage evaluation settings using the same model under test. |
| `judge` | object | no | Optional heuristic LLM judge configuration. |
| `runner` | object | no | Local execution settings such as parallelism and rate limiting. |
| `defaults` | object | no | Default timeout, skills, assertions, artifacts, and judge settings for cases. |
| `stability` | object | no | Attempt count and pass policy for nondeterministic behavior. |
| `report` | object | no | YAML, HTML, artifact retention, and comparison settings. |

## Fixture Discovery

`fixtures` may define:

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `root` | string | `fixtures` | Directory containing workspace fixtures. |
| `exclude` | array | none | Fixture ID glob patterns to exclude. |

## Skill Settings

The root `skills` array defines explicit skill source directories that can be selected by variants. Entries may be strings or objects.

String form:

```yaml
skills:
  - .agents/skills/local-agents-probe
```

Object form:

```yaml
skills:
  - name: license-header
    path: ../../demo-skill/license-header
    materializeAs: license-header
```

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `skills[]` | string | none | Explicit source skill directory. Skill name is inferred from the directory basename. |
| `skills[].name` | string | path basename | Logical skill name used by variants. |
| `skills[].path` | string | required | Explicit source skill directory containing `SKILL.md`. |
| `skills[].materializeAs` | string | `name` | Destination directory name under `.agents/skills`. |

Rules:

- A suite may define multiple skills so variants can compare different skill implementations.
- Skill source paths are resolved relative to the suite file unless absolute.
- Skill-enabled variants should reference a configured skill by `skill`.
- If a suite defines exactly one skill, a `kind: skill` variant may omit `skill` and use that single skill.
- The runner must materialize only the skill selected by the current variant.

## Variant Settings

Each `variants` entry defines either a skill-enabled variant or a no-skill control variant.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `name` | string | required | Variant ID used in run identity and reports. |
| `kind` | string | `skill` | `skill` or `control`. `control` means no target skill is materialized. |
| `skill` | string | required for `kind: skill` unless exactly one root skill exists | Root `skills` entry to materialize. |
| `materializeAs` | string | selected skill materialization name | Skill directory name under `.agents/skills`. Overrides `skills[].materializeAs`. |
| `controlOf` | string | none | Optional skill variant name this no-skill control should be compared against. |
| `allowAmbientSkills` | boolean | `false` | For control variants only. When false, visible target skills cause setup failure. |

Rules:

- `kind: skill` variants must materialize exactly the selected root skill unless the case intentionally tests multiple skills.
- `kind: control` variants must not materialize the target skill.
- Control variants should run the same prompts and assertions as skill variants unless the case overrides variant behavior.
- A control variant should verify that the target skill is not visible in Codex SDK preflight before execution.
- Reports should use `controlOf` or matching case/model dimensions to compare skill-enabled behavior with no-skill behavior.

## Security Settings

`security` may define:

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `env.policy` | string | `minimal` | `minimal`, `inherit`, or `empty`. |
| `env.allow` | array | baseline | Environment variable names allowed in addition to baseline. |
| `env.denyPatterns` | array | secret-like patterns | Environment variable name patterns to suppress or redact. |
| `env.loadFixtureEnv` | boolean | `true` | Load `fixtures/.env.skill` and fixture-specific `.env.skill` files. |
| `sandbox` | string | `workspace-write` | Passed to Codex SDK thread and turn execution. |
| `network` | boolean | `false` | Suite-level network policy for Codex runs. Maps to `sandbox_workspace_write.network_access` for `workspace-write`. |
| `approval` | string | `never` | Suite-level Codex approval mode. Maps to the Codex SDK approval mode field. |
| `redaction.enabled` | boolean | `true` | Redact secret-looking values from report previews and HTML. |
| `cleanup` | string | `on_pass` | `always`, `on_pass`, or `never`. |

## Stability Settings

`stability` may define:

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `maxAttempts` | integer | `3` | Maximum total attempts including the first attempt. |
| `retryOn` | array | `failed`, `errored` | Run statuses that trigger another attempt. |
| `passPolicy` | string | `any` | `all`, `any`, `majority`, or `threshold`. |
| `threshold` | number | none | Required pass ratio when `passPolicy` is `threshold`. |
| `classifyFlaky` | boolean | `true` | Mark mixed outcomes across attempts as flaky. |
| `stopOnPass` | boolean | `true` | Stop retrying after the first passing attempt when the pass policy allows it. |

## Usage Evaluation Settings

`usageEvaluation` configures follow-up artifact queries that use the same Codex model under test.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `enabled` | boolean | `false` | Allows artifact-usage evaluation steps. Disabled by default unless a suite or case opts in. |
| `sameModel` | boolean | `true` | Must default to true for fair model comparison. |
| `timeout` | duration | `2m` | Per usage-evaluation turn timeout. |
| `structuredOutput` | boolean | `true` | Usage evaluation should request structured output. |
| `cache` | boolean | `false` | Disabled by default because model/variant artifact behavior is the measured output. |

Rules:

- Usage evaluation must use the same model as the generation run unless a case explicitly opts out.
- Usage evaluation token usage and duration are reported separately from generation token usage and duration.
- Usage evaluation accuracy is evaluated from structured output with deterministic assertions.

## Judge Settings

`judge` configures optional heuristic LLM-judged assertions. It is separate from artifact-usage evaluation.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `enabled` | boolean | `false` | Allows LLM-judged assertions. Disabled by default unless a suite or case opts in. CLI `--deterministic-only` overrides to false. |
| `model` | string | implementation default | Stable, inexpensive model used for all LLM judge calls unless explicitly overridden. |
| `temperature` | number | `0` | Judge should be as deterministic as the provider allows. |
| `timeout` | duration | `2m` | Per-judge-call timeout. |
| `cache` | boolean | `true` | Cache judge results by prompt, evidence hash, rubric, and judge config. |
| `maxEvidenceBytes` | integer | implementation default | Bound evidence sent to the judge. |
| `compareEfficiency` | boolean | `false` | When true, run optional judge prompts over skill/control token and duration deltas. |

Rules:

- Prefer artifact-usage evaluation and deterministic structured-output checks when the question can be expressed as a task against generated artifacts.
- Use LLM judge only for heuristic quality questions that cannot be reduced to structured output or deterministic checks.
- Efficiency comparison should be deterministic when thresholds are configured, and may additionally use `judge.compareEfficiency` for qualitative assessment of whether token/time savings are meaningful for the task.
- Judge prompt, response, model, config, evidence hash, and cache hit status must be retained as artifacts.

## Runner Settings

`runner` controls local execution behavior.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `parallel` | integer | `1` | Maximum concurrent Codex SDK runs. CLI `--parallel` overrides this value. |
| `rateLimit` | object | none | Optional future limits for requests per minute or concurrent judge calls. |

Rules:

- Parallelism applies only to independent case/model/variant/attempt runs.
- Retries for the same logical run are serialized by default.
- Result ordering must be stable even when execution is concurrent.

## Example

```yaml
version: 1
name: codex skill bench

fixtures:
  exclude:
    - experimental-*

skills:
  - name: spec-compiler
    path: ../skills/spec-compiler
  - name: spec-compiler-experimental
    path: ../skills/spec-compiler-experimental
    materializeAs: spec-compiler

models:
  - gpt-5.5

variants:
  - name: default
    kind: skill
    skill: spec-compiler
  - name: experimental
    kind: skill
    skill: spec-compiler-experimental
  - name: no-skill
    kind: control
    controlOf: default

security:
  sandbox: workspace-write
  env:
    policy: minimal
    loadFixtureEnv: true
    allow:
      - PATH
      - SHELL
      - HOME
      - USER
      - TMPDIR
      - LANG
      - TERM
    denyPatterns:
      - "*TOKEN*"
      - "*SECRET*"
      - "*PASSWORD*"
      - "AWS_*"
  network: false
  approval: never
  redaction:
    enabled: true
  cleanup: on_pass

defaults:
  timeout: 10m
  skills:
    - spec-compiler

judge:
  enabled: false
  model: inexpensive-judge-model
  temperature: 0
  cache: true
  compareEfficiency: false

usageEvaluation:
  enabled: false
  sameModel: true
  structuredOutput: true
  timeout: 2m

runner:
  parallel: 2

stability:
  maxAttempts: 3
  retryOn:
    - failed
    - errored
  passPolicy: any
  classifyFlaky: true

report:
  resultsDir: results
  html: true
  yaml: true
```

## Rules / Constraints

- `suite.yaml` is the primary CLI input for `run`, `validate`, and `list`.
- All relative paths in the suite config are resolved relative to the suite file.
- Case-level fields override suite-level defaults.
- The runner must reject unknown required schema versions.
- The runner must preserve enough resolved configuration in each run result to reproduce the invocation.
- The default configuration must preserve the user's logged-in `CODEX_HOME` and materialize skill variants into the copied run workspace.
- Control variants must not materialize the target skill and must fail preflight if the target skill is still visible unless `allowAmbientSkills` is true.
- Security settings are suite-level defaults because they describe the operating assumptions of the skill under test.
- Stability settings can be overridden per model, fixture, and case as defined in [Retry And Stability Policy](retry-and-stability-policy.md).
- Usage evaluation uses the same model under test and is reported separately from generation metrics.
- Judge settings are optional heuristic evaluation settings and should not replace usage evaluation for artifact-query tasks.

## Related Documents

- [Test Definition Format](test-definition-format.md)
- [Workspace Fixture](workspace-scenario-set.md)
- [Test Case Model](test-case-model.md)
- [Codex Runner](codex-runner.md)
- [Comparison Matrix](comparison-matrix.md)
- [Project Local Skill Materialization Policy](project-local-skill-materialization-policy.md)
- [Security And Isolation Policy](security-and-isolation-policy.md)
- [Retry And Stability Policy](retry-and-stability-policy.md)
- [Deterministic And LLM Assertion Policy](deterministic-and-llm-assertion-policy.md)
- [Artifact Usage Evaluation Policy](artifact-usage-evaluation-policy.md)
- [Python Implementation Policy](python-implementation-policy.md)

## Native-Language Summary

`suite.yaml` は `fixtures/` の親に置く全体設定で、利用モデル、rootの `skills` 配列、skill variant、skillなしcontrol、security内のCodex SDK実行設定、fixture discovery、安定化、レポート出力をまとめて制御する。
