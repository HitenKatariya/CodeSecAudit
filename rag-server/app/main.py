"""RAG Server application entrypoint."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import setup_logger
from app.embeddings.model import get_embedding_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logger(settings.redis_url)
    logger = logging.getLogger("rag_server")
    mgr = get_embedding_manager(settings.rag_embedding_model)
    if not mgr.is_ready:
        logger.warning(
            "Embedding provider is not configured. Set EMBEDDING_API_BASE and "
            "EMBEDDING_MODEL (plus EMBEDDING_API_KEY if required) to enable RAG search."
        )
    yield


settings = get_settings()

app = FastAPI(
    title="CodeSecAudit RAG Server",
    version=settings.app_version,
    description="Internal private OWASP RAG retrieval and embedding microservice",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/", tags=["Root"])
def root_index():
    return {
        "service": "codesec-rag-server",
        "description": "Internal OWASP RAG Retrieval and Vector Microservice",
        "version": settings.app_version,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "endpoints": {
            "health_and_system": [
                {"method": "GET", "path": "/health/live", "description": "Liveness probe"},
                {"method": "GET", "path": "/health/ready", "description": "Readiness probe (Qdrant & Model status)"},
                {"method": "GET", "path": "/version", "description": "Service version, corpus version, and embedding model"}
            ],
            "search_and_retrieval": [
                {"method": "POST", "path": "/v1/search", "description": "Search top-k OWASP guidance chunks with optional CWE filter (Protected)"}
            ],
            "indexing": [
                {"method": "POST", "path": "/v1/index", "description": "Trigger indexing of corpus into Qdrant (Protected)"},
                {"method": "GET", "path": "/v1/index/status", "description": "Get Qdrant collection status and document count (Protected)"}
            ]
        }
    }

app.include_router(router)
