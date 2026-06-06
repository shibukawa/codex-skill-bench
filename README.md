# Codex Skill Bench

Codex Skill Bench runs small workspace-based benchmark cases for Codex skills. It copies a fixture workspace, optionally materializes a skill into that copy, runs Codex, captures the JSON event stream, and writes YAML reports with token and duration comparisons.

This repository currently contains the MVP runner. It supports one or more configured models and variants, but the intended first use is a single model with two variants: `with-skill` and `no-skill`.

## Requirements

- Python 3.11+
- `uv`
- A working Codex login when running real Codex cases

Run without installing the package:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git list examples/basic-suite/suite.yaml
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git eval examples/basic-suite/suite.yaml --results results/basic-suite-real
```

Run tests:

```bash
uv run pytest -q
```

## CLI

Initialize a suite in the current directory:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git init [skill-path]
```

If `skill-path` is omitted, `init` starts an interactive wizard. It creates `suite.yaml`, `fixtures/`, and `fixtures/README.md`.

Add a fixture from an existing workspace snapshot:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git add-fixture [name] [target-path] [prompt]
```

If arguments are omitted, `add-fixture` starts an interactive wizard. It creates `fixtures/<name>/workspace/` by copying `target-path`, then appends a test case to `fixtures/<name>/fixture.yaml` with `prompt: <prompt>`.

When `target-path` is the suite root, snapshot creation excludes `fixtures/` and project-local `.agent/skills/` or `.agents/skills/` directories.

List resolved runs without executing Codex:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git list <suite.yaml>
```

Evaluate a suite:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git eval <suite.yaml> [options]
```

`csb run` is kept as an alias for `eval` when using the grouped CLI entrypoint.

Options:

- `--results <dir>`: output directory. Defaults to `results`.
- `--model <name>`: run only models whose name exactly matches.
- `--variant <name>`: run only the named variant.
- `--fixture <text>`: run fixtures whose id contains the text.
- `--case <text>`: run cases whose id contains the text.

Use model name `default` to omit the SDK `model` argument and let Codex choose its configured default model.

## Fixture Layout

A suite points at a `fixtures` root. Each fixture is a directory with a fixed `workspace/` directory and a `fixture.yaml` containing its cases:

```text
examples/basic-suite/
  suite.yaml
  fixtures/
    README.md
    simple-python/
      fixture.yaml
      workspace/
        src/sample.py
```

The fixture directory name is the fixture id and title. The runner copies `workspace/` into each run directory before invoking Codex. The original fixture workspace is not modified. `fixtures/README.md` describes the local suite commands and explains `suite.yaml` and `fixture.yaml`.

## Suite Configuration

Example:

```yaml
version: 1
name: basic license header comparison

skills:
  - path: ../../demo-skill/license-header

models:
  - default

variants:
  - name: with-skill
    kind: skill
    skill: license-header
  - name: no-skill
    kind: control
    controlOf: with-skill

security:
  sandbox: workspace-write
  network: false
  approval: never

runner:
  parallel: 1
```

Fields:

- `fixtures.root`: fixture directory relative to the suite file.
- `fixtures.exclude`: optional fixture id glob deny-list.
- `skills`: explicit source skill directories. Entries may be strings or `{name, path, materializeAs}` objects.
- `models`: list of model names as strings.
- `variants`: run variants. `kind: skill` materializes a skill; `kind: control` does not.
- `variants[].skill`: root `skills` entry to materialize.
- `variants[].materializeAs`: skill directory name under `.agents/skills`.
- `variants[].controlOf`: names the skill variant this control compares against.
- `security.sandbox`: passed to Codex SDK thread and turn execution.
- `security.approval`: mapped to Codex SDK approval mode. Defaults to `never`.

Codex execution uses the Python Codex SDK. A `codex` object and `skillRoot` are not part of the suite schema.

`runner.parallel` is recorded in configuration, but this MVP currently runs sequentially.

## Fixture Configuration

`fixture.yaml`:

```yaml
cases:
  - title: Add license header
    prompt: |
      Add an MIT license header to src/sample.py.
```

Fields:

- `cases`: list of case definitions for this fixture.

The fixture id and title are the fixture directory name. The workspace directory is always `workspace/`.

## Case Configuration

Each `cases[]` item uses the case schema. Example:

```yaml
title: Add license header
timeout: 5m
promptVariants:
  skill: |
    Add an MIT license header to src/sample.py.
    Use year 2026 and owner Example Corp.
  no-skill: |
    Add an MIT license header to src/sample.py.
    Use year 2026 and owner Example Corp.
