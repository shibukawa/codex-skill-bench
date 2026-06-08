---
id: "codex-runner"
type: "batch-component"
title: "Codex Runner"
aliases:
  - "execution engine"
tags:
  - "python"
  - "codex"
  - "process"
facts:
  lifecycle.status: "blueprint"
  owner: "tooling"
---

# Codex Runner

## Summary

The Codex Runner materializes isolated run directories, prepares project-local skills, invokes Codex through the Python Codex SDK, and captures normalized execution artifacts.

## Responsibilities

- Copy or generate the test workspace fixture, including fixed fixture workspaces under `fixtures/<fixture-id>/workspace/`.
- Install or overlay the selected skill implementation variant into the copied run workspace's project-local skill root, unless the selected variant is a no-skill control.
- Build the Codex execution request with configured model, sandbox, approval, network, timeout, and output paths.
- Load and merge `.env.skill` files according to [Security And Isolation Policy](security-and-isolation-policy.md).
- Capture normalized SDK result events into an events artifact.
- Capture the final assistant message from SDK result data.
- Preserve SDK diagnostics, exit status where available, duration, and environment metadata.
- Snapshot file changes after the run.
- Run artifact-usage evaluations after the main run when configured, using the same model under test by default.
- Apply suite-level security, network, approval, redaction, and cleanup policy.

## Interfaces

### Input

- [Test Case Model](test-case-model.md)
- [Workspace Fixture](workspace-scenario-set.md)
- Suite-level defaults for model list, sandbox mode, timeout, output directory, and security policy.
- Skill variant definitions from [Comparison Matrix](comparison-matrix.md).

### Output

- Raw event file: `results/<run-id>.events.jsonl`
- Final message file: `results/<run-id>.final.md`
- Stderr file: `results/<run-id>.stderr.log`
- Filesystem diff summary for [Assertion Engine](assertion-engine.md)
- Normalized metadata for [Report Generator](report-generator.md)

## Execution Rules

- Each run must use a clean workspace directory.
- When a scenario belongs to a [Workspace Fixture](workspace-scenario-set.md), each run must copy the fixture's fixed `workspace/` directory into a fresh run workspace before Codex starts.
- Each run should inherit the logged-in `CODEX_HOME` unless a suite explicitly requests an advanced isolated-auth mode.
- Each skill-enabled run must place the selected root `skills` entry under the copied workspace, defaulting to `.agents/skills/<skill-name>/`.
- Each no-skill control run must skip target skill materialization.
- The runner must not mutate source fixtures, fixture workspaces, or canonical skill variant directories.
- Timeouts must terminate the Codex process and mark the run as errored.
- The runner must emit human-readable progress events to the CLI before long-running phases: workspace preparation, skill materialization, skill preload start/end, main Codex run start, run completion, and summary write completion.
- Progress events must identify the run ID and, when running a batch, the current run index and total selected runs.
- Progress output is diagnostic and must go to stderr through the CLI layer, not to result artifacts or stdout run listings.
- Non-zero Codex exit code does not automatically fail every assertion; it is exposed as an assertion target.
- Environment variables passed to Codex must follow the configured policy from [Security And Isolation Policy](security-and-isolation-policy.md).
- `.env.skill` values must be merged before env allow/deny and redaction rules are applied.
- The runner must record environment variable names passed to Codex, but not secret-looking values.
- Cleanup must follow the suite cleanup policy after artifacts and file-change summaries are captured.

## Parallel Execution

The runner may execute independent attempts concurrently. Parallelism must never share mutable run workspaces, SDK conversations, retry state, or result artifact paths.

Rules:

- `--parallel <n>` limits concurrent Codex SDK runs.
- Each case/model/variant/attempt gets its own run workspace and SDK conversation.
- Retries for the same logical run should be serialized unless a future policy explicitly supports speculative attempts.
- Parallel workers must respect suite-level rate limits, timeouts, and cleanup policy.
- Reports should preserve deterministic ordering by run ID even when execution is concurrent.

## Artifact-Usage Evaluation Runs

