from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

import yaml

from .models import RunSpec
from .runner import BenchRunner
from .suite_loader import load_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="csb")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run a benchmark suite")
    _add_run_arguments(run_parser)

    eval_parser = sub.add_parser("eval", help="Evaluate a benchmark suite")
    _add_run_arguments(eval_parser)

    list_parser = sub.add_parser("list", help="List resolved runs")
    list_parser.add_argument("suite", type=Path)

    init_parser = sub.add_parser("init", help="Initialize a benchmark suite")
    init_parser.add_argument("skill_path", type=Path, nargs="?")

    fixture_parser = sub.add_parser("add-fixture", help="Create a fixture from a workspace snapshot")
    fixture_parser.add_argument("name", nargs="?")
    fixture_parser.add_argument("target_path", type=Path, nargs="?")
    fixture_parser.add_argument("prompt", nargs="?")

    args = parser.parse_args(argv)
    if args.command in {"run", "eval"}:
        return run_suite(args)
    if args.command == "list":
        return list_suite(args)
    if args.command == "init":
        return init_suite(args)
    if args.command == "add-fixture":
        return add_fixture(args)
    parser.error(f"unknown command: {args.command}")
    return 2


def eval_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval")
    _add_run_arguments(parser)
    return run_suite(parser.parse_args(argv))


def init_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="init")
    parser.add_argument("skill_path", type=Path, nargs="?")
    return init_suite(parser.parse_args(argv))


def add_fixture_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="add-fixture")
    parser.add_argument("name", nargs="?")
    parser.add_argument("target_path", type=Path, nargs="?")
    parser.add_argument("prompt", nargs="?")
    return add_fixture(parser.parse_args(argv))


def list_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="list")
    parser.add_argument("suite", type=Path)
    return list_suite(parser.parse_args(argv))


def run_suite(args: argparse.Namespace) -> int:
    suite, fixtures = load_suite(args.suite)
    specs = select_runs(suite, fixtures, args)
    results_dir = args.results or Path(suite.codex.get("resultsDir", "results"))
    runner = BenchRunner(results_dir)
    summary = runner.run(specs)
    print(f"wrote {results_dir / 'summary.yaml'}")
    print(f"runs: {sum(len(v['variants']) for f in summary['fixtures'].values() for c in f['cases'].values() for v in c['models'].values())}")
    return 0


