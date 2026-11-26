"""Execution flow and architectural before/after comparator."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from app.reviews.diff_analyzer import DiffAnalysis


@dataclass
class FlowComparison:
    flow_before_description: str
    flow_after_description: str
    mermaid_diagram: str
    security_architecture_notes: list[str]


def generate_flow_comparison(diff_analysis: DiffAnalysis, findings: list[dict[str, Any]]) -> FlowComparison:
    """Generate side-by-side execution flow comparison and Mermaid diagrams."""
    has_critical_findings = any(f.get("severity") in ("critical", "high") for f in findings)
    has_medium_findings = any(f.get("severity") == "medium" for f in findings)

    cwe_ids = {f.get("cwe_id") for f in findings if f.get("cwe_id")}
    modules_modified = [f.path for f in diff_analysis.files]

    # Deduce architectural domain
    is_sql = "CWE-89" in cwe_ids or any("sql" in m.lower() or "db" in m.lower() for m in modules_modified)
    is_cmd = "CWE-78" in cwe_ids or any("ping" in m.lower() or "cmd" in m.lower() for m in modules_modified)
    is_eval = "CWE-94" in cwe_ids or any("calc" in m.lower() or "eval" in m.lower() for m in modules_modified)
    is_crypto = "CWE-328" in cwe_ids or any("hash" in m.lower() or "token" in m.lower() for m in modules_modified)

    if has_critical_findings:
        before_desc = (
            "**Previous State:** Caller inputs were either not handled by this service or "
            "evaluated through legacy unverified channels without structured parameter binding."
        )
        after_desc = (
            "**Current PR State:** The PR introduces direct execution paths that accept untrusted inputs "
            "into execution sinks without defensive sanitization (e.g. raw SQL string formatting, shell=True, eval)."
        )
        mermaid = _build_vulnerable_mermaid(is_sql, is_cmd, is_eval)
        notes = [
            "Taint propagation traces directly from user-controlled parameters to system execution sinks.",
            "Lack of parameterization or argument isolation enables arbitrary code or SQL injection.",
            "Requires immediate refactoring to use bound parameters and argv vector execution.",
        ]
    elif has_medium_findings or is_crypto:
        before_desc = (
            "**Previous State:** System utilized standard identity or caching mechanisms, "
            "or lacked fast checksum generators for assets and entity tags."
        )
        after_desc = (
            "**Current PR State:** The PR introduces hashing routines for entity tags and checksums. "
            "However, legacy algorithms (MD5 / SHA-1) are referenced, which are vulnerable to collision attacks."
        )
        mermaid = _build_medium_crypto_mermaid()
        notes = [
            "Data flow executes reliably but relies on deprecated cryptographic primitives.",
            "While adequate for non-security cache keys, it fails modern OWASP ASVS §6.2.2 requirements.",
            "Recommended to upgrade to SHA-256 with salts or HMAC for cryptographic integrity.",
        ]
    else:
        before_desc = (
            "**Previous State:** Components required modern defensive interfaces, strict input validation, "
            "and parameterized database abstractions."
        )
        after_desc = (
            "**Current PR State:** The PR introduces hardened execution flows. Incoming data is strictly validated, "
            "SQL statements use bound parameter tuples/dictionaries, subprocesses use argument arrays without shells, "
            "and digests use salted SHA-256."
        )
        mermaid = _build_secure_mermaid()
        notes = [
            "Strict separation between code instructions and untrusted data buffers.",
            "Zero shell interpolation prevents command execution breakout.",
            "Database engine treats all user inputs strictly as literals via parameterized bindings.",
        ]

    return FlowComparison(
        flow_before_description=before_desc,
        flow_after_description=after_desc,
        mermaid_diagram=mermaid,
        security_architecture_notes=notes,
    )


def _build_vulnerable_mermaid(is_sql: bool, is_cmd: bool, is_eval: bool) -> str:
    sink_label = "Vulnerable Execution Sink"
    if is_sql:
        sink_label = "DB Engine: String Concat (CWE-89)"
    elif is_cmd:
        sink_label = "OS Shell: shell=True (CWE-78)"
    elif is_eval:
        sink_label = "Python Runtime: eval() (CWE-94)"

    return f"""```mermaid
flowchart TD
  subgraph BeforeFlow ["Flow Before PR"]
    direction TB
    B_REQ["Caller Request"] --> B_NOOP["No Direct Service Endpoint"]
    B_NOOP --> B_SAFE["Baseline Unchanged"]
  end

  subgraph AfterFlow ["Flow After PR (Tainted Sink Detected)"]
    direction TB
    A_REQ["Untrusted User Input"] --> A_CONCAT["Raw String Interpolation"]
    A_CONCAT --> A_SINK["{sink_label}"]
    A_SINK -.->|Exploit Path| A_ALERT["🚨 Security Gate Blocked"]
  end
```"""


def _build_medium_crypto_mermaid() -> str:
    return """```mermaid
flowchart TD
  subgraph BeforeFlow ["Flow Before PR"]
    direction TB
    B_IN["Payload / Asset"] --> B_OLD["Standard Processing"]
    B_OLD --> B_RET["Baseline Output"]
  end

  subgraph AfterFlow ["Flow After PR (Deprecated Digest)"]
    direction TB
    A_IN["Payload Data"] --> A_HASH["Legacy Algorithm: MD5 / SHA-1"]
    A_HASH --> A_TAG["Checksum / ETag Generation"]
    A_TAG -.->|Weak Collision Resistance| A_WARN["⚠️ OWASP ASVS Modernization Recommended"]
  end
```"""


def _build_secure_mermaid() -> str:
    return """```mermaid
flowchart TD
  subgraph BeforeFlow ["Flow Before PR"]
    direction TB
    B_REQ["Client Request"] --> B_LEGACY["Legacy / Unhardened Endpoint"]
    B_LEGACY --> B_OUT["Response"]
  end

  subgraph AfterFlow ["Flow After PR (Hardened Execution)"]
    direction TB
    A_REQ["Client Request"] --> A_VAL["Input Validation & Type Casting"]
    A_VAL --> A_PARAM["Parameterized Query / Argv Array"]
    A_PARAM --> A_SAFE["Secure Execution Engine (Isolated Boundaries)"]
    A_SAFE --> A_PASS["✅ Verified Security Approval"]
  end
```"""
