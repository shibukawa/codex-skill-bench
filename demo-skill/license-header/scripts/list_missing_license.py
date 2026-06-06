#!/usr/bin/env python3
"""List project files missing a selected license header as JSON Lines."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from license_header_utils import detect_style, has_license_header, load_license


DEFAULT_EXTENSIONS = {
    ".bash",
    ".c",
    ".cc",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".md",
    ".mjs",
    ".pl",
    ".properties",
    ".py",
    ".rb",
    ".rs",
    ".scss",
    ".sh",
    ".svelte",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
    ".zsh",
}

SKIP_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Project root to audit")
    parser.add_argument("--license", required=True, type=Path, help="License text file")
    parser.add_argument("--year", help="Value for {year} placeholders")
    parser.add_argument("--owner", help="Value for {owner} placeholders")
    parser.add_argument("--style", choices=["auto", "hash", "line", "block"], default="auto")
    parser.add_argument("--extensions", help="Comma-separated extension allowlist, such as .py,.js,.ts")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files and directories except VCS dirs")
    return parser.parse_args()


def extension_set(raw: str | None) -> set[str]:
    if raw is None:
        return DEFAULT_EXTENSIONS
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def should_skip(path: Path, root: Path, extensions: set[str], include_hidden: bool) -> bool:
    rel_parts = path.relative_to(root).parts
    for part in rel_parts[:-1]:
        if part in {".git", ".hg", ".svn"}:
            return True
        if part in SKIP_DIRS:
            return True
        if not include_hidden and part.startswith("."):
            return True
    name = path.name
    if not include_hidden and name.startswith("."):
        return True
    if path.suffix.lower() in extensions:
        return False
    if name in {"Dockerfile", "Makefile"} and "" not in extensions:
        return False
    return True


def iter_candidate_files(root: Path, extensions: set[str], include_hidden: bool):
    for path in sorted(root.rglob("*")):
        if path.is_file() and not should_skip(path, root, extensions, include_hidden):
            yield path


def emit(record: dict[str, str]) -> None:
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    license_text = load_license(args.license, year=args.year, owner=args.owner)
    extensions = extension_set(args.extensions)

    for path in iter_candidate_files(root, extensions, args.include_hidden):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            emit({"path": rel, "reason": "non-utf8", "style": detect_style(path, args.style)})
            continue
        if not has_license_header(text, license_text):
            emit({"path": rel, "reason": "missing-license", "style": detect_style(path, args.style)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
