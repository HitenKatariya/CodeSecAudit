"""Script to generate production-grade Postman Collection and Environments for CodeSecAudit AI."""

import json
import os

COLLECTION_NAME = "CodeSecAudit AI - Full E2E API Suite"
COLLECTION_DESC = (
    "Comprehensive end-to-end API collection for CodeSecAudit AI. "
    "Enables automated 1-by-1 testing of all endpoints across Main Server (FastAPI), "
    "RAG Server (Vector Search & Embeddings), and Client Web Proxy (Next.js 14). "
    "Features automated HMAC-SHA256 signature calculation, session propagation, and test assertions."
)

def create_request_item(
    name: str,
    method: str,
    url_path: str,
    base_var: str = "main_url",
    description: str = "",
    headers: dict = None,
    cookies: bool = False,
    query_params: list = None,
    body_json: dict = None,
    raw_body: str = None,
    pre_request_script: str = "",
    test_script: str = "",
):
    headers = headers or {}
    if cookies:
        headers["Cookie"] = "codesec_session={{codesec_session}}"

    header_list = [{"key": k, "value": v, "type": "text"} for k, v in headers.items()]

    path_clean = url_path.split("?")[0].strip("/")
    path_segments = [p for p in path_clean.split("/") if p]
    url_obj = {
        "raw": f"{{{{{base_var}}}}}{url_path}",
        "host": [f"{{{{{base_var}}}}}"],
        "path": path_segments,
    }

    if "?" in url_path and not query_params:
        query_params = []
        for pair in url_path.split("?")[1].split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                query_params.append({"key": k, "value": v})

    if query_params:
        url_obj["query"] = query_params

    item = {
        "name": name,
        "event": [],
        "request": {
            "method": method,
            "header": header_list,
            "url": url_obj,
            "description": description,
        },
        "response": [],
    }

    if body_json is not None:
        item["request"]["body"] = {
            "mode": "raw",
            "raw": json.dumps(body_json, indent=2),
            "options": {"raw": {"language": "json"}},
        }
        if "Content-Type" not in headers:
            item["request"]["header"].append({"key": "Content-Type", "value": "application/json", "type": "text"})
    elif raw_body is not None:
        item["request"]["body"] = {
            "mode": "raw",
            "raw": raw_body,
            "options": {"raw": {"language": "json"}},
        }

    if pre_request_script:
        item["event"].append({
            "listen": "prerequest",
            "script": {
                "type": "text/javascript",
                "exec": [line for line in pre_request_script.strip().split("\n")],
            },
        })

    if test_script:
        item["event"].append({
            "listen": "test",
            "script": {
                "type": "text/javascript",
                "exec": [line for line in test_script.strip().split("\n")],
            },
        })

    return item


