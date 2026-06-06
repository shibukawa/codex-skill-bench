---
name: codex-skill-bench
description: Run, inspect, and author Codex Skill Bench suites for evaluating Codex skills against workspace fixtures. Use when Codex needs to initialize a benchmark suite, add fixtures, edit suite.yaml or fixture.yaml, compare skill and no-skill variants, interpret results/summary.yaml, debug benchmark runs, or explain the supported Codex Skill Bench YAML formats without relying on repository-local specs.
---

# Codex Skill Bench

Use this skill to operate Codex Skill Bench from a user workspace. Treat the bundled references as the portable source of truth because most users will not have this repository's `specs/` directory.

## Quick Workflow

1. Locate the suite root: look for `suite.yaml`; fixtures normally live under `fixtures/`.
2. If no suite exists, initialize one:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git init [skill-path]
```

3. Add or inspect fixtures. A fixture is `fixtures/<fixture-id>/fixture.yaml` plus `fixtures/<fixture-id>/workspace/`.
4. List resolved runs before spending model time:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git list suite.yaml
```

5. Run a narrow eval first, then broaden:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git eval suite.yaml --results results --fixture <id-substring> --case <id-substring>
```

6. Inspect `results/summary.yaml`, then per-run artifacts under `results/runs/<run-id>/`.

## Adding Fixtures

Prefer the CLI when snapshotting an existing workspace:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git add-fixture <name> <target-path> "<prompt>"
```

When `target-path` is the suite root, snapshotting excludes generated `fixtures/` and project-local `.agent/skills/` or `.agents/skills/`.

For hand-authored fixtures:

- Create `fixtures/<fixture-id>/workspace/` with the initial project state.
- Write `fixtures/<fixture-id>/fixture.yaml` with a `cases:` list.
- Keep cases independent; each case/model/variant run receives a fresh workspace copy.
- Use `promptVariants` when skill and control prompts should differ.

Read `references/format.md` before editing `suite.yaml` or `fixture.yaml`.

## Running And Debugging

Use these commands from the suite root or pass an explicit suite path:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git list suite.yaml
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git eval suite.yaml --results results
uv run pytest -q
```

If the package is installed locally, the console scripts are `csb`, `eval`, `init`, `add-fixture`, and `list`. `csb run` is an alias for `eval`.

For debugging:

- Run `list` first to confirm fixture/case/model/variant expansion.
- Use `--fixture`, `--case`, `--model`, and `--variant` to isolate one run.
- Check `stderr.log` for SDK or runner errors.
- Check `events.jsonl` and `final.md` for what Codex did.
- For skill variants, check `preload.*` artifacts separately from the benchmark turn.

Read `references/results.md` when interpreting output artifacts, token deltas, preload costs, or activation failures.

## Current Implementation Boundaries

Distinguish current MVP behavior from planned schema fields:

- Implemented: `init`, `add-fixture`, `list`, `eval`, fixture workspace copy, project-local skill materialization under `.agents/skills`, prompt variant resolution, skill preload measurement, raw SDK result capture, per-run YAML, aggregate `summary.yaml`, and skill/control token and duration deltas.
- Not implemented yet: deterministic assertions, multi-step cases, retries, parallel execution, HTML reports, command judges, LLM judges, artifact-usage evaluation, file diff assertions, and most advanced suite fields.

When authoring portable user guidance, prefer implemented fields unless the user is explicitly designing future benchmark schema.
