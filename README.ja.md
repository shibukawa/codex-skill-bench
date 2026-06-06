# Codex Skill Bench

Codex Skill Bench は、Codex skill をワークスペースfixture単位で比較実行するためのベンチマークツールです。fixtureのワークスペースをコピーし、必要ならskillをそのコピー内に配置し、Codexを実行し、JSONイベントログからtoken使用量と実行時間を集計してYAMLレポートを出力します。

現在はMVP実装です。複数モデルや複数variantの定義はできますが、最初の用途としては1モデルで `with-skill` と `no-skill` を比較する想定です。

## 必要なもの

- Python 3.11+
- `uv`
- 実Codexを動かす場合は、ログイン済みで利用可能な `codex` CLI

`uv` 経由で実行します。

```bash
uv run codex-skill-bench list examples/basic-suite/suite.yaml
uv run codex-skill-bench run examples/basic-suite/suite.yaml --results results/basic-suite-real
```

テスト:

```bash
uv run pytest -q
```

## CLI

Codexを実行せず、展開されるrunだけを表示します。

```bash
uv run codex-skill-bench list <suite.yaml>
```

suiteを実行します。

```bash
uv run codex-skill-bench run <suite.yaml> [options]
```

オプション:

- `--results <dir>`: 出力先ディレクトリ。デフォルトは `results`。
- `--model <name>`: 指定モデル名だけを実行。
- `--variant <name>`: 指定variantだけを実行。
- `--fixture <text>`: idに指定文字列を含むfixtureだけを実行。
- `--case <text>`: idに指定文字列を含むcaseだけを実行。

モデル名に `default` を指定すると、Codex CLI呼び出し時に `--model` を渡しません。ログイン済みCodex CLI側の既定モデルを使いたい場合に使います。

## Fixture構成

suiteは `fixtures` のルートを指します。各fixtureは、ワークスペースと1つ以上のcase YAMLを持つディレクトリです。

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

runnerは各runの前に `workspace/` をコピーします。元のfixtureワークスペースは変更されません。

## Suite設定

例:

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

主なフィールド:

- `fixtures.root`: suiteファイルから見たfixtureディレクトリ。
- `fixtures.include`: 実行対象fixture idのallow-list。
- `fixtures.exclude`: 除外するfixture idのdeny-list。
- `fixtures.caseGlob`: 各fixture内でcase YAMLを探すglob。デフォルトは `cases/*.yaml`。
- `models`: モデル一覧。文字列または `{name: ...}` を指定できます。
- `variants`: 実行variant一覧。`kind: skill` はskillを配置し、`kind: control` は配置しません。
- `variants[].skillPath`: skill variantでコピーするskillディレクトリ。
- `variants[].materializeAs`: `codex.skillRoot` 配下に作るskillディレクトリ名。
- `variants[].controlOf`: 比較対象のskill variant名。
- `codex.bin`: Codex CLI実行ファイル。デフォルトは `codex`。
- `codex.sandbox`: `codex exec --sandbox` に渡す値。
- `codex.skillRoot`: runワークスペース内でskillを配置する場所。デフォルトは `.agents/skills`。
- `security.approval`: `codex -a` に渡す値。デフォルトは `never`。
- `security.network`: `sandbox_workspace_write.network_access=true|false` として渡します。

`codex.backend` と `runner.parallel` は設定として保持していますが、現時点のMVPではCLI backendを逐次実行します。

## Fixture設定

`fixture.yaml`:

```yaml
id: simple-python
title: Simple Python fixture
workspace:
  path: workspace
```

フィールド:

- `id`: run idやレポートで使うfixture id。
- `workspace.path`: 各runでコピーするワークスペースディレクトリ。デフォルトは `workspace`。

## Case設定

例:

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

プロンプトの解決順:

1. `promptByVariant[variantName]`
2. `promptByVariantKind[variantKind]`
3. `prompt`
4. `promptFile`

`timeout` は秒数の整数、または `ms`、`s`、`m` で終わる文字列を指定できます。

## 内部の挙動

選択されたfixture、case、model、variantごとに、runnerは次を行います。

1. `results/runs/<run-id>/` を作成。
2. fixtureのワークスペースを `results/runs/<run-id>/workspace` にコピー。
3. `kind: skill` の場合、`skillPath` を `<workspace>/<codex.skillRoot>/<materializeAs>` にコピー。
4. 現在のvariant向けのpromptを解決。
5. 次の形でCodexを実行。

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

6. Codex JSONイベントストリームを `events.jsonl` に保存。
7. stderrを `stderr.log` に保存。
8. `turn.completed.usage` イベントを読み取り、token使用量を集計。
9. run単位のresult YAMLと、全体の `summary.yaml` を出力。

## 出力

各runには次が保存されます。

- `workspace`: Codex実行後のコピー済みワークスペース。
- `events.jsonl`: Codexの生JSONイベント。
- `final.md`: `--output-last-message` で保存された最終応答。
- `stderr.log`: Codex stderrまたはrunnerエラー。
- `<run-id>.result.yaml`: run単位のレポート。

集約された `summary.yaml` は次の階層です。

```text
fixtures -> cases -> models -> variants -> attempts
```

skill/controlペアの比較は `comparisons` に出ます。

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

`generationTokenDelta` は `control.totalTokens - skill.totalTokens` です。
`generationDurationDeltaMs` は `control.durationMs - skill.durationMs` です。

値が正なら、skill variantの方がtokenまたは時間を節約したという意味です。

## 現在の制限

- 現在のrunnerはPython Codex SDK backendではなく、Codex CLI互換経路で実行します。
- assertion、LLM judge、コマンド実行evaluation、retry、parallel実行、HTMLレポート、成果物diffはまだ未実装です。
- token使用量はCodex JSONイベントに `turn.completed.usage` が出ることに依存します。timeoutしたrunでは、そのイベントが出る前だとtoken使用量が0になることがあります。