def build_collection():
    items = []

    # ----------------------------------------------------
    # 01: Health & System Discovery
    # ----------------------------------------------------
    health_items = [
        create_request_item(
            name="1.1 Main Server Root API Directory",
            method="GET",
            url_path="/",
            description="Returns service metadata, documentation links, and route catalogue.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Valid root service catalogue", function () {
    const res = pm.response.json();
    pm.expect(res.service).to.eql("codesec-main-server");
    pm.expect(res.endpoints).to.be.an("object");
});
""",
        ),
        create_request_item(
            name="1.2 Main Server Liveness Probe",
            method="GET",
            url_path="/health/live",
            description="Kubernetes / Docker liveness probe verifying HTTP daemon is responsive.",
            test_script="""
pm.test("Status is 200 OK", function () {
    pm.response.to.have.status(200);
    pm.expect(pm.response.json().status).to.eql("ok");
});
""",
        ),
        create_request_item(
            name="1.3 Main Server Readiness Probe",
            method="GET",
            url_path="/health/ready",
            description="Deep readiness probe checking PostgreSQL, Redis, and RAG Service availability.",
            test_script="""
pm.test("Readiness check passes or reports components", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 503]);
    const res = pm.response.json();
    if (pm.response.code === 200) {
        pm.expect(res.status).to.eql("ready");
    }
});
""",
        ),
        create_request_item(
            name="1.4 Main Server Version Info",
            method="GET",
            url_path="/version",
            description="Returns application version and git commit SHA.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
    const res = pm.response.json();
    pm.expect(res.service).to.eql("main-server");
    pm.expect(res.version).to.be.a("string");
});
""",
        ),
    ]
    items.append({"name": "01 - Health & System Discovery", "item": health_items})

    # ----------------------------------------------------
    # 02: Authentication & Sessions
    # ----------------------------------------------------
    auth_items = [
        create_request_item(
            name="2.1 GitHub OAuth Start (PKCE Redirect)",
            method="GET",
            url_path="/v1/auth/github/start",
            description="Initiates GitHub OAuth flow with state & code verifier in session.",
            test_script="""
pm.test("Redirects to GitHub OAuth (302/307)", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 302, 307]);
});
""",
        ),
        create_request_item(
            name="2.2 GitHub OAuth Callback Guard",
            method="GET",
            url_path="/v1/auth/github/callback?code=mock_code&state=mock_state",
            description="Tests OAuth callback validation guard with invalid/mock state.",
            test_script="""
pm.test("Guards against invalid OAuth state (400 or 422)", function () {
    pm.expect(pm.response.code).to.be.oneOf([400, 422]);
});
""",
        ),
        create_request_item(
            name="2.3 Get Current User Profile (/me)",
            method="GET",
            url_path="/v1/auth/me",
            cookies=True,
            description="Retrieves current authenticated tenant profile, active organization, and admin status.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Valid user profile returned", function () {
    const res = pm.response.json();
    pm.expect(res.id).to.be.a("string");
    pm.expect(res.username).to.be.a("string");
    pm.expect(res.active_organization_id).to.be.a("string");
});
""",
        ),
    ]
    items.append({"name": "02 - Authentication & Sessions", "item": auth_items})

    # ----------------------------------------------------
    # 03: Repositories Management
    # ----------------------------------------------------
    repo_items = [
        create_request_item(
            name="3.1 List Repositories",
            method="GET",
            url_path="/v1/repositories",
            cookies=True,
            description="Lists all monitored repositories in the tenant's organization with risk metrics.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Returns repository list", function () {
    const res = pm.response.json();
    pm.expect(res).to.be.an("array");
    if (res.length > 0) {
        pm.environment.set("repo_id", res[0].id);
        pm.expect(res[0]).to.have.property("security_score");
    }
});
""",
        ),
        create_request_item(
            name="3.2 Get Repository Details",
            method="GET",
            url_path="/v1/repositories/{{repo_id}}",
            cookies=True,
            description="Fetches specific repository details, security score, and open finding counts.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Repository payload structure", function () {
    const res = pm.response.json();
    pm.expect(res.id).to.eql(pm.environment.get("repo_id"));
    pm.expect(res.status).to.be.oneOf(["Protected", "Warning", "Blocked"]);
});
""",
        ),
    ]
    items.append({"name": "03 - Repositories Management", "item": repo_items})

    # ----------------------------------------------------
    # 04: Security Policies
    # ----------------------------------------------------
    policy_items = [
        create_request_item(
            name="4.1 Get Organization Security Policy",
            method="GET",
            url_path="/v1/policies",
            cookies=True,
            description="Fetches gating rules, threshold score, and blocked vulnerability classes.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Policy properties exist", function () {
    const res = pm.response.json();
    pm.expect(res).to.have.property("block_critical");
    pm.expect(res).to.have.property("min_security_score");
});
""",
        ),
        create_request_item(
            name="4.2 Update Security Policy",
            method="PUT",
            url_path="/v1/policies",
            cookies=True,
            description="Updates organization policy rules in Redis for PR gating.",
            body_json={
                "block_critical": True,
                "block_secrets": True,
                "block_high": True,
                "block_medium": False,
                "min_security_score": 85,
                "confidence_threshold": 75,
                "secret_detection": True
            },
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Policy updated successfully", function () {
    const res = pm.response.json();
    pm.expect(res.min_security_score).to.eql(85);
    pm.expect(res.block_critical).to.be.true;
});
""",
        ),
    ]
    items.append({"name": "04 - Security Policies", "item": policy_items})

    # ----------------------------------------------------
    # 05: Review Orchestration & Jobs
    # ----------------------------------------------------
    review_items = [
        create_request_item(
            name="5.1 Enqueue Manual Review (Vulnerabilities: SQLi + Command Injection)",
            method="POST",
            url_path="/v1/reviews",
            cookies=True,
            description="Enqueues a review job with dangerous code to test detector engine and RAG enrichment.",
            body_json={
                "repository_id": "{{repo_id}}",
                "code_content": "import os\nimport sqlite3\n\ndef login(req):\n    user = req.params['user']\n    cmd = req.params['cmd']\n    os.system('echo ' + cmd)\n    cursor.execute(f'SELECT * FROM users WHERE name = {user}')\n",
                "file_path": "auth/controller.py"
            },
            test_script="""
