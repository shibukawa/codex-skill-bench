from __future__ import annotations

import argparse
from pathlib import Path

from .models import RunSpec
from .runner import BenchRunner
from .suite_loader import load_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codex-skill-bench")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run a benchmark suite")
    run_parser.add_argument("suite", type=Path)
    run_parser.add_argument("--results", type=Path, default=None)
    run_parser.add_argument("--model", default=None)
    run_parser.add_argument("--variant", default=None)
    run_parser.add_argument("--case", default=None)
    run_parser.add_argument("--fixture", default=None)

    list_parser = sub.add_parser("list", help="List resolved runs")
    list_parser.add_argument("suite", type=Path)

    args = parser.parse_args(argv)
    if args.command == "run":
        return run_suite(args)
    if args.command == "list":
        return list_suite(args)
    parser.error(f"unknown command: {args.command}")
    return 2


def run_suite(args: argparse.Namespace) -> int:
    suite, fixtures = load_suite(args.suite)
    specs = select_runs(suite, fixtures, args)
    results_dir = args.results or Path(suite.codex.get("resultsDir", "results"))
    runner = BenchRunner(results_dir)
    summary = runner.run(specs)
    print(f"wrote {results_dir / 'summary.yaml'}")
    print(f"runs: {sum(len(v['variants']) for f in summary['fixtures'].values() for c in f['cases'].values() for v in c['models'].values())}")
    return 0


def list_suite(args: argparse.Namespace) -> int:
    suite, fixtures = load_suite(args.suite)
    for spec in select_runs(suite, fixtures, args):
        print(spec.run_id)
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


if __name__ == "__main__":
    raise SystemExit(main())

