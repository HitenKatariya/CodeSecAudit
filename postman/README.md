# CodeSecAudit AI — Postman API Test Suite

This directory contains the complete end-to-end Postman API collection and environment files for **CodeSecAudit AI**, covering all services in the architecture:
- **Main Server** (FastAPI Core Security Orchestrator)
- **RAG Server** (OWASP Vector Search & Embedding Microservice)
- **Client Next.js Web Proxy** (Runtime App Router Proxy)

---

## 📁 Files in this Directory

| File | Description |
|---|---|
| [`CodeSecAudit_AI.postman_collection.json`](file:///home/omchoksi/workspace/CodeSecurityAuditAgent/postman/CodeSecAudit_AI.postman_collection.json) | Full Postman Collection (v2.1.0) containing 11 folders and 30+ automated requests. |
| [`CodeSecAudit_Local.postman_environment.json`](file:///home/omchoksi/workspace/CodeSecurityAuditAgent/postman/CodeSecAudit_Local.postman_environment.json) | Environment config pointing to local Docker (`localhost:8000`, `localhost:8010`, `localhost:3000`). |
| [`CodeSecAudit_Render.postman_environment.json`](file:///home/omchoksi/workspace/CodeSecurityAuditAgent/postman/CodeSecAudit_Render.postman_environment.json) | Environment config pointing to Render Cloud deployments. |

---

## ⚡ Zero-Manual Effort Features

1. **Automatic GitHub Webhook Signing**:
   - The webhook test contains a pre-request JavaScript script using Postman's built-in `CryptoJS.HmacSHA256`.
   - It hashes the request body with `github_webhook_secret` and dynamically injects `X-Hub-Signature-256: sha256=<hash>` and a fresh `X-GitHub-Delivery` GUID. You never have to calculate HMAC hashes manually.
2. **Dynamic ID Propagation & Chaining**:
   - Running `GET /v1/repositories` automatically saves `repo_id`.
   - Running `POST /v1/reviews` automatically captures the returned `job_id` into `test_job_id`.
   - Running `GET /v1/reviews` automatically captures the first review into `review_id`.
   - Running `GET /v1/findings` automatically captures the first finding into `finding_id`.
   - Subsequent detail endpoints (`GET /v1/reviews/{{review_id}}`, `GET /v1/findings/{{finding_id}}`) use these variables without manual copy-pasting.
3. **Session Authentication via Cookie**:
   - All authenticated requests include `Cookie: codesec_session={{codesec_session}}`.
   - Pre-configured with the default test session (`test-session-admin`) or dynamically updateable with an OAuth session.
4. **Automated Test Assertions**:
   - Every single endpoint has built-in JavaScript assertions testing status codes (200, 202, 401, 302, etc.), schema validity, and payload properties.

---

## 🚀 Quickstart Guide

### Option 1: Import into Postman App

1. Open **Postman**.
2. Click **Import** (top left).
3. Drag and drop the following files:
   - `postman/CodeSecAudit_AI.postman_collection.json`
   - `postman/CodeSecAudit_Local.postman_environment.json`
   - `postman/CodeSecAudit_Render.postman_environment.json`
4. In the top right environment dropdown, select **CodeSecAudit AI - Local Docker Environment** (or **Render Cloud**).
5. Run requests one-by-one or click **Run collection** to run the entire suite in sequence!

---

### Option 2: Run via CLI (Newman)

You can run the entire collection headlessly from your terminal using Newman:

```bash
# Run against local environment
npx newman run postman/CodeSecAudit_AI.postman_collection.json \
  -e postman/CodeSecAudit_Local.postman_environment.json

# Run against Render cloud deployment
npx newman run postman/CodeSecAudit_AI.postman_collection.json \
  -e postman/CodeSecAudit_Render.postman_environment.json
```

---

## 📂 Collection Structure & Endpoints

### 01 - Health & System Discovery
- `GET {{main_url}}/` — Main Server Root API Catalog
- `GET {{main_url}}/health/live` — Main Server Liveness Probe
- `GET {{main_url}}/health/ready` — Main Server Readiness Probe (PostgreSQL, Redis, RAG)
- `GET {{main_url}}/version` — Version and Git SHA

### 02 - Authentication & Sessions
- `GET {{main_url}}/v1/auth/github/start` — Initiate GitHub OAuth with PKCE
- `GET {{main_url}}/v1/auth/github/callback` — OAuth Callback Guard (400/422 validation)
- `GET {{main_url}}/v1/auth/me` — Current Authenticated User & Org Profile
- `POST {{main_url}}/v1/auth/logout` — Terminate Active Session

### 03 - Repositories Management
- `GET {{main_url}}/v1/repositories` — List monitored repositories with security scores
- `GET {{main_url}}/v1/repositories/{{repo_id}}` — Get repository detail and open issue counts

### 04 - Security Policies
- `GET {{main_url}}/v1/policies` — Get organization PR gating policy
- `PUT {{main_url}}/v1/policies` — Update gating policy (min score, block thresholds)

### 05 - Review Orchestration & Jobs
- `POST {{main_url}}/v1/reviews` (Vulnerabilities) — Enqueue code with SQLi & Command Injection
- `POST {{main_url}}/v1/reviews` (Clean) — Enqueue secure code (verdict APPROVE)
- `POST {{main_url}}/v1/reviews` (Suppressed) — Test `codesec-ignore-next-line` directive
- `GET {{main_url}}/v1/reviews` — List paginated review history
- `GET {{main_url}}/v1/reviews/{{review_id}}` — Get review detail with all findings

### 06 - Security Findings Triage
- `GET {{main_url}}/v1/findings` — List all open findings
- `GET {{main_url}}/v1/findings?severity=critical` — Filter findings by critical severity
- `GET {{main_url}}/v1/findings?cwe_id=CWE-89` — Filter findings by CWE-89
- `GET {{main_url}}/v1/findings/{{finding_id}}` — Get finding detail, attack scenario & fix

### 07 - Team Management
- `GET {{main_url}}/v1/team` — List organization team members and roles

### 08 - GitHub Webhooks & Signatures
- `POST {{main_url}}/v1/webhooks/github` (Valid) — Auto HMAC-SHA256 signed PR webhook
- `POST {{main_url}}/v1/webhooks/github` (Invalid) — Guard test rejecting invalid signatures (401)

### 09 - Admin Log Streaming & Auditing
- `GET {{main_url}}/main-server-logs` — Tail Redis stream logs for main-server
- `GET {{main_url}}/client-server-logs` — Tail Redis stream logs for client Next.js
- `GET {{main_url}}/rag-server-logs` — Tail Redis stream logs for rag-server

### 10 - RAG Knowledge Base & Embeddings
- `GET {{rag_url}}/health/live` — RAG microservice liveness
- `GET {{rag_url}}/health/ready` — Qdrant & Embedding model readiness
- `GET {{rag_url}}/version` — RAG corpus version and embedding model
- `POST {{rag_url}}/v1/search` (SQLi) — Search OWASP guidance for SQL injection
- `POST {{rag_url}}/v1/search` (Command Injection) — Search OWASP guidance for command injection
- `POST {{rag_url}}/v1/search` (No Token) — Verify 401 Unauthorized guard
- `GET {{rag_url}}/v1/index/status` — Get Qdrant index document count
- `POST {{rag_url}}/v1/index` — Trigger batch corpus indexing

### 11 - Client Next.js Proxy & Frontend Health
- `GET {{client_url}}/health` — Next.js health check
- `GET {{client_url}}/version` — Next.js version check
- `GET {{client_url}}/api/auth/me` — Runtime API Proxy test forwarding to main-server
- `GET {{client_url}}/api/reviews` — Runtime API Proxy test for reviews

### 12 - Session Teardown & Logout
- `POST {{main_url}}/v1/auth/logout` — Terminate Active Session

---

## 🧪 Verified Test Results (Newman CLI)

The entire suite was executed end-to-end against the local live Docker stack:
```
┌─────────────────────────┬────────────────────┬───────────────────┐
│                         │           executed │            failed │
├─────────────────────────┼────────────────────┼───────────────────┤
│              iterations │                  1 │                 0 │
├─────────────────────────┼────────────────────┼───────────────────┤
│                requests │                 39 │                 0 │
├─────────────────────────┼────────────────────┼───────────────────┤
│            test-scripts │                 39 │                 0 │
├─────────────────────────┼────────────────────┼───────────────────┤
│      prerequest-scripts │                  1 │                 0 │
├─────────────────────────┼────────────────────┼───────────────────┤
│              assertions │                 55 │                 0 │
└─────────────────────────┴────────────────────┴───────────────────┘
```
**100% Success Rate (0 Failures, 55 Assertions Passed)** across Main Server, RAG Vector microservice, and Next.js Client Proxy.

---

## 🔑 Environment Variables Reference

| Variable | Local Default | Render Default | Purpose |
|---|---|---|---|
| `main_url` | `http://localhost:8000` | `https://codesec-api.onrender.com` | Base URL for FastAPI main server |
| `rag_url` | `http://localhost:8010` | `https://codesec-rag.onrender.com` | Base URL for RAG microservice |
| `client_url` | `http://localhost:3000` | `https://codesec-website.onrender.com` | Base URL for Next.js web application |
| `codesec_session` | `test-session-admin` | `test-session-admin` | HttpOnly cookie value for authenticated endpoints |
| `rag_service_token` | `dev_rag_service_token_secret` | `dev_rag_service_token_secret` | Internal bearer token for RAG microservice |
| `github_webhook_secret` | `dev_github_webhook_secret_key` | `dev_github_webhook_secret_key` | Secret used to calculate HMAC-SHA256 signature |
| `repo_id` | `repo-1` | `repo-1` | Active repository ID for review & detail requests |
| `review_id` | `rev-demo-101` | `rev-demo-101` | Active review ID for detail requests |
| `finding_id` | `fin-demo-1` | `fin-demo-1` | Active finding ID for detail requests |
| `test_job_id` | *(auto-populated)* | *(auto-populated)* | Stores ID from `POST /v1/reviews` |
| `webhook_signature` | *(auto-populated)* | *(auto-populated)* | Auto-calculated by pre-request script |