pm.test("Status code is 202 Accepted", function () {
    pm.response.to.have.status(202);
});
pm.test("Job enqueued with valid job_id", function () {
    const res = pm.response.json();
    pm.expect(res.status).to.eql("enqueued");
    pm.expect(res.job_id).to.be.a("string");
    pm.environment.set("test_job_id", res.job_id);
});
""",
        ),
        create_request_item(
            name="5.2 Enqueue Clean Code Review (No Vulnerabilities)",
            method="POST",
            url_path="/v1/reviews",
            cookies=True,
            description="Enqueues secure code using parameterized queries and safe hashing.",
            body_json={
                "repository_id": "{{repo_id}}",
                "code_content": "import hashlib\nimport sqlite3\n\ndef safe_hash(password: str) -> str:\n    return hashlib.sha256(password.encode()).hexdigest()\n\ndef get_user(db, user_id: int):\n    return db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()\n",
                "file_path": "security/safe_utils.py"
            },
            test_script="""
pm.test("Status code is 202 Accepted", function () {
    pm.response.to.have.status(202);
});
pm.test("Job ID returned", function () {
    pm.expect(pm.response.json().job_id).to.be.a("string");
});
""",
        ),
        create_request_item(
            name="5.3 Enqueue Suppressed Vulnerability Code Review",
            method="POST",
            url_path="/v1/reviews",
            cookies=True,
            description="Verifies inline directive suppression (`codesec-ignore-next-line: CWE-94`).",
            body_json={
                "repository_id": "{{repo_id}}",
                "code_content": "# codesec-ignore-next-line: CWE-94\neval('2 + 2')\n",
                "file_path": "calculator/evaluator.py"
            },
            test_script="""
