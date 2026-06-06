---
id: "retry-and-stability-policy"
type: "requirement"
title: "Retry And Stability Policy"
aliases:
  - "retry policy"
  - "flaky policy"
  - "stability policy"
tags:
  - "retry"
  - "stability"
  - "models"
facts:
  lifecycle.status: "accepted"
---

# Retry And Stability Policy

## Summary

The runner retries failed runs by default to absorb model and tool flakiness while still reporting instability. Retry and stability settings can be defined globally, overridden per model, overridden per fixture, and finally overridden per case.

## Defaults

The default policy is:

```yaml
stability:
  maxAttempts: 3
  retryOn:
    - failed
    - errored
  passPolicy: any
  classifyFlaky: true
```

This means the runner executes one attempt first, then retries only when the run fails or errors, up to three total attempts. A case is considered passed if any attempt passes. If at least one attempt fails or errors and a later attempt passes, the case is marked `flaky` in reports.

## Fields

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `maxAttempts` | integer | `3` | Maximum total attempts including the first attempt. |
| `retryOn` | array | `failed`, `errored` | Run statuses that trigger another attempt. |
| `passPolicy` | string | `any` | `any`, `all`, `majority`, or `threshold`. |
| `threshold` | number | none | Required pass ratio when `passPolicy` is `threshold`. |
| `classifyFlaky` | boolean | `true` | Mark mixed outcomes as flaky. |
| `stopOnPass` | boolean | `true` | Stop retrying after the first passed attempt when `passPolicy` allows it. |

`attempts` is accepted as a compatibility alias for `maxAttempts`, but `maxAttempts` is canonical.

## Override Order

Resolved stability configuration is built in this order:

1. Suite-level `stability`.
2. Model-level `models[*].stability`.
3. Fixture-level `fixture.yaml` defaults or stability.
4. Case-level `stability` or compatibility `attempts`.
5. CLI overrides.

Later values override earlier values. Maps are deep-merged and scalar fields replace earlier values.

## Model Override Example

```yaml
models:
  - name: gpt-5.5
    stability:
      maxAttempts: 3
      passPolicy: any

  - name: gpt-5.5
    alias: gpt-5.5-high
    config:
      model_reasoning_effort: high
    stability:
      maxAttempts: 2
      passPolicy: all
```

## Case Override Example

```yaml
id: license-header-smoke
title: License header smoke test
stability:
  maxAttempts: 1
  passPolicy: all
steps:
  - prompt: |
      Use the $license-header skill to audit missing headers.
```

## Status Aggregation

| Attempt Outcomes | Aggregated Status |
| --- | --- |
| Any passed and `passPolicy: any` | `passed` or `flaky` when earlier attempts failed/errored. |
| All passed and `passPolicy: all` | `passed`. |
| Mixed pass/fail with `classifyFlaky: true` | `flaky` when policy allows success. |
| No attempt passed | `failed` or `errored` based on the dominant terminal status. |

Reports must show every attempt, the resolved stability policy, and the aggregated case result.

## Related Documents

- [Suite Config Model](suite-config-model.md)
- [Test Definition Format](test-definition-format.md)
- [Report Generator](report-generator.md)

## Native-Language Summary

デフォルトは失敗またはエラー時に最大3回まで再試行し、どれか1回成功すれば成功扱いにする。ただし失敗後に成功した場合はflakyとしてレポートする。設定はsuite、model、fixture、case、CLIの順に上書きする。
