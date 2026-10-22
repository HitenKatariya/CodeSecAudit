# Slim multi-stage image (~130-160 MB). Embeddings are remote (OpenAI-compatible
# API), so there is no torch/CUDA/transformers stack in the image.
FROM python:3.11-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ONLY_BINARY=:all:

WORKDIR /build

COPY pyproject.toml ./
COPY app/__init__.py app/__init__.py
RUN pip install --prefix=/install .

FROM python:3.11-alpine AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8010

WORKDIR /app

RUN apk add --no-cache libstdc++ \
    && adduser -D -u 10001 appuser

COPY --from=builder /install /usr/local

COPY app/ app/
COPY scripts/ scripts/

USER appuser

EXPOSE 8010

CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8010}"]
