"""Comprehensive E2E test suite for all backend endpoints across services."""

import asyncio
import hashlib
import hmac
import json
import time
import uuid
import httpx

MAIN_URL = "http://localhost:8000"
RAG_URL = "http://localhost:8010"
RAG_TOKEN = "dev_rag_service_token_secret"
WEBHOOK_SECRET = "dev_github_webhook_secret_key"
AUTH_COOKIES = {"codesec_session": "test-session-admin"}

results: list[dict] = []

def record(endpoint: str, method: str, status: str, code: int, detail: str, duration_ms: float):
    results.append({
        "endpoint": endpoint, "method": method, "status": status,
        "code": code, "detail": detail, "duration_ms": round(duration_ms, 1)
    })
    sym = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")
    print(f"{sym} [{status}] {method:4} {endpoint:<32} HTTP {code:<3} ({duration_ms:.1f}ms) - {detail}")

async def timed_req(client: httpx.AsyncClient, method: str, url: str, **kwargs):
    t0 = time.perf_counter()
    resp = await client.request(method, url, **kwargs)
    ms = (time.perf_counter() - t0) * 1000
    return resp, ms

async def test_rag(client: httpx.AsyncClient):
    print("\n--- 1. Testing RAG-Server Endpoints ---")
    headers = {"X-Internal-RAG-Token": RAG_TOKEN}
    for path in ["/health/live", "/health/ready", "/version"]:
        r, ms = await timed_req(client, "GET", f"{RAG_URL}{path}")
        record(f"rag:{path}", "GET", "PASS" if r.status_code == 200 else "FAIL", r.status_code, "OK", ms)

    r, ms = await timed_req(client, "POST", f"{RAG_URL}/v1/search", json={"query": "test"})
    record("rag:/v1/search (no-token)", "POST", "PASS" if r.status_code == 401 else "FAIL", r.status_code, "Guarded", ms)

    r, ms = await timed_req(client, "POST", f"{RAG_URL}/v1/search", headers=headers, json={"query": "sql injection", "cwe_id": "CWE-89"})
    record("rag:/v1/search (valid)", "POST", "PASS" if r.status_code == 200 else "FAIL", r.status_code, f"Items: {len(r.json().get('results', []))}", ms)

    r, ms = await timed_req(client, "GET", f"{RAG_URL}/v1/index/status")
    record("rag:/v1/index/status (no-tok)", "GET", "PASS" if r.status_code == 401 else "FAIL", r.status_code, "Guarded", ms)

    r, ms = await timed_req(client, "GET", f"{RAG_URL}/v1/index/status", headers=headers)
    record("rag:/v1/index/status (valid)", "GET", "PASS" if r.status_code == 200 else "FAIL", r.status_code, f"Docs: {r.json().get('total_documents')}", ms)

async def test_main_public(client: httpx.AsyncClient):
    print("\n--- 2. Testing Main-Server Public & Health Endpoints ---")
    for path in ["/", "/health/live", "/health/ready", "/version"]:
        r, ms = await timed_req(client, "GET", f"{MAIN_URL}{path}")
        record(f"main:{path}", "GET", "PASS" if r.status_code == 200 else "FAIL", r.status_code, "OK", ms)

    r, ms = await timed_req(client, "GET", f"{MAIN_URL}/v1/auth/github/start", follow_redirects=False)
    record("main:/v1/auth/github/start", "GET", "PASS" if r.status_code in (302, 307) else "FAIL", r.status_code, "Redirect", ms)

    r, ms = await timed_req(client, "GET", f"{MAIN_URL}/v1/auth/github/callback", follow_redirects=False)
    record("main:/v1/auth/github/cb (empty)", "GET", "PASS" if r.status_code == 422 else "FAIL", r.status_code, "Validation Guard", ms)

    r, ms = await timed_req(client, "POST", f"{MAIN_URL}/v1/auth/logout")
    record("main:/v1/auth/logout", "POST", "PASS" if r.status_code == 200 else "FAIL", r.status_code, "Cookie cleared", ms)

