"""Git patch parser to identify lines added in PR diff."""

import re
from typing import Optional


def parse_patch_added_lines(patch: str) -> set[int]:
    added_lines: set[int] = set()
    current_line = 0

    for line in patch.splitlines():
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                current_line = int(match.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            if current_line > 0:
                added_lines.add(current_line)
                current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            continue
        elif line.startswith(" ") or line == "" or line.startswith("\\"):
            if current_line > 0:
                current_line += 1

    return added_lines


def extract_added_lines(patch: str) -> list[tuple[int, str]]:
    """Return (line_number, content) pairs for every added line in a unified diff."""
    added: list[tuple[int, str]] = []
    current_line = 0

    for line in patch.splitlines():
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                current_line = int(match.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            if current_line > 0:
                added.append((current_line, line[1:]))
                current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            continue
        elif line.startswith(" ") or line == "" or line.startswith("\\"):
            if current_line > 0:
                current_line += 1

    return added


def split_diff_by_file(diff_text: str) -> dict[str, str]:
    """Split a multi-file unified diff into {file_path: per-file patch} chunks."""
    files: dict[str, str] = {}
    current_path: Optional[str] = None
    current_lines: list[str] = []

    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            if current_path and current_lines:
                files[current_path] = "".join(current_lines)
            current_path = None
            current_lines = [line]
        elif line.startswith("+++ b/"):
            current_path = line[len("+++ b/"):].strip()
            current_lines.append(line)
        else:
            current_lines.append(line)

    if current_path and current_lines:
        files[current_path] = "".join(current_lines)

    return files
