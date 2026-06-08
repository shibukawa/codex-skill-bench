from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import yaml

from .models import RunSpec, VariantConfig
from .report import write_html_report
from .suite_loader import resolve_prompt


PROJECT_SKILL_ROOT = ".agents/skills"


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
    preload: dict[str, Any] | None = None
    exit_code: int | None = None
    error: str | None = None


@dataclass
class StreamTurnResult:
    status: str
    duration_ms: int | None
    final_response: str | None


class BenchRunner:
    def __init__(self, results_dir: Path, status: Callable[[str], None] | None = None):
        self.results_dir = results_dir.resolve()
        self.runs_dir = self.results_dir / "runs"
        self.status = status
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def run(self, specs: list[RunSpec]) -> dict[str, Any]:
        results: list[RunResult] = []
        total = len(specs)
        if total == 0:
            self._status("no runs selected")
        for index, spec in enumerate(specs, start=1):
            self._status(f"[{index}/{total}] start {spec.run_id}")
            result = self.run_one(spec)
            results.append(result)
            self._status(f"[{index}/{total}] {result.status} {spec.run_id} ({result.duration_ms}ms)")
        summary = build_summary(results)
        summary_path = self.results_dir / "summary.yaml"
        self._status(f"writing summary: {summary_path}")
        with summary_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(summary, f, sort_keys=False, allow_unicode=True)
        self._status(f"wrote summary: {summary_path}")
        report_path = write_html_report(self.results_dir, summary)
        self._status(f"wrote report: {report_path}")
        return summary

    def run_one(self, spec: RunSpec) -> RunResult:
        self._status(f"{spec.run_id}: preparing workspace")
        run_root = self.runs_dir / spec.run_id
        workspace = run_root / "workspace"
        if run_root.exists():
            shutil.rmtree(run_root)
        run_root.mkdir(parents=True)
        shutil.copytree(spec.fixture.workspace, workspace)

        materialized = self._materialize_variant(spec.variant, workspace, PROJECT_SKILL_ROOT)
        if materialized:
            self._status(f"{spec.run_id}: materialized skill {materialized}")
        prompt = resolve_prompt(spec.case, spec.variant)

        events_path = run_root / "events.jsonl"
        final_path = run_root / "final.md"
        stderr_path = run_root / "stderr.log"
        preload_events_path = run_root / "preload.events.jsonl"
        preload_final_path = run_root / "preload.final.md"
        preload_stderr_path = run_root / "preload.stderr.log"
        result_path = self.results_dir / f"{spec.run_id}.result.yaml"

        exit_code: int | None = None
        error: str | None = None
        preload: dict[str, Any] | None = None
        try:
            if should_preload_skill(spec):
                self._status(f"{spec.run_id}: preloading skill {skill_name(spec)}")
                preload = self._run_skill_preload(
                    spec,
                    workspace,
                    preload_events_path,
                    preload_final_path,
                    preload_stderr_path,
                )
                self._status(f"{spec.run_id}: preload {preload['status']} ({preload['durationMs']}ms)")
            started = time.monotonic()
            self._status(f"{spec.run_id}: running Codex")
            exit_code = self._run_codex(spec, workspace, prompt, events_path, final_path, stderr_path)
            if exit_code == 0 and should_require_skill_activation(spec) and not skill_was_activated(events_path, spec):
                exit_code = 1
                error = f"skill was not activated: {skill_name(spec)}"
                self._status(f"{spec.run_id}: {error}")
            status = "passed" if exit_code == 0 else "errored"
        except Exception as exc:  # keep per-run artifacts even on runner errors
            status = "errored"
            error = str(exc)
            stderr_path.write_text(str(exc), encoding="utf-8")
            started = locals().get("started", time.monotonic())
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
            preload=preload,
            exit_code=exit_code,
            error=error,
            artifacts={
                "runRoot": str(run_root),
                "workspace": str(workspace),
                "events": str(events_path),
                "final": str(final_path),
                "stderr": str(stderr_path),
                "preloadEvents": str(preload_events_path) if preload else "",
                "preloadFinal": str(preload_final_path) if preload else "",
                "preloadStderr": str(preload_stderr_path) if preload else "",
                "result": str(result_path),
                "materializedSkill": str(materialized) if materialized else "",
            },
        )
        write_result(result_path, result)
        return result

    def _status(self, message: str) -> None:
        if self.status is not None:
            self.status(message)

    def _materialize_variant(self, variant: VariantConfig, workspace: Path, skill_root: str) -> Path | None:
        if variant.kind == "control":
            return None
        if variant.skill_path is None:
            raise ValueError(f"skill variant {variant.name} requires a configured skill")
        target_name = variant.materialize_as or variant.skill_name or variant.skill_path.name
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
        return self._run_codex_sdk(spec, workspace, prompt, events_path, final_path, stderr_path)

    def _run_codex_sdk(
        self,
        spec: RunSpec,
        workspace: Path,
        prompt: str,
        events_path: Path,
        final_path: Path,
        stderr_path: Path,
    ) -> int:
        from openai_codex import ApprovalMode, Codex, Sandbox

        approval = _sdk_approval(str(spec.suite.security.get("approval", "never")), ApprovalMode)
        sandbox = _sdk_sandbox(str(spec.suite.security.get("sandbox", "workspace-write")), Sandbox)
        model = None if spec.model.name == "default" else spec.model.name

        with events_path.open("w", encoding="utf-8") as events, stderr_path.open("w", encoding="utf-8") as stderr:
            try:
                with Codex() as codex:
                    thread = codex.thread_start(
                        approval_mode=approval,
                        cwd=str(workspace),
                        ephemeral=True,
                        model=model,
                        sandbox=sandbox,
                    )
                    turn = thread.turn(prompt, cwd=str(workspace), model=model, sandbox=sandbox)
                    result = collect_streamed_turn(turn, events, turn_id=turn.id)
            except Exception as exc:
                stderr.write(str(exc))
                raise

            final_path.write_text(result.final_response or "", encoding="utf-8")
            return 0 if result.status == "completed" else 1

    def _run_skill_preload(
        self,
        spec: RunSpec,
        workspace: Path,
        events_path: Path,
        final_path: Path,
        stderr_path: Path,
    ) -> dict[str, Any]:
        from openai_codex import ApprovalMode, Codex, Sandbox, SkillInput, TextInput

        approval = _sdk_approval(str(spec.suite.security.get("approval", "never")), ApprovalMode)
        sandbox = _sdk_sandbox(str(spec.suite.security.get("sandbox", "workspace-write")), Sandbox)
        model = None if spec.model.name == "default" else spec.model.name
        name = skill_name(spec)
        skill_path = workspace / PROJECT_SKILL_ROOT / name
        prompt = str(
            spec.suite.runner.get(
                "skillPreloadPrompt",
                f"Load the ${name} skill only. Read its instructions and reply with a short confirmation.",
            )
        )

        started = time.monotonic()
        with events_path.open("w", encoding="utf-8") as events, stderr_path.open("w", encoding="utf-8") as stderr:
            try:
                with Codex() as codex:
                    thread = codex.thread_start(
                        approval_mode=approval,
                        cwd=str(workspace),
                        ephemeral=True,
                        model=model,
                        sandbox=sandbox,
                    )
                    turn = thread.turn(
                        [SkillInput(name=name, path=str(skill_path)), TextInput(prompt)],
                        cwd=str(workspace),
                        model=model,
                        sandbox=sandbox,
                    )
                    result = collect_streamed_turn(turn, events, turn_id=turn.id)
            except Exception as exc:
                stderr.write(str(exc))
                raise
            duration_ms = int((time.monotonic() - started) * 1000)
            final_path.write_text(result.final_response or "", encoding="utf-8")

        return {
            "status": result.status,
            "durationMs": duration_ms,
            "usage": read_usage(events_path),
            "artifacts": {
                "events": str(events_path),
                "final": str(final_path),
                "stderr": str(stderr_path),
            },
        }


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
            usage = usage_from_event(event)
            if not isinstance(usage, dict):
                continue
            total["inputTokens"] += int(usage.get("input_tokens", 0) or 0)
            total["inputTokens"] += int(usage.get("inputTokens", 0) or 0)
            total["cachedInputTokens"] += int(usage.get("cached_input_tokens", 0) or 0)
            total["cachedInputTokens"] += int(usage.get("cachedInputTokens", 0) or 0)
            total["outputTokens"] += int(usage.get("output_tokens", 0) or 0)
            total["outputTokens"] += int(usage.get("outputTokens", 0) or 0)
            total["reasoningOutputTokens"] += int(usage.get("reasoning_output_tokens", 0) or 0)
            total["reasoningOutputTokens"] += int(usage.get("reasoningOutputTokens", 0) or 0)
            if "total_tokens" in usage:
                total["totalTokens"] += int(usage.get("total_tokens", 0) or 0)
            if "totalTokens" in usage:
                total["totalTokens"] += int(usage.get("totalTokens", 0) or 0)
    if total["totalTokens"] == 0:
        total["totalTokens"] = total["inputTokens"] + total["outputTokens"]
    return total


