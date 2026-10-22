"""RAG Server API route definitions."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas import (
    HealthResponse,
    IndexRequest,
    IndexStatusResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    VersionResponse,
)
from app.core.config import get_settings
from app.core.security import verify_internal_token
from app.embeddings.model import (
    EmbeddingAPIError,
    EmbeddingNotConfigured,
    get_embedding_manager,
)
from app.indexing.corpus import index_chunks, load_corpus_from_url
from app.retrieval.qdrant_client import QdrantStore

logger = logging.getLogger("rag_server")
router = APIRouter()


def _get_qdrant() -> QdrantStore:
    settings = get_settings()
    return QdrantStore(
        settings.qdrant_url,
        settings.rag_collection_name,
        api_key=settings.qdrant_api_key,
    )


@router.get("/health/live")
def health_live():
    return {"status": "ok"}


@router.get("/health/ready", response_model=HealthResponse)
def health_ready():
    settings = get_settings()
    qdrant = _get_qdrant()
    embed = get_embedding_manager(settings.rag_embedding_model)

    qdrant_ok = qdrant.is_healthy()
    qdrant_status = "connected" if qdrant_ok else "unreachable"
    model_status = "ready" if embed.is_ready else "not_configured"

    if not qdrant_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"qdrant": qdrant_status, "model": model_status},
        )

    return HealthResponse(status="ready", qdrant=qdrant_status, embedding_model=model_status)


@router.get("/version", response_model=VersionResponse)
def version():
    settings = get_settings()
    return VersionResponse(
        service="rag-server",
        version=settings.app_version,
        git_sha=settings.git_sha,
        corpus_version=settings.rag_corpus_version,
        embedding_model=settings.rag_embedding_model,
    )


@router.post("/v1/search", response_model=SearchResponse, dependencies=[Depends(verify_internal_token)])
def search(req: SearchRequest):
    settings = get_settings()
    embed = get_embedding_manager(settings.rag_embedding_model)
    qdrant = _get_qdrant()

    try:
        input_type = "query" if settings.embedding_send_input_type else None
        query_vec = embed.encode([req.query], input_type=input_type)[0]
        results = qdrant.search(query_vec, top_k=req.top_k, cwe_filter=req.cwe_id)
        return SearchResponse(
            query=req.query,
            top_k=req.top_k,
            results=[SearchResultItem(**r) for r in results],
        )
    except EmbeddingNotConfigured as exc:
        logger.warning("Search unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except EmbeddingAPIError as exc:
        logger.error("Embedding provider error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding provider request failed",
        ) from exc
    except Exception as exc:
        logger.error("Search failed: %s", exc)
        raise HTTPException(status_code=500, detail="Search failed") from exc


@router.post("/v1/index", status_code=202, dependencies=[Depends(verify_internal_token)])
def trigger_index(req: IndexRequest):
    settings = get_settings()
    url = req.corpus_url or "https://huggingface.co/datasets/OMCHOKSI108/CodeSecAudit-RAG/resolve/main/rag/rag_corpus.jsonl.gz"
    try:
        chunks = load_corpus_from_url(url)
        if req.max_documents and req.max_documents > 0:
            chunks = chunks[: req.max_documents]
        embed = get_embedding_manager(settings.rag_embedding_model)
        qdrant = _get_qdrant()
        indexed = index_chunks(
            qdrant,
            embed,
            chunks,
            batch_size=settings.embedding_batch_size,
            input_type="passage" if settings.embedding_send_input_type else None,
        )
        return {"status": "indexed", "count": indexed}
    except EmbeddingNotConfigured as exc:
        logger.warning("Indexing unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except EmbeddingAPIError as exc:
        logger.error("Indexing failed (embedding provider): %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding provider request failed",
        ) from exc
    except Exception as exc:
        logger.error("Indexing failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/v1/index/status", response_model=IndexStatusResponse, dependencies=[Depends(verify_internal_token)])
def index_status():
    settings = get_settings()
    qdrant = _get_qdrant()
    count = qdrant.count()
    return IndexStatusResponse(
        collection_name=settings.rag_collection_name,
        total_documents=count,
        corpus_version=settings.rag_corpus_version,
        is_ready=count > 0,
    )
