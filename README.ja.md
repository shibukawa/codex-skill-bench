# Codex Skill Bench

Codex Skill Bench は、Codex skill をワークスペースfixture単位で比較実行するためのベンチマークツールです。fixtureのワークスペースをコピーし、必要ならskillをそのコピー内に配置し、Codexを実行し、JSONイベントログからtoken使用量と実行時間を集計してYAMLレポートを出力します。

現在はMVP実装です。複数モデルや複数variantの定義はできますが、最初の用途としては1モデルで `with-skill` と `no-skill` を比較する想定です。

## 必要なもの

- Python 3.11+
- `uv`
- 実Codexを動かす場合は、利用可能なCodexログイン

インストールせずに実行します。

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git list examples/basic-suite/suite.yaml
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git eval examples/basic-suite/suite.yaml --results results/basic-suite-real
```

テスト:

```bash
uv run pytest -q
```

## CLI

現在のディレクトリでsuiteを初期化します。

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git init [skill-path]
```

`skill-path` を省略すると、`init` は対話ウィザードを開始します。`suite.yaml`、`fixtures/`、`fixtures/README.md`、および同梱の `agents/` と `references/` を含む `.agents/skills/codex-skill-bench/` を作成します。

既存ワークスペースのスナップショットからfixtureを追加します。

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git add-fixture [name] [target-path] [prompt]
```

引数を省略すると、`add-fixture` は対話ウィザードを開始します。`target-path` をコピーして `fixtures/<name>/workspace/` を作成し、`prompt: <prompt>` のtest caseを `fixtures/<name>/fixture.yaml` に追加します。

`target-path` がsuite rootの場合、スナップショット作成時に `fixtures/` と project-local の `.agent/skills/` または `.agents/skills/` は除外されます。

Codexを実行せず、展開されるrunだけを表示します。

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git list <suite.yaml>
```

suiteを評価実行します。

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git eval <suite.yaml> [options]
```

カレントディレクトリに `suite.yaml` がある場合、`list`、`eval`、`csb list`、`csb eval`、`csb run` ではsuiteパスを省略できます。

まとめCLI entrypointを使う場合は、`csb run` を `eval` のaliasとして利用できます。

オプション:

- `--results <dir>`: 出力先ディレクトリ。デフォルトは `results`。
- `--model <name>`: 指定モデル名だけを実行。
- `--variant <name>`: 指定variantだけを実行。
- `--fixture <text>`: idに指定文字列を含むfixtureだけを実行。
- `--case <text>`: idに指定文字列を含むcaseだけを実行。

モデル名に `default` を指定すると、SDKの `model` 引数を渡さず、Codex側の既定モデルを使います。

## Fixture構成

suiteは `fixtures` のルートを指します。各fixtureは、固定の `workspace/` と、case一覧を含む `fixture.yaml` を持つディレクトリです。

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

fixtureディレクトリ名がfixture idおよびtitleになります。runnerは各runの前に `workspace/` をコピーします。元のfixtureワークスペースは変更されません。`fixtures/README.md` はローカルsuiteのコマンドと `suite.yaml` / `fixture.yaml` の説明を含みます。`init` は project-local helper skill も `.agents/skills/codex-skill-bench/` にインストールします。

## Suite設定

例:

```yaml
version: 1
name: basic license header comparison

fixtures:
  root: fixtures

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

report:
  resultsDir: results
```

主なフィールド:

- `fixtures.root`: suiteファイルから見たfixtureディレクトリ。
- `fixtures.exclude`: 除外するfixture idのglob deny-list。
- `skills`: 明示的なsource skillディレクトリ。文字列、または `{name, path, materializeAs}` objectを指定できます。
- `models`: モデル名の文字列配列。
- `variants`: 実行variant一覧。`kind: skill` はskillを配置し、`kind: control` は配置しません。
- `variants[].skill`: root `skills` の中から配置するskill名。
- `variants[].materializeAs`: `.agents/skills` 配下に作るskillディレクトリ名。
- `variants[].controlOf`: 比較対象のskill variant名。
- `security.sandbox`: Codex SDKのthread/turn実行に渡すsandbox。
- `security.approval`: Codex SDK approval modeに変換されます。デフォルトは `never`。
- `report.resultsDir`: `--results` 省略時の既定出力先ディレクトリ。

Codex実行はPython Codex SDKを使います。`codex` objectと `skillRoot` はsuite schemaには含めません。

`runner.parallel` は設定として保持していますが、現時点のMVPでは逐次実行します。

## Fixture設定

`fixture.yaml`:

```yaml
cases:
  - title: Add license header
    prompt: |
      Add an MIT license header to src/sample.py.
```

フィールド:

- `cases`: このfixtureで実行するcase定義のリスト。

fixture idとtitleはfixtureディレクトリ名です。ワークスペースディレクトリは常に `workspace/` です。

## Case設定

各 `cases[]` itemはcase schemaです。例:

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

プロンプトの解決順:

1. `promptVariants[variantName]`
2. control variantでは `promptVariants["no-skill"]`
3. skill variantでは一致する `promptVariants["specific-skill[<skill-name>]"]`
4. skill variantでは `promptVariants["skill"]`
5. `prompt`
6. `promptFile`

`prompt` と `promptVariants` は排他です。文字列の `prompt` は、同じ内容の `skill` / `no-skill` promptとして正規化されます。

skill variantでは `$skill` が `$license-header` のような解決済みskill参照に置換されます。解決後のpromptがそのskill参照を含まない場合でも、runnerが選択skillを使う短い指示を先頭に補い、materialized skillが起動対象になるようにします。

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

## ライセンス

このプロジェクトは GNU Affero General Public License v3.0 or later でライセンスされます。詳細は [LICENSE](LICENSE) を参照してください。
