#!/usr/bin/env python3
"""Prepend a selected license notice to source/text files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from license_header_utils import comment_license, detect_style, has_license_header, load_license, split_preserved_prefix


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="Files to update")
    parser.add_argument("--license", required=True, type=Path, help="License text file")
    parser.add_argument("--year", help="Value for {year} placeholders")
    parser.add_argument("--owner", help="Value for {owner} placeholders")
    parser.add_argument("--style", choices=["auto", "hash", "line", "block"], default="auto")
    parser.add_argument("--check", action="store_true", help="Report intended changes without writing")
    return parser.parse_args()


def update_file(path: Path, license_text: str, requested_style: str, check: bool) -> str:
    text = path.read_text(encoding="utf-8")
    if has_license_header(text, license_text):
        return "unchanged"
    style = detect_style(path, requested_style)
    prefix, body = split_preserved_prefix(text)
    updated = prefix + comment_license(license_text, style) + body.lstrip("\n")
    if not check:
        path.write_text(updated, encoding="utf-8")
    return "would-update" if check else "updated"


def main() -> int:
    args = parse_args()
    license_text = load_license(args.license, year=args.year, owner=args.owner)
    failed = False
    for path in args.files:
        try:
            status = update_file(path, license_text, args.style, args.check)
        except UnicodeDecodeError:
            status = "skipped-binary-or-non-utf8"
        except OSError as exc:
            failed = True
            status = f"error:{exc}"
        print(f"{status}\t{path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
