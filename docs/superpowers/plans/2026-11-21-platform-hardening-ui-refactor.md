# CodeSecAudit AI — Platform Hardening, Review Intelligence & UI Overhaul Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform CodeSecAudit AI into an enterprise-grade PR security gate with deep repository context, false-positive elimination through strict CWE/OWASP ASVS grounding, a streamlined team invitation lifecycle, machine-readable coding-agent remediation contracts, and a deduplicated Next.js UI validated end-to-end with Playwright.

**Architecture:**
- **Backend / Review Worker**: Hybrid AST-deterministic + LLM (`pr_agent`) + Qdrant RAG pipeline enhanced with surrounding diff context analysis and strict CWE/ASVS citation.
- **Team & Permissions**: Database-backed `OrganizationInvitation` with secure token mailers, role-based access, and shared organization review visibility without per-developer app re-installation.
- **Coding Agent Contract**: SARIF 2.1.0 and machine-readable remediation JSON emitted in PR comments so external agents (Claude, Copilot, Aider) can auto-commit fixes.
- **Frontend (Next.js 14)**: Clean tab architecture eliminating redundancy between Dashboard, PRs, Findings, Trends, and Reports; verified via automated Playwright test suites.

**Tech Stack:** FastAPI, Next.js 14 (App Router), PostgreSQL 16, Redis 7, Qdrant, SQLAlchemy (Asyncpg), Playwright.

---

## 1. Architectural Q&A & Technical Reality

### Q1: Does each review process have repository context? Do we use an LLM?
* **Repository Context**:
  * *Current*: The review worker (`app/jobs/worker.py`) fetches the **unified git diff** via GitHub's API (`fetch_pull_request_diff`). It parses added lines and scans them. It does **not** clone the full repository or build whole-repo AST symbol tables.
  * *Target*: Enrich the review payload with **surrounding hunk context** (up to 50 lines before/after changed lines) and import statements from the file to detect whether input is sanitized or parameterized by upstream code.
* **LLM Usage (Dual Engine Architecture)**:
  * *Yes, conditionally*:
    1. **Deterministic Rule Engine** (`app/reviews/engine.py`): Always runs instantly (0ms latency), scanning for CWE-78, CWE-89, CWE-94, CWE-328, CWE-798, CWE-22, CWE-918.
    2. **LLM Engine** (`app/reviews/pr_agent_client.py`): When `PR_AGENT_REVIEW_ENABLED=true` and an API key is configured, it invokes `PRReviewer` with prompt instructions prioritizing deep logic bugs, authorization bypasses, and data validation gaps.
    3. **Semantic RAG Engine** (`app/reviews/rag_client.py`): For every detected finding, it queries Qdrant vector store (2,833 OWASP Cheat Sheets and CWE entries) for remediation guidance.

---

### Q2: How does team member invitation work? Do team members need to reinstall the GitHub App?
* **Current State**: The team page (`client/src/app/team/page.tsx`) currently uses a client-side mock modal. The backend only has `GET /v1/team`.
* **Target Production Workflow**:
  1. **Owner Invites**: Account owner enters coworker email and assigns role (`Admin`, `Security Lead`, `Developer`, `Viewer`).
  2. **Tokenized Invite Email**: Backend generates a secure cryptographically random token (`OrganizationInvitation` record) and dispatches an invitation email with an acceptance link (`/invite/accept?token=...`).
  3. **No GitHub App Re-installation Needed**:
     * GitHub Apps are installed on the **GitHub Organization or Repository**, **not** on individual user profiles.
     * When the team member accepts the invite and logs in, they are bound to the CodeSec Organization.
     * They immediately inherit access to all repositories, PR audit trails, and security reports under that organization.
  4. **Shared PR Reviews**: All reviews on organization repositories are visible to all team members according to their role.

---

### Q3: On Open Source Repos, does every person's PR get audited? Can coding agents consume the report?
* **Open Source PR Auditing**: **YES!**
  * When CodeSecAudit AI is installed on a public repository, GitHub fires webhook events (`pull_request.opened`, `synchronize`) for **every** PR, including fork PRs submitted by outside open-source contributors.
  * The GitHub App creates check runs and posts comments on any contributor's PR.
* **Coding Agent Remediation Format**:
  * Instead of monolithic comments that coding agents struggle to parse, we introduce a standardized machine-readable JSON block in every review comment:
    ```markdown
    <!-- CODESEC_AGENT_PAYLOAD_START
    {
      "schema_version": "1.0.0",
      "verdict": "BLOCK",
      "cvss_score": 9.89,
      "findings": [
        {
          "cwe_id": "CWE-89",
          "file_path": "routes/charge.py",
          "line_number": 42,
          "patch_suggested": "query = ...\ndb.execute(query, {'id': account_id})"
        }
      ]
    }
    CODESEC_AGENT_PAYLOAD_END -->
    ```
  * External coding agents (Claude Code, Aider, Copilot Workspace) can regex-extract this payload to automatically open automated fix pull requests.