pm.test("Status code is 202 Accepted", function () {
    pm.response.to.have.status(202);
});
""",
        ),
        create_request_item(
            name="5.4 List Reviews (Paginated)",
            method="GET",
            url_path="/v1/reviews?limit=20&offset=0",
            cookies=True,
            description="Lists review history for the active organization.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Review list parsed", function () {
    const res = pm.response.json();
    pm.expect(res).to.be.an("array");
    if (res.length > 0) {
        pm.environment.set("review_id", res[0].id);
        pm.expect(res[0]).to.have.property("verdict");
        pm.expect(res[0]).to.have.property("risk_score");
    }
});
""",
        ),
        create_request_item(
            name="5.5 Get Review Detail & Findings",
            method="GET",
            url_path="/v1/reviews/{{review_id}}",
            cookies=True,
            description="Retrieves a specific review by ID including all detected findings, risk score, and verdict.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Review details valid", function () {
    const res = pm.response.json();
    pm.expect(res.id).to.eql(pm.environment.get("review_id"));
    pm.expect(res.findings).to.be.an("array");
});
""",
        ),
    ]
    items.append({"name": "05 - Review Orchestration & Jobs", "item": review_items})

    # ----------------------------------------------------
    # 06: Security Findings Triage
    # ----------------------------------------------------
    finding_items = [
        create_request_item(
            name="6.1 List All Open Findings",
            method="GET",
            url_path="/v1/findings?limit=50",
            cookies=True,
            description="Lists all security findings across all repositories for the organization.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Findings list structure", function () {
    const res = pm.response.json();
    pm.expect(res).to.be.an("array");
    if (res.length > 0) {
        pm.environment.set("finding_id", res[0].id);
        pm.expect(res[0]).to.have.property("cwe_id");
        pm.expect(res[0]).to.have.property("severity");
    }
});
""",
        ),
        create_request_item(
            name="6.2 Filter Findings by Critical Severity",
            method="GET",
            url_path="/v1/findings?severity=critical",
            cookies=True,
            description="Filters security findings by 'critical' severity.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Filtered items have critical severity", function () {
    const res = pm.response.json();
    res.forEach(item => {
        pm.expect(item.severity.toLowerCase()).to.eql("critical");
    });
});
""",
        ),
        create_request_item(
            name="6.3 Filter Findings by CWE-89 (SQL Injection)",
            method="GET",
            url_path="/v1/findings?cwe_id=CWE-89",
            cookies=True,
            description="Filters findings specifically for SQL Injection vulnerabilities.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Findings match CWE-89", function () {
    const res = pm.response.json();
    res.forEach(item => {
        pm.expect(item.cwe_id).to.eql("CWE-89");
    });
});
""",
        ),
        create_request_item(
            name="6.4 Get Finding Detail by ID",
            method="GET",
            url_path="/v1/findings/{{finding_id}}",
            cookies=True,
            description="Fetches detailed remediation guidance, attack scenario, and code snippet for a finding.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Finding details structure", function () {
    const res = pm.response.json();
    pm.expect(res.id).to.eql(pm.environment.get("finding_id"));
    pm.expect(res).to.have.property("suggested_fix");
    pm.expect(res).to.have.property("code_snippet");
});
""",
        ),
    ]
    items.append({"name": "06 - Security Findings Triage", "item": finding_items})

    # ----------------------------------------------------
    # 07: Team Management
    # ----------------------------------------------------
    team_items = [
        create_request_item(
            name="7.1 List Team Members & Roles",
            method="GET",
            url_path="/v1/team",
            cookies=True,
            description="Retrieves the team roster for the current active organization.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Team member list structure", function () {
    const res = pm.response.json();
    pm.expect(res).to.be.an("array");
    if (res.length > 0) {
        pm.expect(res[0]).to.have.property("role");
        pm.expect(res[0]).to.have.property("email");
    }
});
""",
        ),
    ]
    items.append({"name": "07 - Team Management", "item": team_items})

    # ----------------------------------------------------
    # 08: GitHub Webhooks & Signatures
    # ----------------------------------------------------
    webhook_payload = {
        "action": "opened",
        "installation": {"id": 12345678},
        "repository": {
            "id": 98765432,
            "full_name": "omchoksi/CodeSecurityAuditAgent",
            "private": False
        },
        "pull_request": {
            "number": 108,
            "head": {"sha": "c0ffeebabe1234567890"}
        }
    }
    raw_payload_str = json.dumps(webhook_payload, separators=(',', ':'))

    webhook_items = [
        create_request_item(
            name="8.1 Ingest GitHub Pull Request Webhook (Auto HMAC-SHA256 Signed)",
            method="POST",
            url_path="/v1/webhooks/github",
            description="Simulates incoming GitHub PR webhook. Pre-request script automatically signs payload using HMAC-SHA256.",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "{{$guid}}",
                "X-Hub-Signature-256": "{{webhook_signature}}",
                "Content-Type": "application/json"
            },
            raw_body=raw_payload_str,
            pre_request_script="""
var secret = pm.environment.get("github_webhook_secret") || "dev_github_webhook_secret_key";
var body = pm.request.body.raw;
var hash = CryptoJS.HmacSHA256(body, secret).toString(CryptoJS.enc.Hex);
pm.environment.set("webhook_signature", "sha256=" + hash);
pm.request.headers.upsert({key: "X-Hub-Signature-256", value: "sha256=" + hash});
pm.request.headers.upsert({key: "X-GitHub-Delivery", value: pm.variables.replaceIn('{{$guid}}')});
""",
            test_script="""
pm.test("Webhook accepted or handled correctly", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 202]);
    const res = pm.response.json();
    pm.expect(res).to.have.property("status");
});
""",
        ),
        create_request_item(
            name="8.2 Ingest Webhook - Invalid Signature Test",
            method="POST",
            url_path="/v1/webhooks/github",
            description="Tests security rejection when X-Hub-Signature-256 does not match.",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "{{$guid}}",
                "X-Hub-Signature-256": "sha256=invalidbadhash000000000000000000000000000000000000000000000000",
                "Content-Type": "application/json"
            },
            raw_body=raw_payload_str,
            test_script="""
pm.test("Rejects unauthenticated webhook with 401 Unauthorized", function () {
    pm.expect(pm.response.code).to.eql(401);
});
""",
        ),
    ]
    items.append({"name": "08 - GitHub Webhooks & Signatures", "item": webhook_items})

    # ----------------------------------------------------
    # 09: Admin Log Streaming & Auditing
    # ----------------------------------------------------
    admin_log_items = [
        create_request_item(
            name="9.1 Tail Main-Server Logs",
            method="GET",
            url_path="/main-server-logs?limit=25",
            cookies=True,
            description="Tails sanitized Redis stream logs for main-server (requires system admin).",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Log entries format", function () {
    const res = pm.response.json();
    pm.expect(res).to.be.an("array");
});
""",
        ),
        create_request_item(
            name="9.2 Tail Client-Server Logs",
            method="GET",
            url_path="/client-server-logs?limit=25",
            cookies=True,
            description="Tails sanitized Redis stream logs for client Next.js application.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
""",
        ),
        create_request_item(
            name="9.3 Tail RAG-Server Logs",
            method="GET",
            url_path="/rag-server-logs?limit=25",
            cookies=True,
            description="Tails sanitized Redis stream logs for RAG vector microservice.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
""",
        ),
    ]
    items.append({"name": "09 - Admin Log Streaming & Auditing", "item": admin_log_items})

    # ----------------------------------------------------
    # 10: RAG Knowledge Base & Embeddings
    # ----------------------------------------------------
    rag_items = [
        create_request_item(
            name="10.1 RAG Server Liveness Probe",
            method="GET",
            url_path="/health/live",
            base_var="rag_url",
            description="Liveness probe for RAG microservice.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
    pm.expect(pm.response.json().status).to.eql("ok");
});
""",
        ),
        create_request_item(
            name="10.2 RAG Server Readiness Probe",
            method="GET",
            url_path="/health/ready",
            base_var="rag_url",
            description="Checks Qdrant connection and embedding model status.",
            test_script="""
pm.test("Readiness probe returns status (200 or 503 if unconfigured)", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 503]);
});
""",
        ),
        create_request_item(
            name="10.3 RAG Server Version & Model Status",
            method="GET",
            url_path="/version",
            base_var="rag_url",
            description="Reports RAG corpus version and embedding model identifier.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
    const res = pm.response.json();
    pm.expect(res.service).to.eql("rag-server");
    pm.expect(res).to.have.property("embedding_model");
});
""",
        ),
        create_request_item(
            name="10.4 Semantic Search OWASP Guidance (CWE-89 SQLi)",
            method="POST",
            url_path="/v1/search",
            base_var="rag_url",
            description="Retrieves top OWASP cheat sheet chunks for SQL injection via vector search.",
            headers={"X-Internal-RAG-Token": "{{rag_service_token}}"},
            body_json={
                "query": "SQL injection concatenation in database execute query",
                "cwe_id": "CWE-89",
                "top_k": 3
            },
            test_script="""
