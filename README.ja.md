# Codex Skill Bench

Codex Skill Bench は、Codex skill をワークスペースfixture単位で比較実行するためのベンチマークツールです。fixtureのワークスペースをコピーし、必要ならskillをそのコピー内に配置し、Codexを実行し、JSONイベントログからtoken使用量と実行時間を集計してYAMLレポートを出力します。

現在はMVP実装です。複数モデルや複数variantの定義はできますが、最初の用途としては1モデルで `with-skill` と `no-skill` を比較する想定です。

## 必要なもの

- Python 3.11+
- `uv`
- 実Codexを動かす場合は、利用可能なCodexログイン

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

モデル名に `default` を指定すると、SDKの `model` 引数を渡さず、Codex側の既定モデルを使います。

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

主なフィールド:

- `fixtures.root`: suiteファイルから見たfixtureディレクトリ。
- `fixtures.exclude`: 除外するfixture idのglob deny-list。
- `fixtures.caseGlob`: 各fixture内でcase YAMLを探すglob。デフォルトは `cases/*.yaml`。
- `skills`: 明示的なsource skillディレクトリ。文字列、または `{name, path, materializeAs}` objectを指定できます。
- `models`: モデル名の文字列配列。
- `variants`: 実行variant一覧。`kind: skill` はskillを配置し、`kind: control` は配置しません。
- `variants[].skill`: root `skills` の中から配置するskill名。
- `variants[].materializeAs`: `.agents/skills` 配下に作るskillディレクトリ名。
- `variants[].controlOf`: 比較対象のskill variant名。
- `security.sandbox`: Codex SDKのthread/turn実行に渡すsandbox。
- `security.approval`: Codex SDK approval modeに変換されます。デフォルトは `never`。

Codex実行はPython Codex SDKを使います。`codex` objectと `skillRoot` はsuite schemaには含めません。

`runner.parallel` は設定として保持していますが、現時点のMVPでは逐次実行します。

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
3. `kind: skill` の場合、選択されたroot `skills` entryを `<workspace>/.agents/skills/<materializeAs-or-skill-name>` にコピー。
4. 現在のvariant向けのpromptを解決。
5. skill variantでは、まず別threadでpreloadを実行します。この強制preloadはskill読み込みのコストとコンテキスト量を測るためだけのもので、本番のベンチマークturnには再利用しません。
6. 実際のベンチマークturnを実行。

   runnerは `openai_codex.Codex` を使い、runワークスペースを `cwd` にした一時threadを作成して `thread.run(...)` を呼びます。本番のベンチマークpromptは通常のテキストとして渡し、`SkillInput` で強制起動しません。これにより、promptがskillを正しく起動できるかも検証対象になります。

7. Codex JSONイベントストリーム、またはSDK result要約を `events.jsonl` に保存。
8. stderrを `stderr.log` に保存。
9. `turn.completed.usage` イベントを読み取り、token使用量を集計。
10. skill variantの本番turnで `.agents/skills/<skill>/...` のような配置済みskillパスがSDKイベント内に出なければ、skill未起動としてエラーにします。
11. run単位のresult YAMLと、全体の `summary.yaml` を出力。

## 出力

各runには次が保存されます。

- `workspace`: Codex実行後のコピー済みワークスペース。
- `events.jsonl`: Codexの生JSONイベント。
- `final.md`: `--output-last-message` で保存された最終応答。
- `stderr.log`: Codex stderrまたはrunnerエラー。
- `preload.events.jsonl`, `preload.final.md`, `preload.stderr.log`: SDK skill variantのpreload成果物。
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
    generationEstimatedRepeatDurationDeltaMs: -3000
```

`generationTokenDelta` は `control.totalTokens - skill.totalTokens` です。
`generationDurationDeltaMs` は `control.durationMs - skill.durationMs` です。
`generationEstimatedRepeatDurationDeltaMs` は `control.durationMs - skill.estimatedRepeatDurationMs` です。

値が正なら、skill variantの方がtokenまたは時間を節約したという意味です。

skill variantでは、各runに次も出力されます。

- `preload.durationMs`: 別threadで強制skill loadした時間。
- `preload.usage`: 強制skill loadのtoken使用量。
- `estimatedRepeatDurationMs`: `durationMs - preload.durationMs` を0以上に丸めた値。preloadコストを差し引いた繰り返し実行時の概算時間です。

## 現在の制限

- 保存するイベントはCLIの生JSONストリームではなく、SDK resultを正規化したイベントです。
- assertion、LLM judge、コマンド実行evaluation、retry、parallel実行、HTMLレポート、成果物diffはまだ未実装です。
- token使用量はCodex JSONイベントに `turn.completed.usage` が出ることに依存します。timeoutしたrunでは、そのイベントが出る前だとtoken使用量が0になることがあります。
