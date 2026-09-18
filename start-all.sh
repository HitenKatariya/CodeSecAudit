#!/usr/bin/env bash
set -e

# Single-container launcher: rag-service + backend + website.
# Each server runs from its own dir so existing import layouts keep working:
#   backend/     -> `uvicorn api.main:app`        (needs review_engine/ sibling)
#   rag-service/ -> `uvicorn rag_service.main:app`
#   /app         -> `gunicorn website.app:app`    (needs website/ package)

echo "[start-all] starting rag-service :7860 ..."
(cd /app/rag-service && uvicorn rag_service.main:app --host 0.0.0.0 --port 7860) &
RAG_PID=$!

echo "[start-all] starting backend :8003 ..."
(cd /app/backend && uvicorn api.main:app --host 0.0.0.0 --port 8003) &
API_PID=$!

# Wait for backend health before starting website (max ~60s).
echo "[start-all] waiting for backend /health ..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:8003/health > /dev/null 2>&1; then
    echo "[start-all] backend is up."
    break
  fi
  sleep 1
  if [ "$i" -eq 60 ]; then
    echo "[start-all] WARNING: backend not healthy after 60s, starting website anyway."
  fi
done

echo "[start-all] starting website :10000 (foreground) ..."
cd /app
exec gunicorn website.app:app --bind 0.0.0.0:10000 --workers 2 --timeout 120
