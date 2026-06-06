---
id: "cli-interface"
type: "api"
title: "CLI Interface"
aliases:
  - "command line"
tags:
  - "python"
  - "cli"
facts:
  lifecycle.status: "blueprint"
  api.name: "codex-skill-bench"
---

# CLI Interface

## Summary

`codex-skill-bench` is a local Python CLI for initializing benchmark suites, adding workspace fixtures, running suites, validating case definitions, rendering reports, and inspecting previous results. The documented end-user invocation is installation-free through `uvx --from git+https://github.com/shibukawa/codex-skill-bench.git eval ...`.

## Endpoints / Operations

| Command | Purpose |
| --- | --- |
| `eval init [skill-path]` | Initialize `suite.yaml`, `fixtures/`, and `fixtures/README.md` in the current directory. |
| `eval add-fixture [name] [target-path] [prompt]` | Create a fixture workspace snapshot and append a prompt case to `fixture.yaml`. |
| `codex-skill-bench run <suite.yaml>` | Execute selected test cases and write results. |
| `codex-skill-bench validate <suite.yaml>` | Validate suite and test case definitions without executing Codex. |
| `codex-skill-bench report <results-dir>` | Render or re-render HTML and aggregate YAML from existing results. |
| `codex-skill-bench list <suite.yaml>` | List cases, models, variants, and assertion counts. |
| `codex-skill-bench discover <suite.yaml>` | Discover `fixtures/<fixture-id>/` workspaces and case YAML files. |
| `codex-skill-bench clean <suite.yaml>` | Remove run workspaces and temporary files according to cleanup filters. |

## Request / Input

Common flags:

| Flag | Purpose |
| --- | --- |
| `--case <pattern>` | Filter test cases. |
| `--fixture <pattern>` | Filter workspace fixtures. |
| `--model <name>` | Filter or override models. |
| `--variant <name>` | Filter skill variants. |
| `--results <dir>` | Output directory. |
| `--codex-bin <path>` | Codex executable path. |
| `--deterministic-only` | Skip LLM-judged assertions. |
| `--parallel <n>` | Maximum concurrent Codex runs. |
| `--timeout <duration>` | Default run timeout. |
| `--cleanup <policy>` | Override cleanup policy for this invocation. |
| `--keep-runs` | Keep all run workspaces for debugging. Equivalent to `--cleanup never`. |

`init [skill-path]` input:

| Argument | Required | Purpose |
| --- | --- | --- |
| `skill-path` | no | Optional path to the skill under test. If omitted, `init` opens an interactive TUI wizard and asks for the skill path and suite defaults. |

`init` behavior:

- Create `suite.yaml` in the current directory when it does not already exist.
- Create `fixtures/`.
- Create `fixtures/README.md` with usage examples for `init`, `add-fixture`, `list`, and `run`, plus explanations of `suite.yaml` and `fixture.yaml`.
- If `skill-path` is supplied, configure a skill variant and a no-skill control variant.
- If `skill-path` is omitted, collect the missing values through a TUI wizard before writing files.

`add-fixture [name] [target-path] [prompt]` input:

| Argument | Required | Purpose |
| --- | --- | --- |
| `name` | no | Fixture directory name under `fixtures/`. |
| `target-path` | no | Directory to snapshot into `fixtures/<name>/workspace/`. |
| `prompt` | no | Prompt text to write into the generated test case. |

`add-fixture` behavior:

- If any required argument is omitted, open an interactive TUI wizard for missing values.
- Create `fixtures/<name>/workspace/` from the target directory snapshot.
- Create or update `fixtures/<name>/fixture.yaml`.
- Append a test case whose `prompt` field is the supplied prompt.
- When the target directory is the suite root, exclude `fixtures/` and project-local `.agent/skills/` and `.agents/skills/` directories from the snapshot.

## Response / Output

- Human-readable command progress on stderr.
- YAML and HTML artifacts under the configured results directory.
- Process exit code `0` when all required selected runs pass.
- Non-zero process exit code when validation fails, any required run fails, or runner errors occur.

## Errors

| Error | Meaning |
| --- | --- |
| Invalid suite | Suite or case YAML does not match required schema. |
| Fixture error | Workspace fixture cannot be materialized. |
| Codex error | Codex process cannot start or exits unexpectedly. |
| Assertion error | Evaluator cannot execute an assertion. |
| Report error | Result artifacts cannot be written or rendered. |
| Cleanup error | Run workspace cleanup could not complete. |

## Related Documents

- [Codex Skill Bench System](codex-skill-bench-system.md)
- [Suite Config Model](suite-config-model.md)
- [Test Case Model](test-case-model.md)
- [Workspace Fixture](workspace-scenario-set.md)
- [Report Generator](report-generator.md)
- [Security And Isolation Policy](security-and-isolation-policy.md)

## Native-Language Summary

Python製CLIとして、run、validate、report、list を提供し、case/model/variant/filter/結果出力先などをflagで指定できる。
