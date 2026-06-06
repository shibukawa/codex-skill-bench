from __future__ import annotations

from pathlib import Path
from fnmatch import fnmatch
from typing import Any

import yaml

from .models import CaseConfig, FixtureConfig, ModelConfig, SkillConfig, SuiteConfig, VariantConfig


def load_suite(path: Path) -> tuple[SuiteConfig, list[FixtureConfig]]:
    path = path.resolve()
    data = _load_yaml(path)
    base = path.parent

    fixtures_cfg = data.get("fixtures", {}) or {}
    fixtures_root = _resolve(base, fixtures_cfg.get("root", "fixtures"))
    case_glob = fixtures_cfg.get("caseGlob", "cases/*.yaml")
    skills = [_parse_skill(base, item) for item in data.get("skills", [])]
    skill_by_name = {skill.name: skill for skill in skills}

    models = [_parse_model(item) for item in data.get("models", [])]
    if not models:
        raise ValueError("suite must define at least one model")

    variants = [_parse_variant(base, item, skills, skill_by_name) for item in data.get("variants", [{"name": "default"}])]
    security = data.get("security", {}) or {}
    runner = data.get("runner", {}) or {}
    defaults = data.get("defaults", {}) or {}

    suite = SuiteConfig(
        path=path,
        name=str(data.get("name", path.stem)),
        fixtures_root=fixtures_root,
        case_glob=case_glob,
        skills=skills,
        models=models,
        variants=variants,
        security=security,
        runner=runner,
        defaults=defaults,
    )
    fixtures = discover_fixtures(suite, fixtures_cfg)
    return suite, fixtures


def discover_fixtures(suite: SuiteConfig, fixtures_cfg: dict[str, Any]) -> list[FixtureConfig]:
    exclude = set(fixtures_cfg.get("exclude", []) or [])
    if not suite.fixtures_root.exists():
        raise FileNotFoundError(f"fixtures root not found: {suite.fixtures_root}")

    fixtures: list[FixtureConfig] = []
    for fixture_dir in sorted(p for p in suite.fixtures_root.iterdir() if p.is_dir()):
        fixture_id = fixture_dir.name
        if any(fnmatch(fixture_id, pattern) for pattern in exclude):
            continue

        fixture_yaml = fixture_dir / "fixture.yaml"
        fixture_data = _load_yaml(fixture_yaml) if fixture_yaml.exists() else {}
        fixture_id = str(fixture_data.get("id", fixture_id))
        workspace = _resolve(fixture_dir, fixture_data.get("workspace", {}).get("path", "workspace"))
        cases = [_parse_case(case_path) for case_path in sorted(fixture_dir.glob(suite.case_glob))]
        fixtures.append(
            FixtureConfig(
                fixture_id=fixture_id,
                root=fixture_dir,
                workspace=workspace,
                cases=cases,
                defaults=fixture_data.get("defaults", {}) or {},
            )
        )
    return fixtures


def _parse_model(item: Any) -> ModelConfig:
    if isinstance(item, str):
        return ModelConfig(name=item)
    raise ValueError(f"models entries must be strings: {item!r}")


def _parse_skill(base: Path, item: Any) -> SkillConfig:
    if isinstance(item, str):
        path = _resolve(base, item)
        return SkillConfig(name=path.name, path=path)
    if isinstance(item, dict):
        path = _resolve(base, item["path"])
        return SkillConfig(
            name=str(item.get("name", path.name)),
            path=path,
            materialize_as=item.get("materializeAs"),
        )
    raise ValueError(f"invalid skill entry: {item!r}")


def _parse_variant(
    base: Path,
    item: dict[str, Any],
    skills: list[SkillConfig],
    skill_by_name: dict[str, SkillConfig],
) -> VariantConfig:
    name = str(item["name"])
    kind = str(item.get("kind", "skill"))
    skill_name = item.get("skill")
    selected_skill = None
    if kind == "skill":
        if skill_name is None and len(skills) == 1:
            selected_skill = skills[0]
            skill_name = selected_skill.name
        elif skill_name is not None:
            selected_skill = skill_by_name.get(str(skill_name))
            if selected_skill is None:
                raise ValueError(f"variant {name} references unknown skill: {skill_name}")
        else:
            raise ValueError(f"skill variant {name} requires skill or one configured suite skill")
    return VariantConfig(
        name=name,
        kind=kind,
        skill_name=str(skill_name) if skill_name else None,
        skill_path=selected_skill.path if selected_skill else None,
        materialize_as=item.get("materializeAs") or (selected_skill.materialize_as if selected_skill else None),
        control_of=item.get("controlOf"),
        allow_ambient_skills=bool(item.get("allowAmbientSkills", False)),
    )


def _parse_case(path: Path) -> CaseConfig:
    data = _load_yaml(path)
    prompt_file = data.get("promptFile")
    return CaseConfig(
        case_id=str(data["id"]),
        title=str(data.get("title", data["id"])),
        path=path,
        prompt=data.get("prompt"),
        prompt_file=(path.parent / prompt_file).resolve() if prompt_file else None,
        prompt_by_variant=data.get("promptByVariant", {}) or {},
        prompt_by_variant_kind=data.get("promptByVariantKind", {}) or {},
        timeout_seconds=_parse_duration_seconds(data.get("timeout")),
        raw=data,
    )


def resolve_prompt(case: CaseConfig, variant: VariantConfig) -> str:
    if variant.name in case.prompt_by_variant:
        return case.prompt_by_variant[variant.name]
    if variant.kind in case.prompt_by_variant_kind:
        return case.prompt_by_variant_kind[variant.kind]
    if case.prompt is not None:
        return case.prompt
    if case.prompt_file is not None:
        return case.prompt_file.read_text()
    raise ValueError(f"case {case.case_id} must define prompt, promptFile, or variant prompt")


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return loaded


def _resolve(base: Path, value: str | Path | None) -> Path:
    if value is None:
        return base
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def _parse_duration_seconds(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    text = str(raw)
    if text.endswith("ms"):
        return max(1, int(text[:-2]) // 1000)
    if text.endswith("s"):
        return int(text[:-1])
    if text.endswith("m"):
        return int(text[:-1]) * 60
    return int(text)
