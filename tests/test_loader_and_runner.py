from __future__ import annotations

import json
import re
from pathlib import Path

from codex_skill_bench.cli import eval_main, list_main, main
from codex_skill_bench.runner import PROJECT_SKILL_ROOT, BenchRunner, read_usage, skill_name, skill_was_activated
from codex_skill_bench.models import RunSpec
from codex_skill_bench.suite_loader import load_suite, resolve_prompt


def test_load_basic_suite() -> None:
    suite, fixtures = load_suite(Path("examples/basic-suite/suite.yaml"))
    assert suite.name == "basic license header comparison"
    assert suite.fixtures_root.name == "fixtures"
    assert suite.report["resultsDir"] == "results"
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
    report = results / "report.html"
    assert report.exists()
    text = summary.read_text()
    assert "with-skill" in text
    assert "no-skill" in text
    assert "preload" in text
    assert "generationTokenDelta" in text
    html = report.read_text(encoding="utf-8")
    assert "Skill Bench Report" in html
    assert "simple-python" in html
    assert "comparisonImprovements" in html
    assert "Repeated time improvement" in html
    assert "Open workspace" in html
    assert "summary.yaml" in html
    assert "&amp;id" not in html
    assert '"href": "runs/' in html
    match = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', html, re.S)
    assert match
    report_data = json.loads(match.group(1))
    case = report_data["cases"][0]
    assert case["comparisonImprovements"][0]["baselineVariant"] == "no-skill"
    assert case["comparisonImprovements"][0]["skillVariant"] == "with-skill"
    assert case["comparisonImprovements"][0]["preloadDurationMs"] == 10
    assert case["comparisonImprovements"][0]["preloadTokens"] == 6
    assert case["variants"]["with-skill"]["attempts"][0]["eventItems"]


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
    assert (results / "report.html").exists()


def test_eval_prints_progress_to_stderr(tmp_path: Path, monkeypatch, capsys) -> None:
    def fake_preload(self, spec, workspace, events_path, final_path, stderr_path):
        final_path.write_text("preloaded", encoding="utf-8")
        events_path.write_text(json.dumps({"type": "turn.completed", "usage": {"inputTokens": 5, "outputTokens": 1}}), encoding="utf-8")
        return {"status": "completed", "durationMs": 10, "usage": read_usage(events_path), "artifacts": {}}

    def fake_run(self, spec, workspace, prompt, events_path, final_path, stderr_path):
        final_path.write_text("done", encoding="utf-8")
        events_path.write_text(json.dumps({"type": "turn.completed", "usage": {"inputTokens": 100, "outputTokens": 12}}), encoding="utf-8")
        return 0

    monkeypatch.setattr(BenchRunner, "_run_skill_preload", fake_preload)
    monkeypatch.setattr(BenchRunner, "_run_codex_sdk", fake_run)
    results = tmp_path / "results"

    assert main(["eval", "examples/basic-suite/suite.yaml", "--results", str(results)]) == 0

    captured = capsys.readouterr()
    assert "[codex-skill-bench] loading suite:" in captured.err
    assert "[codex-skill-bench] selected runs: 2" in captured.err
    assert "[codex-skill-bench] [1/2] start simple-python__add-license-header__default__with-skill__attempt-1" in captured.err
    assert "preloading skill license-header" in captured.err
    assert "running Codex" in captured.err
    assert "wrote summary:" in captured.err
    assert "wrote report:" in captured.err


def test_keyboard_interrupt_is_clean_error(monkeypatch, capsys) -> None:
    def fake_run(self, specs):
        raise KeyboardInterrupt

    monkeypatch.setattr(BenchRunner, "run", fake_run)

    assert main(["eval", "examples/basic-suite/suite.yaml"]) == 130

    captured = capsys.readouterr()
    assert "error: interrupted by user" in captured.err
    assert "Traceback" not in captured.err


