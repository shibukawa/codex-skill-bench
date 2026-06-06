---
name: license-header
description: Add, update, or audit source file license headers using bundled reference license texts. Use when Codex needs to prepend a license notice to text/source files, choose a reusable license template from references/, or list project files that are missing a required license header as JSON Lines.
---

# License Header

## Overview

Use this skill to place a selected license notice at the start of source files and to audit a project for files that are missing that notice. Keep the canonical license text in `references/`; use the scripts for deterministic insertion and JSONL reporting.

## Choose a License

Read only the needed file from `references/`:

- `mit.txt` for an MIT license notice.
- `apache-2.0.txt` for an Apache License 2.0 notice.
- `proprietary.txt` for an all-rights-reserved proprietary notice.

Replace `{year}` and `{owner}` before insertion when the selected reference contains placeholders. If the user does not provide values, infer the current year and ask only when the owner cannot be reasonably inferred from repository/package metadata.

## Add a Header

Use `scripts/prepend_license.py` to insert the selected notice at the top of files. It preserves Unix shebang and Python encoding lines, selects a comment style from file extension, and skips files that already contain the normalized license text near the top.

Examples:

```bash
python3 scripts/prepend_license.py --license references/mit.txt --year 2026 --owner "Example Corp" src/main.py src/app.ts
python3 scripts/prepend_license.py --license references/apache-2.0.txt --style block include/example.h
```

For unsupported extensions, pass `--style line`, `--style hash`, or `--style block`.

## Audit Missing Headers

Use `scripts/list_missing_license.py` to emit one JSON object per project file that is missing the selected license. The output is JSONL on stdout.

Examples:

```bash
python3 scripts/list_missing_license.py /path/to/project --license references/mit.txt --year 2026 --owner "Example Corp"
python3 scripts/list_missing_license.py . --license references/proprietary.txt --extensions .py,.js,.ts
```

Each JSONL object includes:

- `path`: path relative to the audited project root.
- `reason`: why the file is reported, usually `missing-license`.
- `style`: detected or requested comment style.

The audit script skips common generated, dependency, VCS, binary, and media paths by default. Add `--include-hidden` when hidden project files should be checked.
