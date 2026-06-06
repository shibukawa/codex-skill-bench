# Codex Skill Bench

Codex Skill Bench runs small workspace-based benchmark cases for Codex skills. It copies a fixture workspace, optionally materializes a skill into that copy, runs Codex, captures the JSON event stream, and writes YAML reports with token and duration comparisons.

This repository currently contains the MVP runner. It supports one or more configured models and variants, but the intended first use is a single model with two variants: `with-skill` and `no-skill`.

## Requirements

- Python 3.11+
- `uv`
- A working `codex` CLI login when running real Codex cases

Install and run through `uv`:

```bash
uv run codex-skill-bench list examples/basic-suite/suite.yaml
uv run codex-skill-bench run examples/basic-suite/suite.yaml --results results/basic-suite-real
```

Run tests:

```bash
uv run pytest -q
```

## CLI

List resolved runs without executing Codex:

```bash
uv run codex-skill-bench list <suite.yaml>
```

Run a suite:

```bash
uv run codex-skill-bench run <suite.yaml> [options]
```

Options:

- `--results <dir>`: output directory. Defaults to `results`.
- `--model <name>`: run only models whose name exactly matches.
- `--variant <name>`: run only the named variant.
- `--fixture <text>`: run fixtures whose id contains the text.
- `--case <text>`: run cases whose id contains the text.

Use model name `default` to omit `--model` when invoking Codex. This lets the logged-in Codex CLI choose its configured default model.

## Fixture Layout

A suite points at a `fixtures` root. Each fixture is a directory with a workspace and one or more case YAML files:

```text
examples/basic-suite/
  suite.yaml
  fixtures/
    simple-python/
      fixture.yaml
      workspace/
        src/sample.py
      cases/
        add-license.yaml
```

The runner copies `workspace/` into each run directory before invoking Codex. The original fixture workspace is not modified.

## Suite Configuration

Example:

```yaml
version: 1
name: basic license header comparison

fixtures:
  root: fixtures
  include:
    - simple-python
  caseGlob: cases/*.yaml

models:
  - name: default

variants:
  - name: with-skill
    kind: skill
    skillPath: ../../demo-skill/license-header
    materializeAs: license-header
  - name: no-skill
    kind: control
    controlOf: with-skill

codex:
  backend: cli
  bin: codex
  sandbox: workspace-write
  skillRoot: .agents/skills

security:
  network: false
  approval: never

runner:
  parallel: 1
```

Fields:

- `fixtures.root`: fixture directory relative to the suite file.
- `fixtures.include`: optional fixture id allow-list.
- `fixtures.exclude`: optional fixture id deny-list.
- `fixtures.caseGlob`: glob used inside each fixture directory. Defaults to `cases/*.yaml`.
- `models`: list of model entries. A string or `{name: ...}` is accepted.
- `variants`: run variants. `kind: skill` materializes a skill; `kind: control` does not.
- `variants[].skillPath`: source skill directory for skill variants.
- `variants[].materializeAs`: skill directory name under `codex.skillRoot`.
- `variants[].controlOf`: names the skill variant this control compares against.
- `codex.bin`: Codex CLI executable. Defaults to `codex`.
- `codex.sandbox`: passed to `codex exec --sandbox`.
- `codex.skillRoot`: where skills are copied inside the run workspace. Defaults to `.agents/skills`.
- `security.approval`: passed to `codex -a`. Defaults to `never`.
- `security.network`: passed as `sandbox_workspace_write.network_access=true|false`.

`codex.backend` and `runner.parallel` are recorded in configuration, but this MVP currently runs through the CLI backend sequentially.

## Fixture Configuration

`fixture.yaml`:

```yaml
id: simple-python
title: Simple Python fixture
workspace:
  path: workspace
```

Fields:

- `id`: fixture id used in run ids and reports.
- `workspace.path`: workspace directory copied for every run. Defaults to `workspace`.

## Case Configuration

Example:

```yaml
id: add-license
title: Add license header
timeout: 5m
promptByVariantKind:
  skill: |
    Use the $license-header skill to add an MIT license header to src/sample.py.
    Use year 2026 and owner Example Corp.
  control: |
    Add an MIT license header to src/sample.py.
    Use year 2026 and owner Example Corp.
```

Prompt resolution order:

1. `promptByVariant[variantName]`
2. `promptByVariantKind[variantKind]`
3. `prompt`
4. `promptFile`

`timeout` accepts integer seconds or strings ending in `ms`, `s`, or `m`.

## Internal Behavior

For each selected fixture, case, model, and variant, the runner:

1. Creates `results/runs/<run-id>/`.
2. Copies the fixture workspace into `results/runs/<run-id>/workspace`.
3. For `kind: skill`, copies `skillPath` into `<workspace>/<codex.skillRoot>/<materializeAs>`.
4. Resolves the prompt for the current variant.
5. Runs:

   ```bash
   codex -a <approval> \
     -c sandbox_workspace_write.network_access=<true|false> \
     exec --json --ephemeral --skip-git-repo-check \
     --sandbox <sandbox> \
     [--model <model>] \
     --cd <workspace> \
     --output-last-message <run-root>/final.md \
     <prompt>
   ```

6. Writes the Codex JSON event stream to `events.jsonl`.
7. Writes stderr to `stderr.log`.
8. Reads `turn.completed.usage` events and accumulates token usage.
9. Writes a per-run result YAML and an aggregate `summary.yaml`.

## Output

Each run has:

- `workspace`: copied workspace after Codex ran.
- `events.jsonl`: raw Codex JSON events.
- `final.md`: final assistant message captured by `--output-last-message`.
- `stderr.log`: Codex stderr or runner error.
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
```

`generationTokenDelta` is `control.totalTokens - skill.totalTokens`.
`generationDurationDeltaMs` is `control.durationMs - skill.durationMs`.

Positive values mean the skill variant used fewer tokens or less time than the control.

## Current Limitations

- The runner currently uses the Codex CLI compatibility path, not a Python Codex SDK backend.
- Assertions, LLM judges, command-based evaluation, retries, parallel execution, HTML reports, and artifact diffing are not implemented yet.
- Token usage depends on `turn.completed.usage` appearing in the Codex JSON event stream. Timed-out runs may have zero token usage if that event has not been emitted.
