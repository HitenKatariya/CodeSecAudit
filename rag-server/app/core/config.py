"""RAG Server configuration module."""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    git_sha: str = Field(default="local", alias="GIT_SHA")

    qdrant_url: str = Field(default="http://qdrant:6333", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    rag_service_token: str = Field(default="dev_rag_service_token_secret", alias="RAG_SERVICE_TOKEN")

    # Embeddings are produced by an external OpenAI-compatible /embeddings API.
    # This keeps the image small (no torch/CUDA/transformers). Any provider that
    # implements POST {base}/embeddings works: OpenAI, Jina, Voyage, Together,
    # Ollama, LM Studio, etc.
    rag_embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_api_base: str = Field(default="", alias="EMBEDDING_API_BASE")
    embedding_api_key: str = Field(default="", alias="EMBEDDING_API_KEY")
    embedding_dim: int = Field(default=1536, alias="EMBEDDING_DIM")
    embedding_timeout: float = Field(default=30.0, alias="EMBEDDING_TIMEOUT")
    embedding_batch_size: int = Field(default=64, alias="EMBEDDING_BATCH_SIZE")
    # NVIDIA NIM's asymmetric embedding models (e.g. nvidia/nv-embedqa-e5-v5)
    # require an input_type field (query vs passage) to embed correctly.
    # Off by default: an unknown extra field isn't guaranteed safe to send to
    # every OpenAI-compatible provider (OpenAI itself, Jina, etc.).
    embedding_send_input_type: bool = Field(default=False, alias="EMBEDDING_SEND_INPUT_TYPE")

    rag_corpus_version: str = Field(default="v1", alias="RAG_CORPUS_VERSION")
    rag_collection_name: str = Field(default="secure_guidance_v1", alias="RAG_COLLECTION_NAME")
    log_redaction_enabled: bool = Field(default=True, alias="LOG_REDACTION_ENABLED")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
