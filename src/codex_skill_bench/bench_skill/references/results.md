# Codex Skill Bench Results Reference

Use this reference to interpret output without needing the source repository specs.

## Run Directories

For each selected fixture, case, model, and variant, the runner creates:

```text
results/
  summary.yaml
  <run-id>.result.yaml
  runs/
    <run-id>/
      workspace/
      events.jsonl
      final.md
      stderr.log
      preload.events.jsonl
      preload.final.md
      preload.stderr.log
```

`preload.*` files exist only for skill variants. The preload run forces skill loading in a separate Codex SDK thread to measure skill-load cost. The actual benchmark turn is still separate.

## Run ID

Run IDs are joined with `__`:

```text
<fixture-id>__<case-id>__<model>__<variant>__attempt-1
```

Model and case IDs are path-safe normalized strings.

## Per-Run Result YAML

Each `<run-id>.result.yaml` contains `run:` with:

- `id`, `fixture`, `case`, `model`, `variant`, `variantKind`
- `status`: `passed` or `errored` in the MVP
- `durationMs`
- `estimatedRepeatDurationMs`: `durationMs - preload.durationMs`, clamped at zero for skill variants
- `exitCode`
- `usage`: token counters
- `preload`: separate preload status, duration, usage, and artifact paths for skill variants
- `artifacts`: paths to run root, workspace, events, final, stderr, result, and materialized skill
- `error`: runner error text when available

## summary.yaml

The aggregate groups results as:

```yaml
fixtures:
  <fixture-id>:
    cases:
      <case-id>:
        models:
          <model>:
            variants:
              <variant>:
                variantKind: skill
                attempts:
                  - ...
                aggregate:
                  status: passed
                  durationMs: 1234
                  estimatedRepeatDurationMs: 1000
                  usage:
                    totalTokens: 123
comparisons:
  - fixture: <fixture-id>
    case: <case-id>
    model: <model>
    skillVariant: with-skill
    controlVariant: no-skill
    generationTokenDelta: 100
    generationDurationDeltaMs: 500
    generationEstimatedRepeatDurationDeltaMs: 700
```

Comparison deltas are calculated as control minus skill:

- Positive `generationTokenDelta` means the skill variant used fewer total generation tokens.
- Positive `generationDurationDeltaMs` means the skill variant was faster including preload.
- Positive `generationEstimatedRepeatDurationDeltaMs` means the skill variant was faster after discounting measured preload cost.

## Token Usage

The runner reads usage from captured SDK result events. Counters include:

- `inputTokens`
- `cachedInputTokens`
- `outputTokens`
- `reasoningOutputTokens`
- `totalTokens`

If total tokens are absent, the MVP falls back to `inputTokens + outputTokens`. Timed-out or failed SDK runs may have zero usage if no usage event was emitted.

## Skill Activation

For skill variants, the MVP treats a run as errored if the benchmark turn does not reference the materialized skill path in captured SDK event data:

```text
.agents/skills/<skill-name>/
```

This is an activation proxy. It checks evidence in `events.jsonl`, not merely that the skill was copied into the workspace. If a skill variant errors with `skill was not activated`, inspect:

- the resolved prompt in the run context,
- whether the prompt mentions `$skill` or the concrete `$<skill-name>`,
- `events.jsonl` for reads or tool calls under `.agents/skills/<skill-name>/`,
- whether `materializeAs` changed the expected skill directory name.

## Debugging Checklist

- Missing fixture: confirm `fixtures.root` and fixture directory names.
- No runs listed: check `models`, `variants`, `fixtures.exclude`, and CLI filters.
- Unknown skill: ensure `variants[].skill` matches `skills[].name` or inferred basename.
- Workspace copy failure: ensure `fixtures/<fixture-id>/workspace/` exists.
- Codex SDK error: inspect `stderr.log`.
- Skill not activated: make the skill prompt explicit or use `$skill` in `promptVariants.skill`.
- Surprising control behavior: ensure the control variant does not materialize the target skill and the control prompt does not mention the skill.

## Planned But Not MVP

The broader specification includes deterministic assertions, file diffs, multi-step cases, retries, parallel execution, HTML reports, command judges, LLM judges, and artifact-usage evaluation. If a user asks for those, explain that the schema has planned concepts but the current MVP runner may parse or ignore fields without evaluating them.