```

Prompt resolution order:

1. `promptVariants[variantName]`
2. `promptVariants["no-skill"]` for control variants
3. `promptVariants["specific-skill[<skill-name>]"]` for matching skill variants
4. `promptVariants["skill"]` for any skill variant
5. `prompt`
6. `promptFile`

`prompt` and `promptVariants` are mutually exclusive. A string `prompt` is normalized as the same prompt for both `skill` and `no-skill`.

For skill variants, `$skill` is replaced with the resolved skill reference such as `$license-header`. If the resolved prompt does not mention that skill reference, the runner prefixes a short instruction to use the selected skill so that the skill variant is still expected to activate the materialized skill.

`timeout` accepts integer seconds or strings ending in `ms`, `s`, or `m`.

## Internal Behavior

For each selected fixture, case, model, and variant, the runner:

1. Creates `results/runs/<run-id>/`.
2. Copies the fixture workspace into `results/runs/<run-id>/workspace`.
3. For `kind: skill`, copies the selected root `skills` entry into `<workspace>/.agents/skills/<materializeAs-or-skill-name>`.
4. Resolves the prompt for the current variant.
5. For skill variants, runs a separate preload thread first. This forced preload only measures skill-load cost and context size. It is not reused for the actual benchmark turn.
6. Runs the actual benchmark turn:

   The runner uses `openai_codex.Codex`, starts a new ephemeral thread with the run workspace as `cwd`, and calls `thread.run(...)`. The main benchmark prompt is passed as plain text; the runner does not force `SkillInput` for the benchmark turn. This keeps skill activation itself part of the test.

7. Writes the Codex JSON event stream, or SDK result summary, to `events.jsonl`.
8. Writes stderr to `stderr.log`.
9. Reads `turn.completed.usage` events and accumulates token usage.
10. Marks a skill variant as errored if the benchmark turn does not reference the materialized skill path, such as `.agents/skills/<skill>/...`, in the captured SDK event data.
11. Writes a per-run result YAML and an aggregate `summary.yaml`.

## Output

Each run has:

- `workspace`: copied workspace after Codex ran.
- `events.jsonl`: raw Codex JSON events.
- `final.md`: final assistant message captured by `--output-last-message`.
- `stderr.log`: Codex stderr or runner error.
- `preload.events.jsonl`, `preload.final.md`, `preload.stderr.log`: SDK skill preload artifacts for skill variants.
- `<run-id>.result.yaml`: per-run report.

The aggregate `summary.yaml` is grouped by:

```text
fixtures -> cases -> models -> variants -> attempts
```

It also includes `comparisons` entries for skill/control pairs:

```yaml
comparisons:
  - fixture: simple-python
    case: add-license
    model: default
    skillVariant: with-skill
    controlVariant: no-skill
    generationTokenDelta: -6718
    generationDurationDeltaMs: -5170
    generationEstimatedRepeatDurationDeltaMs: -3000
```

`generationTokenDelta` is `control.totalTokens - skill.totalTokens`.
`generationDurationDeltaMs` is `control.durationMs - skill.durationMs`.
`generationEstimatedRepeatDurationDeltaMs` is `control.durationMs - skill.estimatedRepeatDurationMs`.

Positive values mean the skill variant used fewer tokens or less time than the control.

For skill variants, each run also reports:

- `preload.durationMs`: time for the separate forced skill-load thread.
- `preload.usage`: token usage for that forced skill-load thread.
- `estimatedRepeatDurationMs`: `durationMs - preload.durationMs`, clamped at zero. This is a rough estimate of repeated-run latency after discounting the measured preload cost.

## Current Limitations

- The runner stores a normalized SDK result event rather than a raw CLI JSON stream.
- Assertions, LLM judges, command-based evaluation, retries, parallel execution, HTML reports, and artifact diffing are not implemented yet.
- Token usage depends on `turn.completed.usage` appearing in the Codex JSON event stream. Timed-out runs may have zero token usage if that event has not been emitted.

## License

This project is licensed under the GNU Affero General Public License v3.0 or later. See [LICENSE](LICENSE).
