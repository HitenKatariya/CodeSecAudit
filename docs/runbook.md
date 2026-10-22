# CodeSecAudit Operational Runbook

## 1. Webhook Signature Failures (Incident Response)

**Symptoms:** GitHub webhook deliveries return 401 Unauthorized.
1. Check `main-server` logs:
   ```bash
   redis-cli XREVRANGE log:main-server + - COUNT 20
   ```
2. Verify `GITHUB_WEBHOOK_SECRET` in `.env` matches the secret configured in GitHub App settings.
3. Verify that the incoming delivery contains the header `X-Hub-Signature-256`.

## 2. Review Queue Backlog & Dead Letter Jobs

**Symptoms:** PR comments are delayed; Redis queue depth is increasing.
1. Inspect queue length in Redis:
   ```bash
   redis-cli LLEN queue:review
   ```
2. Check if `main-worker` is running:
   ```bash
   docker compose ps main-worker
   ```
3. Scale up worker replicas if needed:
   ```bash
   docker compose up -d --scale main-worker=3
   ```

## 3. RAG Microservice Degraded Mode

**Symptoms:** Reviews complete with verdict but have `guidance_available: false`.
1. Check RAG server health:
   ```bash
   curl -f http://localhost:8010/health/ready
   ```
2. Verify Qdrant container status:
   ```bash
   docker compose ps qdrant
   ```
3. Restart `rag-server`:
   ```bash
   docker compose restart rag-server
   ```
*Note:* The system is designed to gracefully degrade to deterministic rule checks without blocking pull request reviews.

## 4. PostgreSQL Backup & Restore

### Backup
```bash
docker exec -t codesec-postgres pg_dump -U codesec codesec > backup_$(date +%F).sql
```

### Restore
```bash
docker exec -i codesec-postgres psql -U codesec codesec < backup_2026-10-08.sql
```

## 5. Secret Rotation Procedures

1. **GitHub Webhook Secret:**
   - Update in GitHub App settings.
   - Update `GITHUB_WEBHOOK_SECRET` in `.env`.
   - Restart `main-server`: `docker compose restart main-server`.

2. **Internal RAG Service Token:**
   - Generate new random token: `openssl rand -hex 32`.
   - Update `RAG_SERVICE_TOKEN` in `.env`.
   - Restart `main-server`, `main-worker`, and `rag-server`.