def collect_streamed_turn(turn: Any, events_file: Any, *, turn_id: str) -> StreamTurnResult:
    completed_turn: dict[str, Any] | None = None
    items: list[dict[str, Any]] = []
    stream = turn.stream()
    try:
        for notification in stream:
            event = notification_to_dict(notification)
            events_file.write(json.dumps(event, ensure_ascii=False) + "\n")
            events_file.flush()
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            if event.get("method") == "item/completed" and payload.get("turnId") == turn_id:
                item = payload.get("item")
                if isinstance(item, dict):
                    items.append(item)
                continue
            if event.get("method") == "turn/completed":
                turn_payload = payload.get("turn")
                if isinstance(turn_payload, dict) and turn_payload.get("id") == turn_id:
                    completed_turn = turn_payload
    finally:
        stream.close()

    if completed_turn is None:
        raise RuntimeError("turn completed event not received")
    status = sdk_status_value(completed_turn.get("status"))
    if status == "failed":
        error = completed_turn.get("error")
        if isinstance(error, dict) and error.get("message"):
            raise RuntimeError(str(error["message"]))
        raise RuntimeError("turn failed with status failed")
    return StreamTurnResult(
        status=status,
        duration_ms=completed_turn.get("durationMs") or completed_turn.get("duration_ms"),
        final_response=final_assistant_response_from_items(items),
    )


