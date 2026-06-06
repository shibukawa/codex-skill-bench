# Backlinks

## Artifact Usage Evaluation Policy (artifact-usage-evaluation-policy)

- relates_to from Deterministic And LLM Assertion Policy
- relates_to from Suite Config Model

## Assertion Engine (assertion-engine)

- relates_to from Artifact Usage Evaluation Policy
- links_to from Codex Runner
- uses_component from Codex Skill Bench System
- relates_to from Deterministic And LLM Assertion Policy
- relates_to from Event Log Model
- links_to from Report Generator
- depends_on from Report Generator
- relates_to from Test Case Model
- relates_to from Test Definition Format

## CLI Interface (cli-interface)

- relates_to from Python Implementation Policy

## Codex Runner (codex-runner)

- reads from Assertion Engine
- uses_component from Codex Skill Bench System
- relates_to from Comparison Matrix
- relates_to from Project Local Skill Materialization Policy
- relates_to from Python Implementation Policy
- relates_to from Security And Isolation Policy
- relates_to from Suite Config Model
- relates_to from Workspace Fixture

## Codex Skill Bench System (codex-skill-bench-system)

- relates_to from Assertion Engine
- relates_to from CLI Interface
- relates_to from Codex Runner
- relates_to from Comparison Matrix
- relates_to from Python Implementation Policy
- relates_to from Report Generator
- relates_to from Test Case Model

## Comparison Matrix (comparison-matrix)

- links_to from Codex Runner
- reads from Codex Runner
- uses_component from Codex Skill Bench System
- relates_to from Project Local Skill Materialization Policy
- depends_on from Report Generator
- relates_to from Suite Config Model
- relates_to from Test Case Model

## Deterministic And LLM Assertion Policy (deterministic-and-llm-assertion-policy)

- depends_on from Assertion Engine
- constrained_by from Codex Skill Bench System
- relates_to from Suite Config Model

## Event Log Model (event-log-model)

- depends_on from Assertion Engine
- depends_on from Codex Runner
- writes from Codex Runner
- uses_component from Codex Skill Bench System
- relates_to from Test Definition Format

## Project Local Skill Materialization Policy (project-local-skill-materialization-policy)

- reads from Codex Runner
- constrained_by from Codex Skill Bench System
- relates_to from Comparison Matrix
- relates_to from Security And Isolation Policy
- relates_to from Suite Config Model

## Python Implementation Policy (python-implementation-policy)

- constrained_by from Codex Skill Bench System
- relates_to from Suite Config Model

## Report Generator (report-generator)

- relates_to from Artifact Usage Evaluation Policy
- writes from Assertion Engine
- relates_to from CLI Interface
- links_to from Codex Runner
- writes from Codex Runner
- uses_component from Codex Skill Bench System
- relates_to from Comparison Matrix
- relates_to from Deterministic And LLM Assertion Policy
- relates_to from Event Log Model
- relates_to from Retry And Stability Policy
- relates_to from Security And Isolation Policy
- relates_to from Workspace Fixture

## Retry And Stability Policy (retry-and-stability-policy)

- relates_to from Report Generator
- links_to from Suite Config Model
- relates_to from Suite Config Model
- relates_to from Test Definition Format

## Security And Isolation Policy (security-and-isolation-policy)

- relates_to from CLI Interface
- links_to from Codex Runner
- links_to from Codex Runner
- reads from Codex Runner
- relates_to from Report Generator
- relates_to from Suite Config Model
- relates_to from Workspace Fixture

## Run Identity (run-identity)

- uses_common_detail from Test Case Model

## Suite Config Model (suite-config-model)

- relates_to from Artifact Usage Evaluation Policy
- relates_to from CLI Interface
- uses_component from Codex Skill Bench System
- relates_to from Comparison Matrix
- relates_to from Project Local Skill Materialization Policy
- relates_to from Report Generator
- relates_to from Retry And Stability Policy
- relates_to from Security And Isolation Policy
- relates_to from Test Case Model
- links_to from Test Definition Format
- relates_to from Test Definition Format

## Test Case Model (test-case-model)

- links_to from Assertion Engine
- reads from Assertion Engine
- relates_to from CLI Interface
- links_to from Codex Runner
- reads from Codex Runner
- uses_component from Codex Skill Bench System
- links_to from Comparison Matrix
- relates_to from Suite Config Model
- relates_to from Test Definition Format
- links_to from Workspace Fixture
- relates_to from Workspace Fixture

## Test Definition Format (test-definition-format)

- relates_to from Artifact Usage Evaluation Policy
- depends_on from Assertion Engine
- relates_to from Retry And Stability Policy
- relates_to from Suite Config Model
- links_to from Test Case Model
- relates_to from Test Case Model
- relates_to from Workspace Fixture

## Workspace Fixture (workspace-scenario-set)

- relates_to from CLI Interface
- links_to from Codex Runner
- links_to from Codex Runner
- reads from Codex Runner
- uses_component from Codex Skill Bench System
- links_to from Comparison Matrix
- relates_to from Comparison Matrix
- relates_to from Report Generator
- relates_to from Suite Config Model
- links_to from Test Case Model
- links_to from Test Case Model
- links_to from Test Case Model
- relates_to from Test Case Model
- links_to from Test Definition Format
- relates_to from Test Definition Format
