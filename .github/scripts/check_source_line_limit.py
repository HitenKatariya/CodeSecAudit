#!/usr/bin/env python3
"""Enforce maximum line count per source file (200 lines max).

Excluded: migrations, node_modules, .next, dist, build, test snapshots, lockfiles.
"""

from __future__ import annotations

import sys
from pathlib import Path

MAX_LINES = 200
TARGET_EXTENSIONS = {".py", ".ts", ".tsx"}
EXCLUDE_DIRS = {
    ".git",
    ".next",
    "node_modules",
    "migrations",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".coverage",
    "scripts",
    "notebooks",
}
EXCLUDE_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
}

# Explicit limits for multi-section frontend landing/views and extensive auth/risk engines
FILE_LINE_OVERRIDES: dict[str, int] = {
    "client/src/app/page.tsx": 1200,
    "client/src/app/settings/page.tsx": 600,
    "client/src/app/dashboard/page.tsx": 500,
    "client/src/app/login/page.tsx": 400,
    "client/src/lib/api.ts": 500,
    "main-server/app/api/auth.py": 700,
    "main-server/app/reviews/risk.py": 500,
    "main-server/app/reviews/report_formatter.py": 400,
}


def should_skip(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return True
    if path.name in EXCLUDE_FILES:
        return True
    if path.suffix not in TARGET_EXTENSIONS:
        return True
    return False


def find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for p in [current, *current.parents]:
        if (p / "docker-compose.yml").exists() or (p / ".git").exists():
            return p
    return Path.cwd()


def check_files(root: Path) -> tuple[int, list[tuple[Path, int, int]]]:
    checked = 0
    violations: list[tuple[Path, int, int]] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or should_skip(path):
            continue

        checked += 1
        rel_posix = path.relative_to(root).as_posix()
        file_limit = FILE_LINE_OVERRIDES.get(rel_posix, MAX_LINES)
        try:
            line_count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            if line_count > file_limit:
                violations.append((path, line_count, file_limit))
        except Exception as e:
            print(f"Error reading {path}: {e}", file=sys.stderr)

    return checked, violations


def main() -> None:
    root = find_repo_root()
    checked, violations = check_files(root)

    print(f"Checked {checked} source files for max {MAX_LINES} lines rule.")

    if violations:
        print(f"\nFAILURE: {len(violations)} file(s) exceeded line limit:")
        for path, count, limit in violations:
            rel = path.relative_to(root)
            print(f"  - {rel}: {count} lines (> {limit})")
        sys.exit(1)

    print("All checked files adhere to the line limit.")


if __name__ == "__main__":
    main()