After the main Codex run completes and artifacts are available, the runner may execute configured usage evaluations. These are follow-up turns that ask the same model under test to query or use the generated artifacts.

Rules:

- Usage evaluations default to the same model, variant, fixture, case, attempt, workspace, and SDK configuration as the generation run.
- Usage evaluations must request structured output according to the case `outputSchema`.
- Usage evaluations must record token usage and duration separately from the main run.
- Usage evaluations may mutate the generated workspace. The runner must capture usage-evaluation diffs separately from generation diffs.
- Structured output parse failure is `usage_evaluation_failed`.

## SDK Execution

Execution is implemented through the Codex SDK from the Python runner. The suite schema does not include a `codex` object.

The SDK request must include:

| Backend field | Source |
| --- | --- |
| `prompt` | Current test step prompt. |
| `cwd` | Copied run workspace. |
| `model` | Suite/model matrix selection. |
| `sandbox` | Resolved `security.sandbox`. |
| `approvalPolicy` | Resolved `security.approval`. |
| `config` | Resolved Codex config overrides, including network policy. |
| `profile` | Optional Codex profile. |

For multi-prompt test cases, the runner should keep a single SDK conversation for the case attempt when the SDK supports replies. Retry attempts must start a new conversation.

## Skill Visibility Preflight

Codex SDK skill discovery is assumed to work for project-local skills materialized under the configured skill root. The runner should still include a preflight check that records whether the selected skill appears in the SDK-visible prompt or session context before a run starts.

For skill-enabled variants, missing skill visibility should be classified as a setup failure, not an assertion failure. For no-skill control variants, visible target skill evidence should be classified as a setup failure unless the variant explicitly allows ambient skills.

## File Change Capture

File change capture must not require Git. A fixture copy may not be a repository, and test workspaces are temporary directories.

The runner must take a filesystem snapshot before Codex starts and another snapshot after Codex exits. The baseline snapshot should be captured after deterministic setup is complete, including fixture copy and skill variant materialization. Runner-managed paths should be excluded from behavioral diffs by default, including result directories and the configured project-local skill root such as `.agents/skills`.

The snapshot and diff implementation should:

- recursively walk the run workspace,
- record relative paths, type, mode where practical, size, and sha256 for regular files,
- treat missing, new, and changed hashes as `deleted`, `added`, and `modified`,
- generate bounded unified diffs for text files,
- produce binary-file summaries without embedding binary content,
- avoid reading or reporting files excluded by suite ignore rules.

`diffIgnore` patterns from the case definition are gitignore-like patterns evaluated relative to the run workspace. They exclude matching paths from file-change assertions, text previews, and report diffs. Built-in ignores should include runner-managed result paths and project-local skill materialization paths such as `.agents/skills/`.

The runner must record at least:

| Field | Notes |
| --- | --- |
| `path` | Relative path inside run workspace. |
| `status` | `added`, `modified`, `deleted`, or `unchanged` when explicitly tracked. |
| `contentSha256` | Hash for final content when file exists. |
| `textPreview` | Optional bounded preview for reports and LLM judging. |
| `diff` | Optional unified diff for text files. |

## Dependencies

- Python `openai-codex` SDK.
- Filesystem copy and diff implementation.
- JSON event parser for [Event Log Model](event-log-model.md).
- Redaction helper for report previews and generated HTML.
- Git is not required for file change detection.

## Reads

- [Test Case Model](test-case-model.md)
- [Workspace Fixture](workspace-scenario-set.md)
- [Comparison Matrix](comparison-matrix.md)
- [Project Local Skill Materialization Policy](project-local-skill-materialization-policy.md)
- [Security And Isolation Policy](security-and-isolation-policy.md)

## Writes

- [Event Log Model](event-log-model.md)
- [Report Generator](report-generator.md)

## Related Requirements

- [Codex Skill Bench System](codex-skill-bench-system.md)

## Native-Language Summary

Codex Runner は、`fixtures/<fixture>/workspace/` などのfixtureとskill variantをrun workspaceに展開し、ログイン済みCODEX_HOMEを継承してCodex SDKを呼び出し、イベント、最終応答、診断情報、ファイル差分を保存する。
