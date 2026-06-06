---
id: "security-and-isolation-policy"
type: "architectural-decision"
title: "Security And Isolation Policy"
aliases:
  - "runner isolation"
  - "security policy"
tags:
  - "security"
  - "isolation"
  - "codex"
facts:
  lifecycle.status: "accepted"
---

# Security And Isolation Policy

## Summary

The runner provides workspace-level isolation and artifact hygiene for local skill evaluation. It does not claim to provide a complete credential sandbox because Codex runs as the logged-in user and may access user-level credential stores unless the underlying Codex sandbox or operating system blocks access.

## Security Boundary

- Codex runs as the invoking logged-in user.
- The default runner inherits the user's logged-in `CODEX_HOME`.
- The runner does not copy authentication files into run workspaces.
- Fixture workspaces and skill variants are copied into isolated run directories.
- The runner relies on Codex sandbox settings and suite-level network/approval policy for command execution behavior.
- Environment filtering reduces accidental exposure but does not fully prevent access to credentials stored outside environment variables, such as files under `~/.aws`, keychains, credential helpers, or cloud CLI caches.

## Environment Variables

The default environment policy is `minimal`.

| Policy | Behavior |
| --- | --- |
| `minimal` | Pass a small baseline such as `PATH`, `SHELL`, `HOME`, `USER`, `TMPDIR`, `LANG`, and `TERM`, plus suite allowlist entries. |
| `inherit` | Inherit the parent process environment except explicit denylist patterns. Intended only for trusted local suites. |
| `empty` | Pass only variables required to start Codex and execute shell commands. |

The suite may define an allowlist and denylist:

```yaml
security:
  env:
    policy: minimal
    allow:
      - PATH
      - SHELL
      - HOME
      - USER
      - TMPDIR
      - LANG
      - TERM
      - GOFLAGS
    denyPatterns:
      - "*TOKEN*"
      - "*SECRET*"
      - "*PASSWORD*"
      - "AWS_*"
```

The runner must record the names of variables passed to Codex, but must not record secret-looking values in normal reports.

## Fixture Environment Files

The runner should load optional `.env.skill` files from the fixture tree before each run. These files are intended for skill-specific, test-specific environment variables such as feature flags, local test endpoints, or non-secret dummy credentials.

Load order:

1. `fixtures/.env.skill`, applied to every fixture under the fixture root.
2. `fixtures/<fixture-id>/.env.skill`, applied only to that fixture.

Fixture-specific values override common fixture-root values. Suite `security.env` policy is applied after merging `.env.skill` values. Deny patterns still suppress or redact matching names.

`.env.skill` format:

```dotenv
# comments are allowed
GOFLAGS=-count=1
LICENSE_HEADER_MODE=test
FAKE_API_TOKEN=fixture-token-for-redaction-tests
```

Rules:

- Empty lines and `#` comments are ignored.
- `KEY=value` syntax is required.
- Quoted values may be supported, but shell expansion must not be performed.
- Values from `.env.skill` are allowed even when `env.policy` is `minimal`, unless denied by `denyPatterns`.
- `.env.skill` files must not be copied into result artifacts by default.
- `.env.skill` is not a secure secret store. It is suitable for test values and redaction tests, not real credentials.

Redaction can be tested with `.env.skill` by using fake secret-looking values and asserting they do not appear in rendered reports.

## Network And Approval Policy

Network and command approval are suite-level policy because they are properties of the evaluated skill and its expected operating mode, not per-attempt choices.

```yaml
security:
  network: false
  approval: never
```

`network: false` should configure Codex and the runner environment to avoid network access where supported. For `workspace-write`, the runner should set `sandbox_workspace_write.network_access=false` in SDK config when supported; `network: true` should set `sandbox_workspace_write.network_access=true`.

`approval` maps to the SDK approval policy field. The runner should record the resolved policy in every run result.

Approval policy is not a complete security boundary. In local probes on 2026-06-01, both `-a never` and `-a untrusted` allowed simple trusted commands such as `pwd`, and both allowed creating a file inside the `workspace-write` run workspace. Therefore the benchmark should treat approval mode as Codex execution policy metadata and a possible behavior variable, not as a guarantee that every shell command is blocked.

Network policy is observable through command events. In local probes on 2026-06-01, `sandbox_workspace_write.network_access=false` caused `curl -I https://example.com` to fail with exit code `6` and a DNS resolution error, while `sandbox_workspace_write.network_access=true` allowed the same command to return `HTTP/2 200`. Tests that depend on network denial should assert normalized command failure or assistant response evidence rather than assuming a specific OS error string.

## Artifact Redaction

Artifact redaction is best-effort hygiene, not a security boundary. The runner should redact known secret-looking values from report previews and HTML. Raw artifacts may be retained for debugging according to cleanup and retention policy.

Recommended redaction targets:

- environment variable values whose names match deny patterns,
- access-token-like strings,
- API-key-like strings,
- private key blocks,
- long bearer-token-like strings.

Redaction behavior itself is testable with ordinary cases by expecting or forbidding text in generated reports and artifacts. For example, a fixture can intentionally echo a fake token and assert that `report.html` does not contain it while raw stderr retention follows the configured artifact policy.

## Cleanup Policy

The default cleanup policy is `on_pass`, meaning successful run workspaces may be removed and failed or errored run workspaces are preserved for debugging.

| Policy | Behavior |
| --- | --- |
| `always` | Remove run workspaces after artifacts are captured. |
| `on_pass` | Remove successful run workspaces and keep failed, errored, or flaky run workspaces. |
| `never` | Keep all run workspaces. |

The runner must never clean source fixtures or source skill variants.

## Related Documents

- [Suite Config Model](suite-config-model.md)
- [Codex Runner](codex-runner.md)
- [Report Generator](report-generator.md)
- [Project Local Skill Materialization Policy](project-local-skill-materialization-policy.md)

## Native-Language Summary

実行はログインユーザー権限で行うため完全なcredential隔離は保証しない。MVPでは最小env、suite単位のnetwork/approval、artifact redaction、成功時削除・失敗時保持のcleanup policyで運用する。