def test_eval_main_uses_current_directory_suite(tmp_path: Path, monkeypatch) -> None:
    def fake_preload(self, spec, workspace, events_path, final_path, stderr_path):
        final_path.write_text("preloaded", encoding="utf-8")
        events_path.write_text(json.dumps({"type": "turn.completed", "usage": {"inputTokens": 5, "outputTokens": 1}}), encoding="utf-8")
        return {"status": "completed", "durationMs": 10, "usage": read_usage(events_path), "artifacts": {}}

    def fake_run(self, spec, workspace, prompt, events_path, final_path, stderr_path):
        final_path.write_text("done", encoding="utf-8")
        events_path.write_text(json.dumps({"type": "turn.completed", "usage": {"inputTokens": 100, "outputTokens": 12}}), encoding="utf-8")
        return 0

    monkeypatch.setattr(BenchRunner, "_run_skill_preload", fake_preload)
    monkeypatch.setattr(BenchRunner, "_run_codex_sdk", fake_run)
    monkeypatch.chdir(Path("examples/basic-suite"))
    results = tmp_path / "results"

    assert eval_main(["--results", str(results)]) == 0

    assert (results / "summary.yaml").exists()
    assert (results / "report.html").exists()


def test_list_main_uses_current_directory_suite(monkeypatch, capsys) -> None:
    monkeypatch.chdir(Path("examples/basic-suite"))

    assert list_main([]) == 0

    out = capsys.readouterr().out
    assert "simple-python__add-license-header__default__with-skill__attempt-1" in out
    assert "simple-python__add-license-header__default__no-skill__attempt-1" in out


def test_omitted_suite_without_current_suite_is_clean_error(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    assert eval_main([]) == 2

    captured = capsys.readouterr()
    assert "suite argument is required unless ./suite.yaml exists" in captured.err
    assert "Traceback" not in captured.err


def test_invalid_suite_yaml_is_clean_grouped_error(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "suite.yaml").write_text(":\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert list_main([]) == 2

    captured = capsys.readouterr()
    assert "error: invalid suite configuration" in captured.err
    assert "invalid YAML" in captured.err
    assert "Traceback" not in captured.err


def test_multiple_validation_errors_are_reported_together(tmp_path: Path, monkeypatch, capsys) -> None:
    fixtures = tmp_path / "fixtures" / "broken"
    fixtures.mkdir(parents=True)
    (tmp_path / "suite.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "name: broken",
                "fixtures:",
                "  root: fixtures",
                "models:",
                "  - 123",
                "variants:",
                "  - name: with-skill",
                "    kind: skill",
                "    skill: missing",
            ]
        ),
        encoding="utf-8",
    )
    (fixtures / "fixture.yaml").write_text(
        "\n".join(
            [
                "cases:",
                "  - title: Duplicate",
                "    prompt: one",
                "  - title: Duplicate",
                "    prompt: two",
                "  - id: bad id",
                "    title: Bad Id",
                "    prompt: three",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert list_main([]) == 2

    captured = capsys.readouterr()
    assert "models[0] must be a string" in captured.err
    assert "variant with-skill references unknown skill: missing" in captured.err
    assert "fixture workspace not found" in captured.err
    assert "duplicate case id: duplicate" in captured.err
    assert "case Bad Id has invalid id: bad id" in captured.err
    assert "Traceback" not in captured.err


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
    bench_skill = tmp_path / ".agents" / "skills" / "codex-skill-bench" / "SKILL.md"
    assert bench_skill.exists()
    assert "uvx --from git+https://github.com/shibukawa/codex-skill-bench.git eval" in bench_skill.read_text(encoding="utf-8")
    assert (tmp_path / ".agents" / "skills" / "codex-skill-bench" / "agents" / "openai.yaml").exists()
    assert (tmp_path / ".agents" / "skills" / "codex-skill-bench" / "references" / "format.md").exists()
    assert (tmp_path / ".agents" / "skills" / "codex-skill-bench" / "references" / "results.md").exists()


def test_init_installs_bench_skill_when_suite_exists(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "suite.yaml").write_text("version: 1\nname: existing\nmodels:\n  - default\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert main(["init"]) == 0

    assert (tmp_path / ".agents" / "skills" / "codex-skill-bench" / "SKILL.md").exists()


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
