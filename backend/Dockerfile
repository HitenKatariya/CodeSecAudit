FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Build context = backend/  (contains api/, review_engine/, review_store/, config/)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

ENV CODESEC_DB_PATH=/app/data/app/reviews.db
ENV CODESEC_ENABLE_RAG=false

VOLUME ["/app/data/app"]
EXPOSE 8003

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8003"]
