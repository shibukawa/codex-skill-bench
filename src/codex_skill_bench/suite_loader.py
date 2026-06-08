from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from fnmatch import fnmatch
import re
from typing import Any

import yaml

from .models import CaseConfig, FixtureConfig, ModelConfig, SkillConfig, SuiteConfig, VariantConfig


@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    message: str


class SuiteValidationError(Exception):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__("invalid suite configuration")


def load_suite(path: Path) -> tuple[SuiteConfig, list[FixtureConfig]]:
    path = path.resolve()
    errors: list[ValidationIssue] = []
    data = _load_yaml(path, errors)
    if errors:
        raise SuiteValidationError(errors)

    base = path.parent

    fixtures_cfg = _mapping_field(data, "fixtures", path, errors, default={})
    fixtures_root = _resolve(base, fixtures_cfg.get("root", "fixtures"))
    skills = _parse_skills(base, data.get("skills", []), path, errors)
    skill_by_name = {skill.name: skill for skill in skills}

    models = _parse_models(data.get("models", []), path, errors)
    if not models:
        errors.append(ValidationIssue(path, "suite must define at least one model"))

    variants = _parse_variants(base, data.get("variants", [{"name": "default"}]), skills, skill_by_name, path, errors)
    security = _mapping_field(data, "security", path, errors, default={})
    runner = _mapping_field(data, "runner", path, errors, default={})
    report = _mapping_field(data, "report", path, errors, default={})
    defaults = _mapping_field(data, "defaults", path, errors, default={})

    suite = SuiteConfig(
        path=path,
        name=str(data.get("name", path.stem)),
        fixtures_root=fixtures_root,
        skills=skills,
        models=models,
        variants=variants,
        security=security,
        runner=runner,
        report=report,
        defaults=defaults,
    )
    fixtures = discover_fixtures(suite, fixtures_cfg, errors)
    if errors:
        raise SuiteValidationError(errors)
    return suite, fixtures


def discover_fixtures(
    suite: SuiteConfig,
    fixtures_cfg: dict[str, Any],
    errors: list[ValidationIssue] | None = None,
) -> list[FixtureConfig]:
    should_raise = errors is None
    errors = errors if errors is not None else []
    exclude = set(fixtures_cfg.get("exclude", []) or [])
    if not suite.fixtures_root.exists():
        errors.append(ValidationIssue(suite.fixtures_root, "fixtures root not found"))
        if should_raise:
            raise SuiteValidationError(errors)
        return []

    fixtures: list[FixtureConfig] = []
    for fixture_dir in sorted(p for p in suite.fixtures_root.iterdir() if p.is_dir()):
        fixture_id = fixture_dir.name
        if any(fnmatch(fixture_id, pattern) for pattern in exclude):
            continue

        fixture_yaml = fixture_dir / "fixture.yaml"
        fixture_data = _load_yaml(fixture_yaml, errors) if fixture_yaml.exists() else {}
        workspace = fixture_dir / "workspace"
        if not workspace.exists():
            errors.append(ValidationIssue(workspace, "fixture workspace not found"))
        cases = _parse_cases(fixture_yaml, fixture_data.get("cases", []), fixture_dir, errors)
        fixtures.append(
            FixtureConfig(
                fixture_id=fixture_id,
                root=fixture_dir,
                workspace=workspace,
                cases=cases,
                defaults=fixture_data.get("defaults", {}) or {},
            )
        )
    if should_raise and errors:
        raise SuiteValidationError(errors)
    return fixtures


def _parse_models(raw: Any, path: Path, errors: list[ValidationIssue]) -> list[ModelConfig]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        errors.append(ValidationIssue(path, "models must be a list of strings"))
        return []

    models: list[ModelConfig] = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            models.append(ModelConfig(name=item))
        else:
            errors.append(ValidationIssue(path, f"models[{index}] must be a string: {item!r}"))
    return models


def _parse_skills(base: Path, raw: Any, path: Path, errors: list[ValidationIssue]) -> list[SkillConfig]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        errors.append(ValidationIssue(path, "skills must be a list"))
        return []

    skills: list[SkillConfig] = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            skill_path = _resolve(base, item)
            skills.append(SkillConfig(name=skill_path.name, path=skill_path))
        elif isinstance(item, dict):
            if "path" not in item:
                errors.append(ValidationIssue(path, f"skills[{index}] must define path"))
                continue
            skill_path = _resolve(base, item["path"])
            skills.append(
                SkillConfig(
                    name=str(item.get("name", skill_path.name)),
                    path=skill_path,
                    materialize_as=item.get("materializeAs"),
                )
            )
        else:
            errors.append(ValidationIssue(path, f"invalid skills[{index}] entry: {item!r}"))
    return skills


def _parse_variants(
    base: Path,
    raw: Any,
    skills: list[SkillConfig],
    skill_by_name: dict[str, SkillConfig],
    path: Path,
    errors: list[ValidationIssue],
) -> list[VariantConfig]:
    if not isinstance(raw, list):
        errors.append(ValidationIssue(path, "variants must be a list"))
        return []

    variants: list[VariantConfig] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(ValidationIssue(path, f"variants[{index}] must be a mapping"))
            continue
        variant = _parse_variant(base, item, skills, skill_by_name, path, index, errors)
        if variant is not None:
            variants.append(variant)
    return variants


