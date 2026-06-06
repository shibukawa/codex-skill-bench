from __future__ import annotations

import json
from pathlib import Path

from codex_skill_bench.cli import main
from codex_skill_bench.runner import PROJECT_SKILL_ROOT, BenchRunner, read_usage, skill_name, skill_was_activated
from codex_skill_bench.models import RunSpec
from codex_skill_bench.suite_loader import load_suite, resolve_prompt


def test_load_basic_suite() -> None:
    suite, fixtures = load_suite(Path("examples/basic-suite/suite.yaml"))
    assert suite.name == "basic license header comparison"
    assert [skill.name for skill in suite.skills] == ["license-header"]
    assert [model.name for model in suite.models] == ["default"]
    assert [variant.name for variant in suite.variants] == ["with-skill", "no-skill"]
    assert suite.variants[0].skill_name == "license-header"
    assert fixtures[0].fixture_id == "simple-python"
    assert fixtures[0].cases[0].case_id == "add-license-header"
    assert fixtures[0].cases[0].title == "Add license header"
    assert "promptVariants" in fixtures[0].cases[0].raw


def test_resolve_prompt_variants() -> None:
    suite, fixtures = load_suite(Path("examples/basic-suite/suite.yaml"))
    case = fixtures[0].cases[0]
    skill_prompt = resolve_prompt(case, suite.variants[0])
    control_prompt = resolve_prompt(case, suite.variants[1])
    assert skill_prompt.startswith("Use the $license-header skill.")
    assert "$skill" not in skill_prompt
    assert control_prompt.startswith("Add an MIT license header")


def test_run_with_fake_sdk(tmp_path: Path, monkeypatch) -> None:
    def fake_preload(self, spec, workspace, events_path, final_path, stderr_path):
        final_path.write_text("preloaded", encoding="utf-8")
        events_path.write_text(json.dumps({"type": "turn.completed", "usage": {"inputTokens": 5, "outputTokens": 1}}), encoding="utf-8")
        return {"status": "completed", "durationMs": 10, "usage": read_usage(events_path), "artifacts": {}}

    def fake_run(self, spec, workspace, prompt, events_path, final_path, stderr_path):
        final_path.write_text("done", encoding="utf-8")
        skill_path = f"{PROJECT_SKILL_ROOT}/{skill_name(spec)}/SKILL.md" if spec.variant.kind == "skill" else ""
        events_path.write_text(
            json.dumps({"type": "turn.completed", "usage": {"inputTokens": 100, "outputTokens": 12}, "path": skill_path}),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(BenchRunner, "_run_skill_preload", fake_preload)
    monkeypatch.setattr(BenchRunner, "_run_codex_sdk", fake_run)
    results = tmp_path / "results"
    assert main(["run", "examples/basic-suite/suite.yaml", "--results", str(results)]) == 0
    summary = results / "summary.yaml"
    assert summary.exists()
    text = summary.read_text()
    assert "with-skill" in text
    assert "no-skill" in text
    assert "preload" in text
    assert "generationTokenDelta" in text


def test_eval_alias_runs_with_fake_sdk(tmp_path: Path, monkeypatch) -> None:
    def fake_preload(self, spec, workspace, events_path, final_path, stderr_path):
        final_path.write_text("preloaded", encoding="utf-8")
        events_path.write_text(json.dumps({"type": "turn.completed", "usage": {"inputTokens": 5, "outputTokens": 1}}), encoding="utf-8")
        return {"status": "completed", "durationMs": 10, "usage": read_usage(events_path), "artifacts": {}}

    def fake_run(self, spec, workspace, prompt, events_path, final_path, stderr_path):
        final_path.write_text("done", encoding="utf-8")
        skill_path = f"{PROJECT_SKILL_ROOT}/{skill_name(spec)}/SKILL.md" if spec.variant.kind == "skill" else ""
        events_path.write_text(
            json.dumps({"type": "turn.completed", "usage": {"inputTokens": 100, "outputTokens": 12}, "path": skill_path}),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(BenchRunner, "_run_skill_preload", fake_preload)
    monkeypatch.setattr(BenchRunner, "_run_codex_sdk", fake_run)
    results = tmp_path / "results"
    assert main(["eval", "examples/basic-suite/suite.yaml", "--results", str(results)]) == 0
    assert (results / "summary.yaml").exists()


def test_init_writes_suite_and_fixture_readme(tmp_path: Path, monkeypatch) -> None:
    skill = tmp_path / "skills" / "demo-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Demo Skill\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert main(["init", str(skill)]) == 0

    suite = (tmp_path / "suite.yaml").read_text(encoding="utf-8")
    assert "fixtures:" in suite
    assert "with-skill" in suite
    assert "no-skill" in suite
    assert "skills/demo-skill" in suite
    readme = tmp_path / "fixtures" / "README.md"
    assert readme.exists()
    assert "codex-skill-bench.git add-fixture" in readme.read_text(encoding="utf-8")


def test_add_fixture_snapshots_root_without_generated_dirs(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "fixtures" / "existing").mkdir(parents=True)
    (tmp_path / ".agent" / "skills" / "local").mkdir(parents=True)
    (tmp_path / ".agent" / "skills" / "local" / "SKILL.md").write_text("# Local\n", encoding="utf-8")
    (tmp_path / ".agents" / "skills" / "local").mkdir(parents=True)
    (tmp_path / ".agents" / "skills" / "local" / "SKILL.md").write_text("# Local\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert main(["add-fixture", "root-snapshot", ".", "Inspect the project."]) == 0

    fixture = tmp_path / "fixtures" / "root-snapshot"
    assert (fixture / "workspace" / "src" / "sample.py").exists()
    assert not (fixture / "workspace" / "fixtures").exists()
    assert not (fixture / "workspace" / ".agent" / "skills").exists()
    assert not (fixture / "workspace" / ".agents" / "skills").exists()
    fixture_yaml = (fixture / "fixture.yaml").read_text(encoding="utf-8")
    assert "prompt: Inspect the project." in fixture_yaml


def test_read_sdk_usage_and_skill_activation(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps(
            {
                "type": "turn.completed",
                "usage": {
                    "total": {
                        "inputTokens": 10,
                        "cachedInputTokens": 2,
                        "outputTokens": 3,
                        "reasoningOutputTokens": 1,
                        "totalTokens": 13,
                    }
                },
                "items": [
                    {
                        "type": "commandExecution",
                        "command": "python3 .agents/skills/license-header/scripts/prepend_license.py",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    suite, fixtures = load_suite(Path("examples/basic-suite/suite.yaml"))
    spec = RunSpec(
        suite=suite,
        fixture=fixtures[0],
        case=fixtures[0].cases[0],
        model=suite.models[0],
        variant=suite.variants[0],
    )
    assert read_usage(events)["totalTokens"] == 13
    assert skill_was_activated(events, spec)
