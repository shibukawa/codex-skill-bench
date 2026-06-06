#!/usr/bin/env python3
"""Shared helpers for license header insertion and auditing."""

from __future__ import annotations

import re
from pathlib import Path


LINE_COMMENT_EXTS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".mjs",
    ".rs",
    ".scss",
    ".swift",
    ".ts",
    ".tsx",
}

HASH_COMMENT_EXTS = {
    ".bash",
    ".conf",
    ".env",
    ".pl",
    ".properties",
    ".ps1",
    ".py",
    ".rb",
    ".sh",
    ".toml",
    ".yaml",
    ".yml",
    ".zsh",
}

BLOCK_COMMENT_EXTS = {
    ".html",
    ".md",
    ".svelte",
    ".vue",
    ".xml",
}


def load_license(path: Path, year: str | None = None, owner: str | None = None) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if year is not None:
        text = text.replace("{year}", year)
    if owner is not None:
        text = text.replace("{owner}", owner)
    return text


def detect_style(path: Path, requested: str = "auto") -> str:
    if requested != "auto":
        return requested
    suffix = path.suffix.lower()
    if suffix in HASH_COMMENT_EXTS or path.name in {"Dockerfile", "Makefile"}:
        return "hash"
    if suffix in LINE_COMMENT_EXTS:
        return "line"
    if suffix in BLOCK_COMMENT_EXTS:
        return "block"
    return "hash"


def comment_license(license_text: str, style: str) -> str:
    lines = license_text.splitlines()
    if style == "hash":
        return "\n".join("#" if not line else f"# {line}" for line in lines) + "\n\n"
    if style == "line":
        return "\n".join("//" if not line else f"// {line}" for line in lines) + "\n\n"
    if style == "block":
        body = "\n".join(" *" if not line else f" * {line}" for line in lines)
        return f"/*\n{body}\n */\n\n"
    raise ValueError(f"unknown comment style: {style}")


def normalize_license_text(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        line = re.sub(r"^(#|//)\s?", "", line)
        line = re.sub(r"^/\*\s?", "", line)
        line = re.sub(r"^\*\s?", "", line)
        line = re.sub(r"\s?\*/$", "", line)
        cleaned_lines.append(line.strip())
    return re.sub(r"\s+", " ", "\n".join(cleaned_lines)).strip()


def split_preserved_prefix(text: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    index = 0
    if lines and lines[0].startswith("#!"):
        index = 1
    if index < len(lines) and re.match(r"#.*coding[:=]\s*[-\w.]+", lines[index]):
        index += 1
    return "".join(lines[:index]), "".join(lines[index:])


def has_license_header(file_text: str, license_text: str, scan_lines: int = 80) -> bool:
    _, body = split_preserved_prefix(file_text)
    head = "\n".join(body.splitlines()[:scan_lines])
    return normalize_license_text(license_text) in normalize_license_text(head)