def _parse_variant(
    base: Path,
    item: dict[str, Any],
    skills: list[SkillConfig],
    skill_by_name: dict[str, SkillConfig],
    path: Path,
    index: int,
    errors: list[ValidationIssue],
) -> VariantConfig | None:
    if "name" not in item:
        errors.append(ValidationIssue(path, f"variants[{index}] must define name"))
        return None
    name = str(item["name"])
    kind = str(item.get("kind", "skill"))
    if kind not in {"skill", "control"}:
        errors.append(ValidationIssue(path, f"variant {name} has invalid kind: {kind}"))
        return None
    skill_name = item.get("skill")
    selected_skill = None
    if kind == "skill":
        if skill_name is None and len(skills) == 1:
            selected_skill = skills[0]
            skill_name = selected_skill.name
        elif skill_name is not None:
            selected_skill = skill_by_name.get(str(skill_name))
            if selected_skill is None:
                errors.append(ValidationIssue(path, f"variant {name} references unknown skill: {skill_name}"))
                return None
        else:
            errors.append(ValidationIssue(path, f"skill variant {name} requires skill or one configured suite skill"))
            return None
    return VariantConfig(
        name=name,
        kind=kind,
        skill_name=str(skill_name) if skill_name else None,
        skill_path=selected_skill.path if selected_skill else None,
        materialize_as=item.get("materializeAs") or (selected_skill.materialize_as if selected_skill else None),
        control_of=item.get("controlOf"),
        allow_ambient_skills=bool(item.get("allowAmbientSkills", False)),
    )


def _parse_cases(path: Path, raw: Any, base: Path, errors: list[ValidationIssue]) -> list[CaseConfig]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        errors.append(ValidationIssue(path, "cases must be a list"))
        return []

    cases: list[CaseConfig] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(ValidationIssue(path, f"cases[{index}] must be a mapping"))
            continue
        case = _parse_case_data(path, item, base, index, errors)
        if case is None:
            continue
        if not case.case_id:
            errors.append(ValidationIssue(path, f"cases[{index}] has an empty case id"))
            continue
        if case.case_id in seen:
            errors.append(ValidationIssue(path, f"duplicate case id: {case.case_id}"))
            continue
        seen.add(case.case_id)
        cases.append(case)
    return cases


def _parse_case_data(
    path: Path,
    data: dict[str, Any],
    base: Path,
    index: int,
    errors: list[ValidationIssue],
) -> CaseConfig | None:
    if "prompt" in data and "promptVariants" in data:
        errors.append(ValidationIssue(path, f"case {data.get('title', '<untitled>')} must not define both prompt and promptVariants"))
    prompt_file = data.get("promptFile")
    if "title" not in data:
        errors.append(ValidationIssue(path, f"cases[{index}] must define title"))
        return None
    title = str(data["title"])
    prompt = data.get("prompt")
    prompt_variants = data.get("promptVariants", {}) or {}
    if prompt_variants and not isinstance(prompt_variants, dict):
        errors.append(ValidationIssue(path, f"case {title} promptVariants must be a mapping"))
        prompt_variants = {}
    if prompt is not None:
        prompt_variants = {"skill": prompt, "no-skill": prompt}
    try:
        timeout_seconds = _parse_duration_seconds(data.get("timeout"))
    except ValueError as exc:
        errors.append(ValidationIssue(path, f"case {title} has invalid timeout: {exc}"))
        timeout_seconds = None
    case_id = str(data.get("id", case_id_from_title(title)))
    if not _valid_id(case_id):
        errors.append(ValidationIssue(path, f"case {title} has invalid id: {case_id}"))
    return CaseConfig(
        case_id=case_id,
        title=title,
        path=path,
        prompt=prompt,
        prompt_file=(base / prompt_file).resolve() if prompt_file else None,
        prompt_variants=prompt_variants,
        timeout_seconds=timeout_seconds,
        raw=data,
    )


def resolve_prompt(case: CaseConfig, variant: VariantConfig) -> str:
    prompt = _select_prompt(case, variant)
    if prompt is not None:
        return _render_prompt(prompt, variant)
    if case.prompt_file is not None:
        return _render_prompt(case.prompt_file.read_text(), variant)
    raise ValueError(f"case {case.case_id} must define prompt, promptFile, or promptVariants")


def _select_prompt(case: CaseConfig, variant: VariantConfig) -> str | None:
    variants = case.prompt_variants
    if variant.name in variants:
        return variants[variant.name]
    if variant.kind == "control":
        return variants.get("no-skill")
    if variant.kind == "skill":
        if variant.skill_name and f"specific-skill[{variant.skill_name}]" in variants:
            return variants[f"specific-skill[{variant.skill_name}]"]
        return variants.get("skill")
    return None


def _render_prompt(prompt: str, variant: VariantConfig) -> str:
    if variant.kind != "skill" or not variant.skill_name:
        return prompt
    skill_ref = f"${variant.skill_name}"
    rendered = prompt.replace("$skill", skill_ref)
    if skill_ref not in rendered:
        rendered = f"Use the {skill_ref} skill.\n{rendered}"
    return rendered


def _load_yaml(path: Path, errors: list[ValidationIssue]) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
    except FileNotFoundError:
        errors.append(ValidationIssue(path, "file not found"))
        return {}
    except yaml.YAMLError as exc:
        errors.append(ValidationIssue(path, f"invalid YAML: {exc}"))
        return {}
    if not isinstance(loaded, dict):
        errors.append(ValidationIssue(path, "YAML root must be a mapping"))
        return {}
    return loaded


def _mapping_field(data: dict[str, Any], name: str, path: Path, errors: list[ValidationIssue], default: dict[str, Any]) -> dict[str, Any]:
    raw = data.get(name, default) or default
    if isinstance(raw, dict):
        return raw
    errors.append(ValidationIssue(path, f"{name} must be a mapping"))
    return default


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


def case_id_from_title(title: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", title.strip().lower())
    return normalized.strip("-")


def _valid_id(value: str) -> bool:
    return bool(value) and re.fullmatch(r"[a-zA-Z0-9._-]+", value) is not None
