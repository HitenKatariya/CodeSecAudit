"""Pydantic schemas for RAG Server endpoints."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    qdrant: str = "unknown"
    embedding_model: str = "unknown"


class VersionResponse(BaseModel):
    service: str = "rag-server"
    version: str = "0.1.0"
    git_sha: str = "local"
    corpus_version: str = "v1"
    embedding_model: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, description="Security issue or query to search")
    top_k: int = Field(default=3, ge=1, le=20)
    cwe_id: Optional[str] = Field(default=None)


class SearchResultItem(BaseModel):
    score: float
    document_id: str
    guidance_text: str
    source_url: str
    section_title: str
    cwe_ids: list[str] = Field(default_factory=list)
    corpus_version: str = "v1"


class SearchResponse(BaseModel):
    query: str
    top_k: int
    results: list[SearchResultItem]


class IndexRequest(BaseModel):
    corpus_url: Optional[str] = None
    max_documents: Optional[int] = None


class IndexStatusResponse(BaseModel):
    collection_name: str
    total_documents: int
    corpus_version: str
    is_ready: bool
