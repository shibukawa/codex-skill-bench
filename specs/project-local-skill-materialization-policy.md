---
id: "project-local-skill-materialization-policy"
type: "architectural-decision"
title: "Project Local Skill Materialization Policy"
aliases:
  - "skill materialization"
  - "project-local skills"
tags:
  - "decision"
  - "codex"
  - "skills"
facts:
  lifecycle.status: "accepted"
---

# Project Local Skill Materialization Policy

## Summary

Skill-enabled variants should be materialized into the run workspace as project-local skills instead of changing `CODEX_HOME`. This preserves the user's logged-in Codex authentication while still allowing each run to test a specific skill implementation. No-skill control variants intentionally skip materialization so the suite can compare skill-enabled behavior with plain Codex behavior.

## Decision

The runner uses the real logged-in Codex home by default and places skill-enabled variants under the copied run workspace. The materialization path is `.agents/skills/<skill-name>/`. Suites define explicit source skills in the root `skills` array, and skill-enabled variants select one of those skills.

## Observed Behavior

`codex debug prompt-input` was run from the project workspace with probe skills in both locations. The resulting model input included:

- `local-agents-probe` from `.agents/skills/local-agents-probe/SKILL.md`
- `local-codex-probe` from `.codex/skills/local-codex-probe/SKILL.md`

This confirms that project-local skill discovery can be used without an isolated `CODEX_HOME`.

## Rationale

- A fresh `CODEX_HOME` does not inherit login state and was observed as `Not logged in`.
- Copying or storing authentication files in evaluation directories is a security risk.
- Project-local skills keep each run isolated at the workspace layer while preserving normal Codex auth, config, and model access.
- The run workspace is already copied per case, so variant materialization naturally fits there.

## Required Behavior

- The default runner must not change `CODEX_HOME`.
- The runner must materialize the selected skill variant into the copied run workspace before invoking Codex.
- The runner must skip materialization for `kind: control` variants.
- The project-local skill root is `.agents/skills`.
- The runner must read source skills from the root `skills` array. Each entry must be an explicit path or an object containing `path`.
- A suite may define multiple root skills so variants can compare skill implementations.
- A skill variant must select the configured root skill by `skill`, unless the suite defines exactly one skill.
- The runner must ensure only the selected variant for a run is present under the project-local skill root unless the case intentionally tests multiple skills.
- Result artifacts must record the materialized skill path, source path, and content hash.
- Result artifacts for no-skill control variants must record that no target skill was materialized.
- For no-skill control variants, the runner should verify during preflight that the target skill is not visible to Codex. Visible target skills should produce setup failure unless the variant explicitly allows ambient skills.

## Security Constraints

- Authentication files from `CODEX_HOME` must not be copied into run directories.
- Project-local skill directories created by the runner must be inside the copied run workspace.
- Skill source paths must be explicit and resolved relative to the suite file unless absolute.
- Skill materialization must be cleaned by deleting the copied run workspace, not by mutating the source skill variant.

## Related Documents

- [Suite Config Model](suite-config-model.md)
- [Codex Runner](codex-runner.md)
- [Comparison Matrix](comparison-matrix.md)

## Native-Language Summary

認証を壊さないため `CODEX_HOME` は差し替えず、suite rootの `skills` 配列で明示したskillだけを、skillありvariantごとのコピー済みworkspace内の `.agents/skills` 配下へ配置する。skillなしcontrol variantでは配置せず、対象skillが見えていないことをpreflightで確認する。
