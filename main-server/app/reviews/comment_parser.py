"""Parsers for normalizing CodeSecAudit GitHub PR comment payloads and markdown reports."""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from app.reviews.risk import calculate_risk_score, decide_verdict, get_suggested_fix

_SEVERITY_WORD = re.compile(r"(CRITICAL|HIGH|MEDIUM|LOW)", re.IGNORECASE)
_CWE_RE = re.compile(r"CWE-\d+", re.IGNORECASE)
_VERDICT_LINE_RE = re.compile(r"Verdict:\*\*[^\n]*?(REQUEST[_\s]CHANGES|WARNING|APPROVE)", re.IGNORECASE)


def _extract_payload_json(body: str) -> Optional[dict[str, Any]]:
    start, end = "CODESEC_AGENT_PAYLOAD_START", "CODESEC_AGENT_PAYLOAD_END"
    if start not in body or end not in body:
        return None
    try:
        data = json.loads(body.split(start, 1)[1].split(end, 1)[0].strip())
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _parse_markdown_findings(body: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line in body.splitlines():
        if not line.strip().startswith("|") or "CWE-" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        sev_m, cwe_m = _SEVERITY_WORD.search(cells[0]), _CWE_RE.search(cells[1])
        loc = cells[3].strip("` ")
        file_path, line_no = (loc.rsplit(":", 1)[0], loc.rsplit(":", 1)[1]) if ":" in loc else (loc, "0")
        cwe_id = cwe_m.group(0).upper() if cwe_m else "CWE-20"
        findings.append({
            "cwe_id": cwe_id,
            "severity": sev_m.group(1).lower() if sev_m else "medium",
            "title": (cells[4].replace("**", "").strip() or f"{cwe_id} Security Issue")[:255],
            "file_path": (file_path or "unknown")[:512],
            "line_number": int(line_no) if line_no.isdigit() else 0,
            "code_snippet": "",
            "suggested_fix": get_suggested_fix(cwe_id),
        })
    return findings


def _normalize_finding(raw: dict[str, Any]) -> dict[str, Any]:
    cwe = str(raw.get("cwe_id") or "CWE-20").upper()[:32]
    fix = raw.get("patch_suggested") or raw.get("suggested_fix") or raw.get("fix") or get_suggested_fix(cwe)
    try:
        line_no = int(raw.get("line_number") or raw.get("line") or 0)
    except (TypeError, ValueError):
        line_no = 0
    return {
        "cwe_id": cwe,
        "severity": str(raw.get("severity") or "medium").lower()[:32],
        "title": str(raw.get("title") or f"{cwe} Security Issue")[:255],
        "file_path": str(raw.get("file_path") or raw.get("file") or "unknown")[:512],
        "line_number": line_no,
        "code_snippet": str(raw.get("code_snippet") or raw.get("snippet") or "")[:300],
        "suggested_fix": str(fix)[:2000],
    }


def parse_bot_comment(body: str, fallback_sha: str) -> dict[str, Any]:
    """Normalize verdict, CVSS score, commit SHA, and findings from a CodeSecAudit PR comment."""
    sha_m = re.search(r"Target Commit:\*\*\s*`([0-9a-fA-F]+)`", body)
    commit_sha = sha_m.group(1) if sha_m else fallback_sha
    payload = _extract_payload_json(body)
    if payload is None:
        findings = _parse_markdown_findings(body)
        score_m = re.search(r"CVSS Security Risk Score:\*\*\s*`([0-9]+(?:\.[0-9]+)?)\s*/\s*10", body)
        risk_score = float(score_m.group(1)) if score_m else calculate_risk_score(findings)
        verdict_m = _VERDICT_LINE_RE.search(body)
        if verdict_m:
            verdict = verdict_m.group(1).upper().replace(" ", "_")
        elif "**REQUEST CHANGES**" in body:
            verdict = "REQUEST_CHANGES"
        elif "**WARNING**" in body:
            verdict = "WARNING"
        elif "**APPROVE**" in body:
            verdict = "APPROVE"
        else:
            verdict = decide_verdict(risk_score, findings=findings)
        return {"verdict": verdict, "risk_score": risk_score, "commit_sha": commit_sha, "findings": findings}

    findings = [_normalize_finding(f) for f in (payload.get("findings") or []) if isinstance(f, dict)]
    raw_score = payload.get("cvss_score")
    risk_score = float(raw_score) if raw_score is not None else calculate_risk_score(findings)
    return {
        "verdict": str(payload.get("verdict") or decide_verdict(risk_score, findings=findings)),
        "risk_score": risk_score,
        "commit_sha": commit_sha,
        "findings": findings,
    }
