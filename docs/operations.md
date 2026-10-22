# CodeSecAudit Operations Manual

## 1. Service Topology & Ports

| Service | Port | Network | Purpose |
|---|---|---|---|
| `client` | 3000 | Public (Dev) | Next.js frontend UI & BFF same-origin proxy |
| `main-server` | 8000 | Public (Dev) | Auth, OAuth, Webhook receiver, REST API |
| `main-worker` | N/A | Internal | Background review processing worker |
| `rag-server` | 8010 | Internal | Private vector search & embedding microservice |
| `postgres` | 5432 | Internal | PostgreSQL 16 persistence |
| `redis` | 6379 | Internal | Sessions, Rate limits, Job Queue, Log Streams |
| `qdrant` | 6333 | Internal | Qdrant vector database for OWASP embeddings |

## 2. Admin Log Streams (Redis Streams)

Logs are written directly to bounded Redis Streams with write-time secret redaction:
- `log:main-server`
- `log:client`
- `log:rag-server`

### Tailing Logs via Redis CLI
```bash
# Tail latest 50 entries from main-server stream
redis-cli XREVRANGE log:main-server + - COUNT 50

# Tail latest 50 entries from RAG server stream
redis-cli XREVRANGE log:rag-server + - COUNT 50
```

### Accessing via Admin REST API
Authenticated admins can query:
```bash
curl -H "Cookie: codesec_session=<ADMIN_SESSION>" http://localhost:8000/main-server-logs?limit=50
curl -H "Cookie: codesec_session=<ADMIN_SESSION>" http://localhost:8000/client-server-logs?limit=50
curl -H "Cookie: codesec_session=<ADMIN_SESSION>" http://localhost:8000/rag-server-logs?limit=50
```
Every access is logged to the `audit_events` table in PostgreSQL.

## 3. Database Migrations (Alembic)

Database schema updates are managed exclusively through Alembic migrations:
```bash
# Inside main-server container or environment:
cd main-server
alembic upgrade head

# Generate a new migration
alembic revision --autogenerate -m "add_new_feature_table"
```

## 4. Re-indexing Qdrant Corpus

To trigger re-indexing of the OWASP guidance corpus:
```bash
curl -X POST http://localhost:8010/v1/index \
  -H "X-Internal-RAG-Token: dev_rag_service_token_secret" \
  -H "Content-Type: application/json" \
  -d '{"corpus_url": "https://huggingface.co/datasets/OMCHOKSI108/CodeSecAudit-RAG/resolve/main/rag/rag_corpus.jsonl.gz"}'
```
Check index status:
```bash
curl http://localhost:8010/v1/index/status \
  -H "X-Internal-RAG-Token: dev_rag_service_token_secret"
```