pm.test("Semantic search passes (200) or reports provider status (502/503)", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 502, 503]);
    if (pm.response.code === 200) {
        const res = pm.response.json();
        pm.expect(res.results).to.be.an("array");
    }
});
""",
        ),
        create_request_item(
            name="10.5 Semantic Search (CWE-78 OS Command Injection)",
            method="POST",
            url_path="/v1/search",
            base_var="rag_url",
            description="Searches OWASP guidance for command execution vulnerabilities.",
            headers={"X-Internal-RAG-Token": "{{rag_service_token}}"},
            body_json={
                "query": "subprocess call shell True command injection",
                "cwe_id": "CWE-78",
                "top_k": 3
            },
            test_script="""
pm.test("Response status is valid", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 502, 503]);
});
""",
        ),
        create_request_item(
            name="10.6 Semantic Search - Unauthorized Guard (No Token)",
            method="POST",
            url_path="/v1/search",
            base_var="rag_url",
            description="Guards private RAG search against unauthorized internal callers.",
            body_json={"query": "test without token"},
            test_script="""
pm.test("Status code is 401 Unauthorized", function () {
    pm.response.to.have.status(401);
});
""",
        ),
        create_request_item(
            name="10.7 Check RAG Index Status",
            method="GET",
            url_path="/v1/index/status",
            base_var="rag_url",
            headers={"X-Internal-RAG-Token": "{{rag_service_token}}"},
            description="Returns current document count and collection status from Qdrant.",
            test_script="""
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
    const res = pm.response.json();
    pm.expect(res).to.have.property("collection_name");
    pm.expect(res).to.have.property("total_documents");
});
""",
        ),
        create_request_item(
            name="10.8 Trigger Knowledge Base Indexing (Batch)",
            method="POST",
            url_path="/v1/index",
            base_var="rag_url",
            headers={"X-Internal-RAG-Token": "{{rag_service_token}}"},
            body_json={
                "corpus_url": "https://huggingface.co/datasets/OMCHOKSI108/CodeSecAudit-RAG/resolve/main/rag/rag_corpus.jsonl.gz",
                "max_documents": 5
            },
            description="Indexes a batch of OWASP corpus chunks into Qdrant.",
            test_script="""
