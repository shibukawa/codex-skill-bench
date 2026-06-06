# Project Backlog

## Items

- id: BLG-20260530120250-01
  state: backlog
  type: validation
  title: Confirm current codex exec JSON event schema
  docs:
    - specs/event-log-model.md
    - specs/codex-runner.md
  sources: []
  acceptance: Capture sample `codex exec --json` logs and map raw event shapes to the normalized event model.
  blockers: []
  updated: 2026-05-30

- id: BLG-20260530120250-02
  state: backlog
  type: documentation
  title: Define concrete suite YAML schema and examples
  docs:
    - specs/test-case-model.md
    - specs/cli-interface.md
  sources: []
  acceptance: Add a complete suite YAML example covering fixtures, prompts, models, variants, deterministic assertions, and LLM assertions.
  blockers: []
  updated: 2026-05-30

- id: BLG-20260530120250-03
  state: backlog
  type: decision
  title: Choose LLM judge provider and structured output contract
  docs:
    - specs/assertion-engine.md
    - specs/deterministic-and-llm-assertion-policy.md
  sources: []
  acceptance: Document judge model configuration, JSON response schema, retry policy, and how judge artifacts are stored.
  blockers: []
  updated: 2026-05-30

- id: BLG-20260530120250-04
  state: backlog
  type: decision
  title: Define skill variant materialization format
  docs:
    - specs/comparison-matrix.md
    - specs/codex-runner.md
  sources: []
  acceptance: Specify how variant directories are copied into `CODEX_HOME` and how skill names or paths are exposed to prompts.
  blockers: []
  updated: 2026-05-30