def notification_to_dict(notification: Any) -> dict[str, Any]:
    return {
        "method": getattr(notification, "method", ""),
        "payload": sdk_model_to_dict(getattr(notification, "payload", None)),
    }


def final_assistant_response_from_items(items: list[dict[str, Any]]) -> str | None:
    last_unknown_phase_response: str | None = None
    for item in reversed(items):
        if item.get("type") != "agentMessage":
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        phase = item.get("phase")
        if phase == "final_answer":
            return text
        if phase is None and last_unknown_phase_response is None:
            last_unknown_phase_response = text
    return last_unknown_phase_response


def usage_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    usage = event.get("usage")
    if isinstance(usage, dict):
        if "total" in usage and isinstance(usage["total"], dict):
            return usage["total"]
        return usage
    if event.get("method") == "thread/tokenUsage/updated":
        payload = event.get("payload")
        if isinstance(payload, dict):
            token_usage = payload.get("tokenUsage") or payload.get("token_usage")
            if isinstance(token_usage, dict):
                if "total" in token_usage and isinstance(token_usage["total"], dict):
                    return token_usage["total"]
                return token_usage
    return None


def sdk_usage_to_dict(usage: Any) -> dict[str, Any] | None:
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump(by_alias=True, mode="json")
    return sdk_model_to_dict(usage)


def sdk_status_value(status: Any) -> str:
    return str(getattr(status, "value", status))


def sdk_model_to_dict(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dict__"):
        return {key: sdk_model_to_dict(item) for key, item in vars(value).items() if not key.startswith("_")}
    if isinstance(value, list):
        return [sdk_model_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: sdk_model_to_dict(item) for key, item in value.items()}
    return value


def _sdk_approval(raw: str, approval_mode: Any) -> Any:
    if raw in {"never", "deny_all", "deny-all"}:
        return approval_mode.deny_all
    return approval_mode.auto_review


def _sdk_sandbox(raw: str, sandbox: Any) -> Any:
    normalized = raw.replace("_", "-")
    if normalized == "read-only":
        return sandbox.read_only
    if normalized == "workspace-write":
        return sandbox.workspace_write
    if normalized == "full-access":
        return sandbox.full_access
    raise ValueError(f"unsupported sdk sandbox: {raw}")


def should_preload_skill(spec: RunSpec) -> bool:
    return spec.variant.kind == "skill"


def should_require_skill_activation(spec: RunSpec) -> bool:
    return spec.variant.kind == "skill"


def skill_name(spec: RunSpec) -> str:
    if spec.variant.materialize_as:
        return spec.variant.materialize_as
    if spec.variant.skill_name:
        return spec.variant.skill_name
    if spec.variant.skill_path:
        return spec.variant.skill_path.name
    return spec.variant.name


def skill_was_activated(events_path: Path, spec: RunSpec) -> bool:
    if not events_path.exists():
        return False
    name = skill_name(spec)
    text = events_path.read_text(encoding="utf-8", errors="replace")
    return f"{PROJECT_SKILL_ROOT}/{name}/" in text


def write_result(path: Path, result: RunResult) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"run": result_to_dict(result)}, f, sort_keys=False, allow_unicode=True)


def result_to_dict(result: RunResult) -> dict[str, Any]:
    estimated_repeat_duration_ms = result.duration_ms
    if result.preload:
        estimated_repeat_duration_ms = max(0, result.duration_ms - int(result.preload.get("durationMs", 0) or 0))
    return {
        "id": result.run_id,
        "fixture": result.fixture_id,
        "case": result.case_id,
        "model": result.model,
        "variant": result.variant,
        "variantKind": result.variant_kind,
        "status": result.status,
        "durationMs": result.duration_ms,
        "estimatedRepeatDurationMs": estimated_repeat_duration_ms,
        "exitCode": result.exit_code,
        "usage": result.usage,
        "preload": result.preload,
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
                "estimatedRepeatDurationMs": result_to_dict(result)["estimatedRepeatDurationMs"],
                "usage": result.usage,
                "preload": result.preload,
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
                        "generationEstimatedRepeatDurationDeltaMs": control.duration_ms
                        - result_to_dict(skill)["estimatedRepeatDurationMs"],
                    }
                )
    return summary