pm.test("Indexing returns valid status code (200, 202, or 503 if unconfigured)", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 202, 502, 503]);
});
""",
        ),
    ]
    items.append({"name": "10 - RAG Knowledge Base & Embeddings", "item": rag_items})

    # ----------------------------------------------------
    # 11: Client Next.js Proxy & Frontend Health
    # ----------------------------------------------------
    client_items = [
        create_request_item(
            name="11.1 Client Frontend Health",
            method="GET",
            url_path="/health",
            base_var="client_url",
            description="Checks Next.js App Router health check route.",
            test_script="""
pm.test("Client health check passes", function () {
    pm.response.to.have.status(200);
    pm.expect(pm.response.json().status).to.eql("ok");
});
""",
        ),
        create_request_item(
            name="11.2 Client Frontend Version",
            method="GET",
            url_path="/version",
            base_var="client_url",
            description="Checks Next.js version route.",
            test_script="""
pm.test("Client version returns 200", function () {
    pm.response.to.have.status(200);
});
""",
        ),
        create_request_item(
            name="11.3 Client Runtime API Proxy - User Me",
            method="GET",
            url_path="/api/auth/me",
            base_var="client_url",
            cookies=True,
            description="Tests the Next.js runtime API proxy forwarding to main-server.",
            test_script="""
pm.test("Client proxy forwards request to main-server", function () {
    pm.response.to.have.status(200);
    pm.expect(pm.response.json()).to.have.property("username");
});
""",
        ),
        create_request_item(
            name="11.4 Client Runtime API Proxy - Reviews",
            method="GET",
            url_path="/api/reviews",
            base_var="client_url",
            cookies=True,
            description="Tests the Next.js runtime API proxy forwarding for reviews.",
            test_script="""
pm.test("Client proxy returns reviews list", function () {
    pm.response.to.have.status(200);
    pm.expect(pm.response.json()).to.be.an("array");
});
""",
        ),
    ]
    items.append({"name": "11 - Client Next.js Proxy & Frontend Health", "item": client_items})

    # ----------------------------------------------------
    # 12: Session Teardown & Logout
    # ----------------------------------------------------
    teardown_items = [
        create_request_item(
            name="12.1 Terminate User Session (Logout)",
            method="POST",
            url_path="/v1/auth/logout",
            cookies=True,
            description="Invalidates active session token in Redis and removes HttpOnly cookie.",
            test_script="""
