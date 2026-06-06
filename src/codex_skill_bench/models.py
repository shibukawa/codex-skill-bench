from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelConfig:
    name: str


@dataclass(frozen=True)
class SkillConfig:
    name: str
    path: Path
    materialize_as: str | None = None


@dataclass(frozen=True)
class VariantConfig:
    name: str
    kind: str = "skill"
    skill_name: str | None = None
    skill_path: Path | None = None
    materialize_as: str | None = None
    control_of: str | None = None
    allow_ambient_skills: bool = False


@dataclass(frozen=True)
class FixtureConfig:
    fixture_id: str
    root: Path
    workspace: Path
    cases: list["CaseConfig"]
    defaults: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseConfig:
    case_id: str
    title: str
    path: Path
    prompt: str | None = None
    prompt_file: Path | None = None
    prompt_variants: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SuiteConfig:
    path: Path
    name: str
    fixtures_root: Path
    skills: list[SkillConfig]
    models: list[ModelConfig]
    variants: list[VariantConfig]
    security: dict[str, Any]
    runner: dict[str, Any]
    defaults: dict[str, Any]


@dataclass(frozen=True)
class RunSpec:
    suite: SuiteConfig
    fixture: FixtureConfig
    case: CaseConfig
    model: ModelConfig
    variant: VariantConfig
    attempt: int = 1

    @property
    def run_id(self) -> str:
        return "__".join(
            [
                self.fixture.fixture_id,
                self.case.case_id,
                safe_id(self.model.name),
                self.variant.name,
                f"attempt-{self.attempt}",
            ]
        )


def safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value).strip("-")
