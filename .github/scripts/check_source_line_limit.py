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
}
EXCLUDE_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
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


def check_files(root: Path) -> tuple[int, list[tuple[Path, int]]]:
    checked = 0
    violations: list[tuple[Path, int]] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or should_skip(path):
            continue

        checked += 1
        try:
            line_count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            if line_count > MAX_LINES:
                violations.append((path, line_count))
        except Exception as e:
            print(f"Error reading {path}: {e}", file=sys.stderr)

    return checked, violations


def main() -> None:
    root = find_repo_root()
    checked, violations = check_files(root)

    print(f"Checked {checked} source files for max {MAX_LINES} lines rule.")

    if violations:
        print(f"\nFAILURE: {len(violations)} file(s) exceeded {MAX_LINES} lines:")
        for path, count in violations:
            rel = path.relative_to(root)
            print(f"  - {rel}: {count} lines (> {MAX_LINES})")
        sys.exit(1)

    print("All checked files adhere to the line limit.")


if __name__ == "__main__":
    main()
