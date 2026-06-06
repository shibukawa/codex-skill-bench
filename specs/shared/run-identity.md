---
id: "run-identity"
type: "glossary-term"
title: "Run Identity"
aliases:
  - "run id"
tags:
  - "naming"
facts:
  lifecycle.status: "blueprint"
---

# Run Identity

## Summary

A run identity uniquely identifies one execution of one test case scenario for one workspace fixture, one model, and one variant. Variants may be skill-enabled implementations or no-skill controls.

## Required Parts

| Part | Required | Notes |
| --- | --- | --- |
| `fixture_id` | yes | The workspace fixture identifier, with `standalone` when no fixture is used. |
| `case_id` | yes | The test case identifier. |
| `model` | yes | The Codex model or alias used for execution. |
| `variant` | yes | Variant name, with `default` when no variant is configured. |
| `variant_kind` | yes | `skill` for skill-enabled runs or `control` for no-skill runs. |
| `attempt` | yes | Numeric retry or repeat index, starting at `1`. |

## Rules

- Run IDs must be stable enough to map result files back to suite inputs.
- Run IDs must be filesystem-safe.
- A recommended format is `<fixture-id>__<case-id>__<model>__<variant>__attempt-<n>`.
- `variant_kind` should be stored in result metadata even when it is not included in the filesystem-safe run ID.

## Native-Language Summary

run identity は、fixture、case、model、variant、variant種別、attempt の組み合わせで一回のCodex実行を一意に表す。
