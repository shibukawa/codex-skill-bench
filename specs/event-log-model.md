---
id: "event-log-model"
type: "data-model"
title: "Event Log Model"
aliases:
  - "codex json events"
tags:
  - "jsonl"
  - "observability"
facts:
  lifecycle.status: "blueprint"
  data.name: "CodexEventLog"
---

# Event Log Model

## Summary

The event log model normalizes Codex SDK output so assertions and reports can reason about skill instruction reads, skill scripts, skill references, assistant messages, token usage, errors, and run progress without hard-coding every raw event detail.

## Fields

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `rawEvents` | array | yes | Parsed or normalized JSON objects from Codex SDK results and notifications. |
| `assistantMessages` | array | yes | Assistant text messages found in events. |
| `toolCalls` | array | yes | Tool invocations, including function name and arguments when available. |
| `commands` | array | yes | Diagnostic shell command records. These are retained for debugging but are not primary assertion targets. |
| `tokenUsage` | object | no | Input, output, cached, and total token counts when emitted. |
| `errors` | array | no | Structured or inferred run errors. |
| `lastMessagePath` | string | yes | Path to final message markdown. |

## Normalized Tool Call

| Field | Type | Notes |
| --- | --- | --- |
| `name` | string | Tool or function name. |
| `arguments` | object/string | Raw or parsed arguments. |
| `startedAt` | timestamp | Optional. |
| `completedAt` | timestamp | Optional. |
| `status` | string | `started`, `completed`, `failed`, or `unknown`. |

## Normalized Command

| Field | Type | Notes |
| --- | --- | --- |
| `cmd` | string | Command string or argv summary. |
| `workdir` | string | Working directory when available. |
| `exitCode` | integer | Exit code when available. |
| `stdoutPreview` | string | Optional bounded preview. |
| `stderrPreview` | string | Optional bounded preview. |

## Derived Skill Events

The evaluator must derive higher-level events from Codex SDK events, SDK-visible skill context, and project-local skill metadata. Test cases should assert these derived skill events instead of matching raw shell commands.

| Derived Event | Source Evidence | Required Normalized Fields |
| --- | --- | --- |
| `skill_activated` | `SKILL.md` for the target skill was read by Codex during the run. | `skill`, `path`, `instructionReadEventId`, `confidence` |
| `skill_instruction_read` | SDK event or diagnostic command evidence reading `.agents/skills/<skill>/SKILL.md`. | `skill`, `path`, `eventId`, `status` |
| `reference_accessed` | SDK event or diagnostic command evidence reading a source-linked reference file under the skill directory, commonly `references/`. | `skill`, `reference`, `path`, `sourceLink`, `eventId`, `status` |
| `script_executed` | SDK event or diagnostic command evidence invoking a file under `.agents/skills/<skill>/scripts/`. | `skill`, `script`, `path`, `argv`, `eventId`, `exitCode`, `stdoutPreview` |
| `assistant_response` | `agent_message` item or final message file. | `text`, `source` |

## Script And Reference Normalization

Skill scripts are the main command-level behavior that the benchmark cares about. The normalizer must identify script executions from SDK events when structured tool data is available, and from diagnostic command strings when only command text is available.

For `script_executed`, the normalizer must:

- unwrap the shell prefix such as `/bin/zsh -lc`,
- parse the inner command using shell-compatible tokenization,
- identify the script path token under `.agents/skills/<skill>/scripts/`,
- store remaining tokens as `argv`,
- expose both parsed `argv` and the original `command` string.

If parsing fails, the evaluator must keep `argv` empty or partial, set a parse diagnostic, and still preserve the original command string.

For `reference_accessed`, the normalizer should use source links declared in `SKILL.md` when available. A reference may be a file under `references/`, a path explicitly linked from `SKILL.md`, or another source file declared by the skill instructions. The normalized event must keep the resolved path and the originating source link so reports can show why the file counts as a skill reference.

## Historical CLI Probe Events

Earlier CLI probes observed that `codex exec --json` emitted one JSON object per line. These examples are retained as compatibility evidence for the normalizer, but the runner now uses Codex SDK results as its execution source. A no-tool CLI probe produced:

```json
{"type":"thread.started","thread_id":"019e76e6-77bd-72c1-be4d-3b11e3c5fa2a"}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"JSON_PROBE_OK"}}
{"type":"turn.completed","usage":{"input_tokens":12396,"cached_input_tokens":4480,"output_tokens":8,"reasoning_output_tokens":0}}
```

A shell-command run produced `command_execution` items:

```json
{"type":"item.started","item":{"id":"item_0","type":"command_execution","command":"/bin/zsh -lc pwd","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_0","type":"command_execution","command":"/bin/zsh -lc pwd","aggregated_output":"/Users/shibukawayoshiki/develop/codex-skill-bench\n","exit_code":0,"status":"completed"}}
```

The normalizer must initially support these event forms:

| Event Type | Item Type | Normalized Target |
| --- | --- | --- |
| `thread.started` | none | Run thread ID. |
| `turn.started` | none | Turn lifecycle marker. |
| `item.started` | `command_execution` | Command started event. |
| `item.completed` | `command_execution` | Command completion, output, exit code, and status. |
| `item.completed` | `agent_message` | Assistant message text. |
| `turn.completed` | none | Token usage and turn completion. |

## Observed Skill Workflow Evidence

Skill activation is defined as Codex reading the target skill's `SKILL.md`. Availability alone is not activation. During a `license-header` skill run, the JSONL stream did not emit a distinct raw `skill.activated` event. Instead, activation was observable through the instruction file read and should be lifted into derived events:

| Evidence | Observed Event Shape | Example |
| --- | --- | --- |
| Skill instructions read | `item.completed` with `item.type=command_execution` | `sed -n '1,220p' .agents/skills/license-header/SKILL.md` |
| Reference read | `item.completed` with `item.type=command_execution` | `sed -n '1,120p' .agents/skills/license-header/references/mit.txt` |
| Audit script run | `item.completed` with `item.type=command_execution` | `python3 .agents/skills/license-header/scripts/list_missing_license.py ...` |
| Mutation script run | `item.completed` with `item.type=command_execution` | `python3 .agents/skills/license-header/scripts/prepend_license.py ...` |
| Result summary | `item.completed` with `item.type=agent_message` | Final message naming used reference and scripts. |

Assertion logic should therefore treat `skill_activated` as an alias for the corresponding `SKILL.md` read event. It must not require a non-existent dedicated raw skill activation event.

## Rules / Constraints

- Raw JSONL must be preserved even when normalization is partial.
- Unknown event shapes must not crash the run by default; they must be retained and counted.
- Token usage assertions must tolerate missing usage data by returning an explicit `not_applicable` or `failed` status according to assertion configuration.
- The normalizer should be version-aware when Codex event schemas evolve.

## Reads

- `results/<run-id>.events.jsonl`
- `results/<run-id>.final.md`

## Related Requirements

- [Assertion Engine](assertion-engine.md)
- [Report Generator](report-generator.md)

## Native-Language Summary

CodexのSDKイベントや互換JSONLを保存しつつ、SKILL.md読み込み、reference参照、script起動、最終応答、token使用量などをassertionしやすい形に正規化する。