def _add_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("suite", type=Path)
    parser.add_argument("--results", type=Path, default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--variant", default=None)
    parser.add_argument("--case", default=None)
    parser.add_argument("--fixture", default=None)


def list_suite(args: argparse.Namespace) -> int:
    suite, fixtures = load_suite(args.suite)
    for spec in select_runs(suite, fixtures, args):
        print(spec.run_id)
    return 0


def init_suite(args: argparse.Namespace) -> int:
    root = Path.cwd()
    skill_path = args.skill_path
    if skill_path is None:
        print("Codex Skill Bench init wizard")
        skill_text = input("Skill path (leave blank for no initial skill): ").strip()
        skill_path = Path(skill_text) if skill_text else None

    fixtures_root = root / "fixtures"
    fixtures_root.mkdir(exist_ok=True)
    readme = fixtures_root / "README.md"
    if not readme.exists():
        readme.write_text(_fixtures_readme(), encoding="utf-8")

    suite_path = root / "suite.yaml"
    if suite_path.exists():
        print(f"exists: {suite_path}")
        print(f"wrote {readme}")
        return 0

    suite: dict[str, Any] = {
        "version": 1,
        "name": root.name,
        "fixtures": {"root": "fixtures"},
        "models": ["default"],
        "variants": [{"name": "default", "kind": "control"}],
        "security": {"sandbox": "workspace-write", "network": False, "approval": "never"},
        "runner": {"parallel": 1},
    }
    if skill_path is not None:
        suite["skills"] = [{"path": _relative_or_absolute(skill_path, root)}]
        suite["variants"] = [
            {"name": "with-skill", "kind": "skill"},
            {"name": "no-skill", "kind": "control", "controlOf": "with-skill"},
        ]

    suite_path.write_text(yaml.safe_dump(suite, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"wrote {suite_path}")
    print(f"wrote {readme}")
    return 0


def add_fixture(args: argparse.Namespace) -> int:
    name = args.name
    target_path = args.target_path
    prompt = args.prompt
    if not (name and target_path and prompt):
        print("Codex Skill Bench add-fixture wizard")
        name = name or input("Fixture name: ").strip()
        target_text = str(target_path) if target_path else input("Target path to snapshot: ").strip()
        target_path = Path(target_text)
        prompt = prompt or input("Prompt: ").strip()

    if not name:
        raise SystemExit("fixture name is required")
    if target_path is None:
        raise SystemExit("target path is required")
    if not prompt:
        raise SystemExit("prompt is required")

    root = Path.cwd()
    source = target_path.resolve()
    fixture_dir = root / "fixtures" / name
    workspace = fixture_dir / "workspace"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    if workspace.exists():
        raise SystemExit(f"workspace already exists: {workspace}")

    shutil.copytree(source, workspace, ignore=_snapshot_ignore(source, root.resolve()))

    fixture_yaml = fixture_dir / "fixture.yaml"
    data = _load_yaml_dict(fixture_yaml) if fixture_yaml.exists() else {}
    cases = data.setdefault("cases", [])
    cases.append({"title": name.replace("-", " ").replace("_", " ").title(), "prompt": prompt})
    fixture_yaml.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"wrote {fixture_yaml}")
    print(f"wrote {workspace}")
    return 0


def select_runs(suite, fixtures, args) -> list[RunSpec]:
    specs: list[RunSpec] = []
    for fixture in fixtures:
        if getattr(args, "fixture", None) and args.fixture not in fixture.fixture_id:
            continue
        for case in fixture.cases:
            if getattr(args, "case", None) and args.case not in case.case_id:
                continue
            for model in suite.models:
                if getattr(args, "model", None) and args.model != model.name:
                    continue
                for variant in suite.variants:
                    if getattr(args, "variant", None) and args.variant != variant.name:
                        continue
                    specs.append(RunSpec(suite=suite, fixture=fixture, case=case, model=model, variant=variant))
    return specs


def _relative_or_absolute(path: Path, base: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return str(resolved.relative_to(base.resolve()))
    except ValueError:
        return str(resolved)


def _snapshot_ignore(source: Path, root: Path):
    if source != root:
        return None

    def ignore(directory: str, names: list[str]) -> set[str]:
        current = Path(directory).resolve()
        ignored: set[str] = set()
        if current == root:
            ignored.add("fixtures")
        if current == root / ".agent" or current == root / ".agents":
            ignored.add("skills")
        return ignored & set(names)

    return ignore


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _fixtures_readme() -> str:
    return """# Codex Skill Bench Fixtures

This directory contains reusable workspace snapshots for `eval` benchmark runs.

## Commands

Initialize a suite without installing the package:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git init [skill-path]
```

If `skill-path` is omitted, `init` starts an interactive wizard and creates `suite.yaml`, `fixtures/`, and this README.

Add a fixture from a workspace snapshot:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git add-fixture [name] [target-path] [prompt]
```

If arguments are omitted, `add-fixture` starts an interactive wizard. It creates `fixtures/<name>/workspace/` from the target path and appends a test case to `fixtures/<name>/fixture.yaml` with `prompt: <prompt>`.

Run or list the suite:

```bash
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git list suite.yaml
uvx --from git+https://github.com/shibukawa/codex-skill-bench.git eval suite.yaml --results results
```

## suite.yaml

`suite.yaml` is the root benchmark configuration. It defines the fixture root, skill paths, model matrix, skill/control variants, security settings, and runner settings. Relative paths are resolved from the directory containing `suite.yaml`.

Minimal skill comparison:

```yaml
version: 1
name: my skill suite
fixtures:
  root: fixtures
skills:
  - path: path/to/skill
models:
  - default
variants:
  - name: with-skill
    kind: skill
  - name: no-skill
    kind: control
    controlOf: with-skill
```

## fixture.yaml

Each fixture lives at `fixtures/<fixture-id>/` and contains:

```text
fixture.yaml
workspace/
```

`workspace/` is copied for each benchmark run. `fixture.yaml` stores the cases that reuse that snapshot:

```yaml
cases:
  - title: Update README
    prompt: |
      Update README.md with setup instructions.
```

When `add-fixture` snapshots the suite root, it excludes `fixtures/` and project-local `.agent/skills/` or `.agents/skills/` directories so generated benchmarks and local skills are not copied into the fixture workspace.
"""


if __name__ == "__main__":
    raise SystemExit(main())
