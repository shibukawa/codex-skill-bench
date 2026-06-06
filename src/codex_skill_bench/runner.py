from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import RunSpec, VariantConfig
from .suite_loader import resolve_prompt


@dataclass
class RunResult:
    run_id: str
    fixture_id: str
    case_id: str
    model: str
    variant: str
    variant_kind: str
    status: str
    duration_ms: int
    usage: dict[str, int]
    artifacts: dict[str, str]
    exit_code: int | None = None
    error: str | None = None


class BenchRunner:
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir.resolve()
        self.runs_dir = self.results_dir / "runs"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def run(self, specs: list[RunSpec]) -> dict[str, Any]:
        results = [self.run_one(spec) for spec in specs]
        summary = build_summary(results)
        summary_path = self.results_dir / "summary.yaml"
        with summary_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(summary, f, sort_keys=False, allow_unicode=True)
        return summary

    def run_one(self, spec: RunSpec) -> RunResult:
        run_root = self.runs_dir / spec.run_id
        workspace = run_root / "workspace"
        if run_root.exists():
            shutil.rmtree(run_root)
        run_root.mkdir(parents=True)
        shutil.copytree(spec.fixture.workspace, workspace)

        materialized = self._materialize_variant(spec.variant, workspace, spec.suite.codex.get("skillRoot", ".agents/skills"))
        prompt = resolve_prompt(spec.case, spec.variant)

        events_path = run_root / "events.jsonl"
        final_path = run_root / "final.md"
        stderr_path = run_root / "stderr.log"
        result_path = self.results_dir / f"{spec.run_id}.result.yaml"

        started = time.monotonic()
        exit_code: int | None = None
        error: str | None = None
        try:
            exit_code = self._run_codex(spec, workspace, prompt, events_path, final_path, stderr_path)
            status = "passed" if exit_code == 0 else "errored"
        except Exception as exc:  # keep per-run artifacts even on runner errors
            status = "errored"
            error = str(exc)
            stderr_path.write_text(str(exc), encoding="utf-8")
        duration_ms = int((time.monotonic() - started) * 1000)
        usage = read_usage(events_path)

        result = RunResult(
            run_id=spec.run_id,
            fixture_id=spec.fixture.fixture_id,
            case_id=spec.case.case_id,
            model=spec.model.name,
            variant=spec.variant.name,
            variant_kind=spec.variant.kind,
            status=status,
            duration_ms=duration_ms,
            usage=usage,
            exit_code=exit_code,
            error=error,
            artifacts={
                "runRoot": str(run_root),
                "workspace": str(workspace),
                "events": str(events_path),
                "final": str(final_path),
                "stderr": str(stderr_path),
                "result": str(result_path),
                "materializedSkill": str(materialized) if materialized else "",
            },
        )
        write_result(result_path, result)
        return result

    def _materialize_variant(self, variant: VariantConfig, workspace: Path, skill_root: str) -> Path | None:
        if variant.kind == "control":
            return None
        if variant.skill_path is None:
            raise ValueError(f"skill variant {variant.name} requires skillPath")
        target_name = variant.materialize_as or variant.skill_path.name
        target = workspace / skill_root / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(variant.skill_path, target)
        return target

    def _run_codex(
        self,
        spec: RunSpec,
        workspace: Path,
        prompt: str,
        events_path: Path,
        final_path: Path,
        stderr_path: Path,
    ) -> int:
        codex_bin = str(spec.suite.codex.get("bin", "codex"))
        sandbox = str(spec.suite.codex.get("sandbox", "workspace-write"))
        approval = str(spec.suite.security.get("approval", "never"))
        network = str(bool(spec.suite.security.get("network", False))).lower()
        timeout = spec.case.timeout_seconds or 600
        cmd = [
            codex_bin,
            "-a",
            approval,
            "-c",
            f"sandbox_workspace_write.network_access={network}",
            "exec",
            "--json",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            sandbox,
        ]
        if spec.model.name != "default":
            cmd.extend(["--model", spec.model.name])
        cmd.extend(
            [
                "--cd",
                str(workspace),
                "--output-last-message",
                str(final_path),
                prompt,
            ]
        )
        with events_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
            completed = subprocess.run(cmd, stdout=stdout, stderr=stderr, cwd=workspace, timeout=timeout)
        return completed.returncode


def read_usage(events_path: Path) -> dict[str, int]:
    total = {
        "inputTokens": 0,
        "cachedInputTokens": 0,
        "outputTokens": 0,
        "reasoningOutputTokens": 0,
        "totalTokens": 0,
    }
    if not events_path.exists():
        return total
    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            usage = event.get("usage")
            if not isinstance(usage, dict):
                continue
            total["inputTokens"] += int(usage.get("input_tokens", 0) or 0)
            total["cachedInputTokens"] += int(usage.get("cached_input_tokens", 0) or 0)
            total["outputTokens"] += int(usage.get("output_tokens", 0) or 0)
            total["reasoningOutputTokens"] += int(usage.get("reasoning_output_tokens", 0) or 0)
    total["totalTokens"] = total["inputTokens"] + total["outputTokens"]
    return total


def write_result(path: Path, result: RunResult) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"run": result_to_dict(result)}, f, sort_keys=False, allow_unicode=True)


def result_to_dict(result: RunResult) -> dict[str, Any]:
    return {
        "id": result.run_id,
        "fixture": result.fixture_id,
        "case": result.case_id,
        "model": result.model,
        "variant": result.variant,
        "variantKind": result.variant_kind,
        "status": result.status,
        "durationMs": result.duration_ms,
        "exitCode": result.exit_code,
        "usage": result.usage,
        "artifacts": result.artifacts,
        "error": result.error,
    }


def build_summary(results: list[RunResult]) -> dict[str, Any]:
    summary: dict[str, Any] = {"fixtures": {}, "comparisons": []}
    for result in results:
        fixture = summary["fixtures"].setdefault(result.fixture_id, {"cases": {}})
        case = fixture["cases"].setdefault(result.case_id, {"models": {}})
        model = case["models"].setdefault(result.model, {"variants": {}})
        model["variants"][result.variant] = {
            "variantKind": result.variant_kind,
            "attempts": [result_to_dict(result)],
            "aggregate": {
                "status": result.status,
                "durationMs": result.duration_ms,
                "usage": result.usage,
            },
        }

    grouped: dict[tuple[str, str, str], dict[str, RunResult]] = {}
    for result in results:
        key = (result.fixture_id, result.case_id, result.model)
        grouped.setdefault(key, {})[result.variant] = result
    for (fixture_id, case_id, model), variants in grouped.items():
        skill_results = [r for r in variants.values() if r.variant_kind == "skill"]
        control_results = [r for r in variants.values() if r.variant_kind == "control"]
        for skill in skill_results:
            for control in control_results:
                summary["comparisons"].append(
                    {
                        "fixture": fixture_id,
                        "case": case_id,
                        "model": model,
                        "skillVariant": skill.variant,
                        "controlVariant": control.variant,
                        "generationTokenDelta": control.usage["totalTokens"] - skill.usage["totalTokens"],
                        "generationDurationDeltaMs": control.duration_ms - skill.duration_ms,
                    }
                )
    return summary
