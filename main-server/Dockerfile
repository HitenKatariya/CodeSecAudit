# Slim multi-stage image (~250-300 MB). pr-agent pulls in tiktoken/litellm,
# which don't reliably ship musllinux wheels, so this moved off Alpine onto
# Debian slim (manylinux wheels everywhere) rather than compiling on musl.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Copy only the project metadata + package stub so this layer is cached until
# dependencies change.
COPY pyproject.toml ./
COPY app/__init__.py app/__init__.py
RUN pip install --prefix=/install .

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

RUN adduser --disabled-password --uid 10001 appuser

COPY --from=builder /install /usr/local

COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .

USER appuser

EXPOSE 8000

# Render injects $PORT; compose falls back to 8000.
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
