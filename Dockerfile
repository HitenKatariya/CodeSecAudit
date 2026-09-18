FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install all three services' deps in one layer (dedup pip resolves).
COPY backend/requirements.txt ./backend-requirements.txt
COPY rag-service/requirements.txt ./rag-service-requirements.txt
COPY website/requirements.txt ./website-requirements.txt
RUN pip install --no-cache-dir \
    -r backend-requirements.txt \
    -r rag-service-requirements.txt \
    -r website-requirements.txt

# Copy service code (keeps backend/api, rag-service/rag_service, website/website layouts
# so all existing `from review_engine/review_store/rag_service/website` imports work).
COPY backend/ ./backend/
COPY rag-service/ ./rag-service/
COPY website/ ./website/
COPY start-all.sh ./start-all.sh
RUN chmod +x ./start-all.sh

# Wiring defaults: backend -> local rag-service, website -> local backend.
ENV PYTHONPATH=/app:/app/backend:/app/rag-service \
    CODESEC_DB_PATH=/app/backend/data/app/reviews.db \
    CODESEC_RAG_MODE=remote \
    CODESEC_RAG_SERVICE_URL=http://localhost:7860 \
    CODESEC_API_URL=http://localhost:8003 \
    RAG_BUILD_ON_START=true

VOLUME ["/app/backend/data/app"]
EXPOSE 8003 7860 10000

CMD ["./start-all.sh"]
