"""Semantic diff parser and change breakdown analyzer."""

from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class FileDiffSummary:
    path: str
    status: str  # "added", "modified", "deleted"
    additions: int = 0
    deletions: int = 0
    added_symbols: list[str] = field(default_factory=list)
    removed_symbols: list[str] = field(default_factory=list)
    what_added: list[str] = field(default_factory=list)
    what_changed: list[str] = field(default_factory=list)
    what_removed: list[str] = field(default_factory=list)


@dataclass
class DiffAnalysis:
    total_files: int
    total_additions: int
    total_deletions: int
    files: list[FileDiffSummary]
    overall_added: list[str]
    overall_changed: list[str]
    overall_removed: list[str]


_DEF_PATTERN = re.compile(r"^\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\(")
_CLASS_PATTERN = re.compile(r"^\s*class\s+([a-zA-Z0-9_]+)")
_ROUTE_PATTERN = re.compile(r"^\s*@(?:router|app)\.(get|post|put|delete|patch)\([\"']([^\"']+)")
_IMPORT_PATTERN = re.compile(r"^\s*(?:from\s+[\w\.]+\s+import|import)\s+([a-zA-Z0-9_,\s]+)")


def _extract_symbols(lines: list[str]) -> list[str]:
    symbols: list[str] = []
    for line in lines:
        m_route = _ROUTE_PATTERN.search(line)
        if m_route:
            symbols.append(f"Route: {m_route.group(1).upper()} {m_route.group(2)}")
            continue
        m_def = _DEF_PATTERN.search(line)
        if m_def:
            symbols.append(f"Function: `{m_def.group(1)}()`")
            continue
        m_class = _CLASS_PATTERN.search(line)
        if m_class:
            symbols.append(f"Class: `{m_class.group(1)}`")
            continue
    return symbols


def _categorize_changes(file_patch: str, status: str) -> tuple[int, int, list[str], list[str], list[str], list[str], list[str]]:
    added_lines: list[str] = []
    removed_lines: list[str] = []

    for line in file_patch.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed_lines.append(line[1:])

    added_syms = _extract_symbols(added_lines)
    removed_syms = _extract_symbols(removed_lines)

    what_added: list[str] = []
    what_removed: list[str] = []
    what_changed: list[str] = []

    if status == "added":
        what_added.append(f"Created new source module with {len(added_lines)} lines.")
        for sym in added_syms:
            what_added.append(f"Introduced {sym}.")
    elif status == "deleted":
        what_removed.append(f"Removed source file ({len(removed_lines)} lines deleted).")
        for sym in removed_syms:
            what_removed.append(f"Deleted {sym}.")
    else:
        for sym in added_syms:
            if sym not in removed_syms:
                what_added.append(f"Added {sym}.")
            else:
                what_changed.append(f"Updated implementation of {sym}.")
        for sym in removed_syms:
            if sym not in added_syms:
                what_removed.append(f"Removed {sym}.")

        if not added_syms and not removed_syms:
            if added_lines and removed_lines:
                what_changed.append(f"Updated internal logic/configuration (+{len(added_lines)} / -{len(removed_lines)}).")
            elif added_lines:
                what_added.append(f"Added inline logic statements (+{len(added_lines)} lines).")
            elif removed_lines:
                what_removed.append(f"Removed deprecated statements (-{len(removed_lines)} lines).")

    return len(added_lines), len(removed_lines), added_syms, removed_syms, what_added, what_changed, what_removed


def analyze_diff(diff_text: str) -> DiffAnalysis:
    """Analyze unified diff to extract modified files, line counts, and semantic changes."""
    files_map: dict[str, list[str]] = {}
    file_statuses: dict[str, str] = {}
    current_path: str | None = None
    is_new = False
    is_deleted = False

    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            current_path = None
            is_new = False
            is_deleted = False
        elif line.startswith("new file mode"):
            is_new = True
        elif line.startswith("deleted file mode"):
            is_deleted = True
        elif line.startswith("+++ b/"):
            current_path = line[len("+++ b/"):].strip()
            status = "added" if is_new else ("deleted" if is_deleted else "modified")
            files_map[current_path] = []
            file_statuses[current_path] = status
        elif line.startswith("--- a/") and is_deleted and not current_path:
            current_path = line[len("--- a/"):].strip()
            files_map[current_path] = []
            file_statuses[current_path] = "deleted"
        elif current_path:
            files_map[current_path].append(line)

    file_summaries: list[FileDiffSummary] = []
    overall_added: list[str] = []
    overall_changed: list[str] = []
    overall_removed: list[str] = []
    total_adds = 0
    total_dels = 0

    for path, lines in files_map.items():
        patch_str = "".join(lines)
        status = file_statuses.get(path, "modified")
        adds, dels, a_syms, r_syms, w_add, w_chg, w_rem = _categorize_changes(patch_str, status)

        total_adds += adds
        total_dels += dels

        summary = FileDiffSummary(
            path=path,
            status=status,
            additions=adds,
            deletions=dels,
            added_symbols=a_syms,
            removed_symbols=r_syms,
            what_added=w_add,
            what_changed=w_chg,
            what_removed=w_rem,
        )
        file_summaries.append(summary)

        for item in w_add:
            overall_added.append(f"`{path}`: {item}")
        for item in w_chg:
            overall_changed.append(f"`{path}`: {item}")
        for item in w_rem:
            overall_removed.append(f"`{path}`: {item}")

    return DiffAnalysis(
        total_files=len(file_summaries),
        total_additions=total_adds,
        total_deletions=total_dels,
        files=file_summaries,
        overall_added=overall_added,
        overall_changed=overall_changed,
        overall_removed=overall_removed,
    )