async def test_main_auth_flow(client: httpx.AsyncClient):
    print("\n--- 3. Testing Main-Server Authenticated Endpoints ---")
    r, ms = await timed_req(client, "GET", f"{MAIN_URL}/v1/auth/me", cookies=AUTH_COOKIES)
    pass_me = r.status_code == 200 and r.json().get("username") == "omchoksi"
    record("main:/v1/auth/me (authed)", "GET", "PASS" if pass_me else "FAIL", r.status_code, f"User: {r.json().get('username')}", ms)

    r, ms = await timed_req(client, "GET", f"{MAIN_URL}/v1/reviews", cookies=AUTH_COOKIES)
    record("main:/v1/reviews (list)", "GET", "PASS" if r.status_code == 200 else "FAIL", r.status_code, f"Found {len(r.json())} reviews", ms)

    r, ms = await timed_req(client, "GET", f"{MAIN_URL}/v1/reviews/rev-demo-101", cookies=AUTH_COOKIES)
    pass_det = r.status_code == 200 and len(r.json().get("findings", [])) >= 2
    record("main:/v1/reviews/demo (detail)", "GET", "PASS" if pass_det else "FAIL", r.status_code, f"Findings: {len(r.json().get('findings', []))}", ms)

    r, ms = await timed_req(client, "GET", f"{MAIN_URL}/v1/reviews/non-existent-uuid", cookies=AUTH_COOKIES)
    record("main:/v1/reviews/non-existent", "GET", "PASS" if r.status_code == 404 else "FAIL", r.status_code, "Not Found Guard", ms)

    # Manual review enqueuing
    payload = {"repository_id": "repo-1", "code_content": "import os\nos.system('ls')", "file_path": "cmd.py"}
    r, ms = await timed_req(client, "POST", f"{MAIN_URL}/v1/reviews", cookies=AUTH_COOKIES, json=payload)
    record("main:/v1/reviews (manual)", "POST", "PASS" if r.status_code == 202 else "FAIL", r.status_code, f"Job: {r.json().get('job_id')}", ms)

    # Admin log streaming
    for srv in ["main-server", "client-server", "rag-server"]:
        path = f"/{srv}-logs"
        r, ms = await timed_req(client, "GET", f"{MAIN_URL}{path}?limit=5", cookies=AUTH_COOKIES)
        record(f"main:{path}", "GET", "PASS" if r.status_code == 200 else "FAIL", r.status_code, f"Logs: {len(r.json())}", ms)

async def test_webhooks(client: httpx.AsyncClient):
    print("\n--- 4. Testing GitHub Webhook Endpoints & Signatures ---")
    del_id = str(uuid.uuid4())
    body = json.dumps({"action": "opened", "installation": {"id": "12345678"}, "repository": {"id": "98765432", "full_name": "omchoksi/repo"}, "pull_request": {"number": 105, "head": {"sha": "c0ffee"}}}).encode()
    valid_sig = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

    r, ms = await timed_req(client, "POST", f"{MAIN_URL}/v1/webhooks/github", content=body, headers={"X-Hub-Signature-256": "sha256=invalid", "X-GitHub-Delivery": del_id, "X-GitHub-Event": "pull_request"})
    record("main:/v1/webhooks/github (bad-sig)", "POST", "PASS" if r.status_code == 401 else "FAIL", r.status_code, "Rejected bad HMAC", ms)

    r, ms = await timed_req(client, "POST", f"{MAIN_URL}/v1/webhooks/github", content=body, headers={"X-Hub-Signature-256": valid_sig, "X-GitHub-Delivery": del_id, "X-GitHub-Event": "pull_request"})
    record("main:/v1/webhooks/github (valid)", "POST", "PASS" if r.status_code == 202 else "FAIL", r.status_code, f"Status: {r.json().get('status')}", ms)

    r, ms = await timed_req(client, "POST", f"{MAIN_URL}/v1/webhooks/github", content=body, headers={"X-Hub-Signature-256": valid_sig, "X-GitHub-Delivery": del_id, "X-GitHub-Event": "pull_request"})
    record("main:/v1/webhooks/github (replay)", "POST", "PASS" if r.status_code == 202 and r.json().get("status") == "duplicate_ignored" else "FAIL", r.status_code, "Replay defense OK", ms)

async def test_missing_crud(client: httpx.AsyncClient):
    print("\n--- 5. Testing SaaS Domain Endpoints (Discovered Gaps) ---")
    checks = [
        ("GET", "/v1/repositories", "Repositories list"),
        ("GET", "/v1/findings", "Findings list"),
        ("GET", "/v1/policies", "Security policy"),
        ("PUT", "/v1/policies", "Update security policy"),
        ("GET", "/v1/team", "Team members list"),
    ]
    for method, path, desc in checks:
        r, ms = await timed_req(client, method, f"{MAIN_URL}{path}", cookies=AUTH_COOKIES, json={})
        status = "PASS" if r.status_code in (200, 201) else "FAIL"
        record(f"main:{path}", method, status, r.status_code, f"{desc} ({'Missing' if r.status_code == 404 or r.status_code == 405 else 'Implemented'})", ms)

async def run_all():
    async with httpx.AsyncClient(timeout=15.0) as client:
        await test_rag(client)
        await test_main_public(client)
        await test_main_auth_flow(client)
        await test_webhooks(client)
        await test_missing_crud(client)

    print("\n================ SUMMARY ================")
    p = sum(1 for r in results if r["status"] == "PASS")
    f = sum(1 for r in results if r["status"] == "FAIL")
    print(f"Total: {len(results)} | Passed: {p} | Failed/Missing: {f}")

if __name__ == "__main__":
    asyncio.run(run_all())
