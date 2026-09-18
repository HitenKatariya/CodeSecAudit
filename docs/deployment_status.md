# Deployment Status

## Live Services

| Service | URL | Status |
|---|---|---|
| RAG Service | https://hitenvk22-codesec-rag-service.hf.space | **Live** |
| GitHub Repo | https://github.com/hitenkatariya/CodeSecAudit | Active |
| Hugging Face Dataset | https://huggingface.co/datasets/hitenvk22/CodeSecAudit-RAG-Shuffled | Published |
| Deploy PR | https://github.com/hitenkatariya/CodeSecAudit/pull/1 | Merged |

## RAG Service Verification

All checks pass against the live remote RAG service.

### Health check

```json
GET /health
{
  "status": "ok",
  "index_loaded": true,
  "total_chunks": 2833,
  "embedding_count": 2833,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

### Search test

```json
POST /rag/search {"query": "SQL injection", "top_k": 2}
{
  "results": [
    {"rank": 1, "score": 0.704, "title": "SQL Injection Prevention Cheat Sheet", "cwe_id": "CWE-89"},
    {"rank": 2, "score": 0.686, "title": "SQL Injection Prevention Cheat Sheet", "cwe_id": "CWE-89"}
  ],
  "metadata": {
    "query_time_ms": 154.58,
    "total_chunks": 2833
  }
}
```

### Main API integration

```text
CODESEC_RAG_MODE=remote
CODESEC_RAG_SERVICE_URL=https://hitenvk22-codesec-rag-service.hf.space

Result: rag_used=True, rag_error=None, verdict=WARNING, risk_score=35
```

### Golden evaluation

```text
12 golden cases: 12/12 passing (with remote RAG enabled)
```

## Pending Deployments

| Component | Host | Status | Notes |
|---|---|---|---|
| API + Dashboard | Render / Railway | Planned | Awaiting SaaS backend prep |
| MongoDB Atlas | MongoDB Cloud | Planned | Schema designed but not deployed |
| Resend Email | Resend | Planned | Workflows designed but not implemented |
| GitHub App | GitHub Marketplace | Planned | Requires GitHub OAuth + App registration |