---

### Q4: Proper Citations (CWE & OWASP Benchmark) to Stop False Positives
* **Strict Grounding Specification**:
  Every finding must include:
  1. **CWE Citation**: e.g., `[CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html)`
  2. **OWASP Benchmark / ASVS Citation**: e.g., `OWASP ASVS v4.0.3 §5.3.4 (Parameterized Queries Required)`
  3. **CVSS v3.1 Vector**: e.g., `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H (9.8)`
* **False-Positive Elimination Rules**:
  * **Sanitization Detection**: If diff hunk contains parameters (`?`, `%s`, `:param`), prepared statements (`execute(sql, (param,))`), or escape functions, suppress the finding.
  * **Inline Suppression**: Support `# codesec-ignore: CWE-89` and `# codesec-ignore-next-line: CWE-89`.

---

## 2. UI Audit & Tab Consolidation Plan

### Redundancy Analysis & New Clean Information Architecture:
1. **Dashboard (`/dashboard`)**: Executive summary: Monitored Repos count, Active PR Gates, Critical Vulnerability Count, Recent PR Stream, and System Status.
2. **Pull Requests (`/pull-requests`)**: Dedicated PR review gate stream with filtering by Verdict (`Blocked`, `Passed`, `Scanning`), repository, and date.
3. **Findings (`/findings`)**: Granular vulnerability triage table with filter by CWE, Severity (`Critical`, `High`, `Medium`), File Path, and status (`Active`, `Suppressed`, `Remediated`).
4. **Security Trends (`/trends`)**: Consolidated analytics with CVSS distribution charts, MTTR timelines, and gate pass rate over time (absorbs redundant metrics from `/reports`).
5. **Reports & Exports (`/reports`)**: Dedicated Compliance & Audit Export Center (generate PDF/CSV reports, OWASP ASVS compliance attestations).
6. **Team & Permissions (`/team`)**: Real team management with invitations, member roles, and GitHub App permission sharing status.
7. **Policies (`/policies`)**: Gate blocking rules (e.g. block on Critical CVSS >= 7.0, allow on warnings, require 2 reviewer approvals).
8. **Settings (`/settings`)**: GitHub App connection, Webhook status, API tokens, and account management.

---

## 3. Subagent Execution Breakdown (Phased Implementation)

### Phase 1: Review Intelligence & False Positive Elimination (Subagents 1-3)
- [ ] **Subagent 1**: Upgrade `main-server/app/reviews/engine.py` with AST context checking (parameterization & sanitization detection) to discard false positives.
- [ ] **Subagent 2**: Update `main-server/app/reviews/report_formatter.py` to embed strict CWE MITRE links, OWASP ASVS benchmarks, and the machine-readable `CODESEC_AGENT_PAYLOAD` for coding agents.
- [ ] **Subagent 3**: Add test fixtures in `main-server/tests/test_false_positives.py` verifying clean queries with parameters are NOT flagged.

### Phase 2: Team Invitation Backend & Email Workflow (Subagents 4-6)
- [ ] **Subagent 4**: Create `OrganizationInvitation` model in `main-server/app/db/models/organization.py` with alembic migration.
- [ ] **Subagent 5**: Implement `POST /v1/team/invite` and `DELETE /v1/team/invite/{id}` in `main-server/app/api/team.py`.
- [ ] **Subagent 6**: Add invitation email generation in `main-server/app/core/mailer.py` with acceptance token flow.

### Phase 3: UI Redundancy Elimination & Refinement (Subagents 7-10)
- [ ] **Subagent 7**: Update `Sidebar.tsx` and consolidate navigation groups to ensure each tab has a unique, non-overlapping purpose.
- [ ] **Subagent 8**: Refactor `client/src/app/team/page.tsx` to connect to real backend `POST /v1/team/invite` with loading and error states.
- [ ] **Subagent 9**: Polish `client/src/app/reports/page.tsx` and `client/src/app/trends/page.tsx` so Reports focuses on CSV/PDF compliance export while Trends focuses on interactive risk visualization.
- [ ] **Subagent 10**: Ensure all UI buttons, tabs, and dark/light mode themes adhere strictly to the no-emoji rule.

### Phase 4: Playwright End-to-End Test Suite (Subagents 11-13)
- [ ] **Subagent 11**: Install and configure Playwright in `client/playwright.config.ts`.
- [ ] **Subagent 12**: Write automated Playwright test suite (`client/e2e/navigation.spec.ts`) validating every tab loads without console errors or broken images.
- [ ] **Subagent 13**: Write automated Playwright test suite (`client/e2e/team_and_reviews.spec.ts`) validating Team invite modal, PR list filtering, and screenshot lightbox modal.
