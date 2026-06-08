# Codex Skill Bench Format Reference

This reference summarizes the suite and fixture formats so the skill works outside the source repository.

## Layout

```text
suite.yaml
fixtures/
  README.md
  <fixture-id>/
    fixture.yaml
    workspace/
      ...
results/
```

`fixture-id` is the fixture directory name. The runner copies `workspace/` into a fresh run directory for every selected case, model, variant, and attempt.

## suite.yaml

Minimal skill/control comparison:

```yaml
version: 1
name: my skill suite

fixtures:
  root: fixtures

skills:
  - path: path/to/skill

models:
  - default

variants:
  - name: with-skill
    kind: skill
  - name: no-skill
    kind: control
    controlOf: with-skill

security:
  sandbox: workspace-write
  network: false
  approval: never

runner:
  parallel: 1

report:
  resultsDir: results
```

### Supported Fields

- `version`: suite schema version. Use `1`.
- `name`: human-readable suite name.
- `fixtures.root`: fixture directory relative to `suite.yaml`; defaults to `fixtures`.
- `fixtures.exclude`: optional fixture ID glob deny-list.
- `skills`: source skill directories. Entries may be strings or objects.
- `models`: required list of model names. Use `default` to omit the SDK model argument and let Codex choose its configured default.
- `variants`: variant matrix. Defaults to one `default` variant if omitted.
- `security.sandbox`: passed to Codex SDK. Supported values are `read-only`, `workspace-write`, and `full-access`.
- `security.approval`: `never` maps to deny-all; other values currently map to auto-review.
- `security.network`: documented suite policy; current MVP records/configures security but does not expose every future network option.
- `runner.parallel`: recorded in config; current MVP runs sequentially.
- `runner.skillPreloadPrompt`: optional prompt for the separate skill preload measurement.
- `report.resultsDir`: default output directory when `--results` is omitted.
- `defaults`: accepted by the loader for future/default data, but most default merging is not implemented in the MVP.

When the current directory contains `suite.yaml`, the suite path can be omitted for `list`, `eval`, `csb list`, `csb eval`, and `csb run`.

### skills Entries

String form:

```yaml
skills:
  - ../skills/license-header
```

Object form:

```yaml
skills:
  - name: license-header
    path: ../skills/license-header
    materializeAs: license-header
```

Rules:

- Relative skill paths resolve from the directory containing `suite.yaml`.
- String entries infer the skill name from the directory basename.
- Object entries require `path`; `name` defaults to the path basename.
- `materializeAs` controls the destination under `.agents/skills/`.
- If exactly one skill is configured, a `kind: skill` variant may omit `skill`.
- If multiple skills are configured, each skill variant must name the selected `skill`.

### variants Entries

Skill variant:

```yaml
variants:
  - name: current
    kind: skill
    skill: license-header
```

Control variant:

```yaml
variants:
  - name: no-skill
    kind: control
    controlOf: current
```

Fields:

- `name`: required variant ID used in run IDs and reports.
- `kind`: `skill` or `control`; defaults to `skill`.
- `skill`: configured root skill name selected by this variant.
- `materializeAs`: override destination skill directory for this variant.
- `controlOf`: names the skill variant this control compares against.
- `allowAmbientSkills`: parsed for future control preflight behavior.

Skill variants materialize the selected source skill into the copied run workspace at `.agents/skills/<name>/`. Control variants skip materialization.

## fixture.yaml

Minimal fixture file:

```yaml
cases:
  - title: Add license header
    timeout: 5m
    prompt: |
      Add an MIT license header to src/sample.py.
```

Fixture rules:

- The file lives at `fixtures/<fixture-id>/fixture.yaml`.
- `workspace/` beside it is the source workspace snapshot.
- `cases` is a list. Each case is independent.
- Case ID defaults to the lowercased title with non-safe characters replaced by `-`.
- Case IDs must be unique within the fixture.

## Case Fields

Current MVP fields:

- `title`: required.
- `id`: optional explicit case ID; if omitted, derived from `title`.
- `prompt`: inline prompt. Mutually exclusive with `promptVariants`.
- `promptFile`: prompt file path relative to the fixture directory.
- `promptVariants`: prompt map selected by variant.
- `timeout`: integer seconds or strings ending in `ms`, `s`, or `m`.

Planned/spec fields that may appear in docs but are not fully evaluated by the MVP include `description`, `tags`, `enabled`, `steps`, `expected`, `unexpected`, `usageEvaluations`, `judgeCommands`, `artifacts`, `diffIgnore`, `setup`, `stability`, case-level `models`, and case-level `variants`.

## Prompt Variant Resolution

For each run, prompt resolution is:

1. `promptVariants[variantName]`
2. `promptVariants["no-skill"]` for `kind: control`
3. `promptVariants["specific-skill[<skill-name>]"]` for matching skill variants
4. `promptVariants["skill"]` for any skill variant
5. `prompt`
6. `promptFile`

Rules:

- `prompt` and `promptVariants` are mutually exclusive.
- A string `prompt` is normalized internally as the same prompt for `skill` and `no-skill`.
- For skill variants, `$skill` is replaced with the resolved skill reference such as `$license-header`.
- If the resolved skill prompt does not mention that skill reference, the runner prefixes `Use the $<skill> skill.` so activation is still expected.

Example:

```yaml
cases:
  - title: Add MIT license headers
    timeout: 5m
    promptVariants:
      skill: |
        Use the $skill skill to add MIT license headers to src/sample.py and src/sample.go.
        Use year 2026 and owner Example Corp.
      no-skill: |
        Add MIT license headers to src/sample.py and src/sample.go.
        Use year 2026 and owner Example Corp.
```

## Fixture Authoring Checklist

- Keep the fixture workspace small and focused.
- Include only files needed for the task; avoid generated results, local credentials, dependency caches, and unrelated repo history.
- Make the requested outcome observable from files or final messages.
- Use a control prompt that is fair: same task, no explicit skill reference.
- Keep prompts deterministic where possible: specify exact filenames, year, owner, commands, or expected behavior.
- Run `list suite.yaml` before `eval`.