pm.test("Logout succeeds (200)", function () {
    pm.response.to.have.status(200);
    pm.expect(pm.response.json().message).to.eql("Logged out");
});
""",
        ),
    ]
    items.append({"name": "12 - Session Teardown & Logout", "item": teardown_items})

    collection = {
        "info": {
            "_postman_id": "codesec-audit-full-api-suite-v1",
            "name": COLLECTION_NAME,
            "description": COLLECTION_DESC,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
    }
    return collection


def build_environment(env_type: str):
    if env_type == "local":
        name = "CodeSecAudit AI - Local Docker Environment"
        values = [
            {"key": "main_url", "value": "http://localhost:8000", "type": "default", "enabled": True},
            {"key": "rag_url", "value": "http://localhost:8010", "type": "default", "enabled": True},
            {"key": "client_url", "value": "http://localhost:3000", "type": "default", "enabled": True},
            {"key": "codesec_session", "value": "test-session-admin", "type": "secret", "enabled": True},
            {"key": "rag_service_token", "value": "dev_rag_service_token_secret", "type": "secret", "enabled": True},
            {"key": "github_webhook_secret", "value": "dev_github_webhook_secret_key", "type": "secret", "enabled": True},
            {"key": "repo_id", "value": "repo-1", "type": "default", "enabled": True},
            {"key": "review_id", "value": "rev-demo-101", "type": "default", "enabled": True},
            {"key": "finding_id", "value": "fin-demo-1", "type": "default", "enabled": True},
            {"key": "test_job_id", "value": "", "type": "default", "enabled": True},
            {"key": "webhook_signature", "value": "", "type": "default", "enabled": True},
        ]
    else:
        name = "CodeSecAudit AI - Render Cloud Production Environment"
        values = [
            {"key": "main_url", "value": "https://codesec-api.onrender.com", "type": "default", "enabled": True},
            {"key": "rag_url", "value": "https://codesec-rag.onrender.com", "type": "default", "enabled": True},
            {"key": "client_url", "value": "https://codesec-website.onrender.com", "type": "default", "enabled": True},
            {"key": "codesec_session", "value": "test-session-admin", "type": "secret", "enabled": True},
            {"key": "rag_service_token", "value": "dev_rag_service_token_secret", "type": "secret", "enabled": True},
            {"key": "github_webhook_secret", "value": "dev_github_webhook_secret_key", "type": "secret", "enabled": True},
            {"key": "repo_id", "value": "repo-1", "type": "default", "enabled": True},
            {"key": "review_id", "value": "rev-demo-101", "type": "default", "enabled": True},
            {"key": "finding_id", "value": "", "type": "default", "enabled": True},
            {"key": "test_job_id", "value": "", "type": "default", "enabled": True},
            {"key": "webhook_signature", "value": "", "type": "default", "enabled": True},
        ]

    return {
        "id": f"codesec-env-{env_type}",
        "name": name,
        "values": values,
        "_postman_variable_scope": "environment",
    }


def main():
    os.makedirs("postman", exist_ok=True)

    collection = build_collection()
    coll_path = "postman/CodeSecAudit_AI.postman_collection.json"
    with open(coll_path, "w") as f:
        json.dump(collection, f, indent=2)
    print(f"✅ Generated Postman Collection: {coll_path} ({len(collection['item'])} folders)")

    local_env = build_environment("local")
    local_path = "postman/CodeSecAudit_Local.postman_environment.json"
    with open(local_path, "w") as f:
        json.dump(local_env, f, indent=2)
    print(f"✅ Generated Local Environment: {local_path}")

    render_env = build_environment("render")
    render_path = "postman/CodeSecAudit_Render.postman_environment.json"
    with open(render_path, "w") as f:
        json.dump(render_env, f, indent=2)
    print(f"✅ Generated Render Environment: {render_path}")


if __name__ == "__main__":
    main()
