from __future__ import annotations

import json
import os
from pathlib import Path

from codex_skill_bench.cli import main
from codex_skill_bench.suite_loader import load_suite


def test_load_basic_suite() -> None:
    suite, fixtures = load_suite(Path("examples/basic-suite/suite.yaml"))
    assert suite.name == "basic license header comparison"
    assert [model.name for model in suite.models] == ["default"]
    assert [variant.name for variant in suite.variants] == ["with-skill", "no-skill"]
    assert fixtures[0].fixture_id == "simple-python"
    assert fixtures[0].cases[0].case_id == "add-license"


def test_run_with_fake_codex(tmp_path: Path, monkeypatch) -> None:
    fake = tmp_path / "codex"
    fake.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv
out = Path(args[args.index("--output-last-message") + 1])
model = args[args.index("--model") + 1] if "--model" in args else "default"
prompt = args[-1]
out.write_text("done for " + model)
usage = {
    "input_tokens": 100 + len(prompt.split()),
    "cached_input_tokens": 0,
    "output_tokens": 12,
    "reasoning_output_tokens": 0,
}
print(json.dumps({"type": "thread.started", "thread_id": "fake"}))
print(json.dumps({"type": "turn.completed", "usage": usage}))
""",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    results = tmp_path / "results"
    assert main(["run", "examples/basic-suite/suite.yaml", "--results", str(results)]) == 0
    summary = results / "summary.yaml"
    assert summary.exists()
    text = summary.read_text()
    assert "with-skill" in text
    assert "no-skill" in text
    assert "generationTokenDelta" in text
