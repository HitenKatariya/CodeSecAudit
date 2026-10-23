"""Main Server configuration module."""

import os
from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_main_server_url() -> str:
    # Render injects RENDER_EXTERNAL_URL; compose uses the service DNS name.
    return os.getenv("RENDER_EXTERNAL_URL", "http://main-server:8000")


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    git_sha: str = Field(default="local", alias="GIT_SHA")

    database_url: str = Field(
        default="postgresql+asyncpg://codesec:codesec_dev_password@postgres:5432/codesec",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    session_secret: str = Field(default="dev_session_secret_change_in_production_32b", alias="SESSION_SECRET")
    github_client_id: str = Field(default="", alias="GITHUB_CLIENT_ID")
    github_client_secret: str = Field(default="", alias="GITHUB_CLIENT_SECRET")
    github_app_id: str = Field(default="", alias="GITHUB_APP_ID")
    github_app_private_key: str = Field(default="", alias="GITHUB_APP_PRIVATE_KEY")
    github_webhook_secret: str = Field(default="", alias="GITHUB_WEBHOOK_SECRET")

    rag_service_url: str = Field(default="http://rag-server:8010", alias="RAG_SERVICE_URL")
    rag_service_token: str = Field(default="dev_rag_service_token_secret", alias="RAG_SERVICE_TOKEN")

    next_public_app_url: str = Field(default="http://localhost:3000", alias="NEXT_PUBLIC_APP_URL")
    main_server_url: str = Field(default_factory=_default_main_server_url, alias="MAIN_SERVER_URL")
    # Public URL GitHub redirects back to. On Render this must point at the
    # client proxy so the session cookie is set on the client origin:
    #   https://<client>.onrender.com/api/auth/github/callback
    oauth_redirect_uri: str = Field(default="", alias="OAUTH_REDIRECT_URI")

    # Free Render plans have no background workers; run the queue consumer
    # inside the web process instead. Disable when deploying a real worker.
    run_worker_inline: bool = Field(default=False, alias="RUN_WORKER_INLINE")

    log_redaction_enabled: bool = Field(default=True, alias="LOG_REDACTION_ENABLED")
    review_max_files: int = Field(default=30, alias="REVIEW_MAX_FILES")
    review_max_file_bytes: int = Field(default=204800, alias="REVIEW_MAX_FILE_BYTES")
    review_max_total_bytes: int = Field(default=1048576, alias="REVIEW_MAX_TOTAL_BYTES")
    review_timeout_seconds: int = Field(default=120, alias="REVIEW_TIMEOUT_SECONDS")

    pr_agent_review_enabled: bool = Field(default=False, alias="PR_AGENT_REVIEW_ENABLED")
    # Model string format is litellm's <provider>/<model> (see
    # docs/PR_AGENT_INTEGRATION_GUIDE.md section 5). Groq first (free, fast),
    # falling back through NVIDIA NIM then Hugging Face if Groq errors out or
    # rate-limits - retry_with_fallback_models() in pr_agent walks this list
    # in order and only advances on failure.
    pr_agent_model: str = Field(default="groq/llama-3.3-70b-versatile", alias="PR_AGENT_MODEL")
    pr_agent_fallback_models: str = Field(
        default="nvidia_nim/meta/llama-3.1-70b-instruct,huggingface/meta-llama/Llama-3.1-8B-Instruct",
        alias="PR_AGENT_FALLBACK_MODELS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        """Render hands out postgres:// or postgresql:// URLs; SQLAlchemy needs +asyncpg."""
        if isinstance(value, str):
            if value.startswith("postgres://"):
                return "postgresql+asyncpg://" + value[len("postgres://") :]
            if value.startswith("postgresql://"):
                return "postgresql+asyncpg://" + value[len("postgresql://") :]
        return value

    @field_validator("rag_service_url", "main_server_url", mode="before")
    @classmethod
    def _ensure_internal_scheme(cls, value: str) -> str:
        """Render's fromService hostport property has no scheme; add one."""
        if isinstance(value, str) and value:
            clean = value.strip().lower()
            if clean.startswith("codesec-main") or clean == "codesec-main:10000":
                return "https://codesec-main.onrender.com"
            if clean.startswith("codesec-rag") or clean == "codesec-rag:10000":
                return "https://codesec-rag.onrender.com"
            if not value.startswith(("http://", "https://")):
                return f"http://{value}"
        return value

    @field_validator("next_public_app_url", "oauth_redirect_uri", mode="before")
    @classmethod
    def _ensure_public_scheme(cls, value: str) -> str:
        """Public URLs are HTTPS unless they point at localhost."""
        if not isinstance(value, str) or not value:
            return value
        clean = value.strip().lower()
        if clean.startswith("codesec-client") or clean == "codesec-client:10000":
            return "https://codesec-client.onrender.com"
        if value.startswith(("http://", "https://")):
            return value
        host = value.split("/", 1)[0].split(":", 1)[0]
        scheme = "http" if host in {"localhost", "127.0.0.1", "::1"} else "https"
        return f"{scheme}://{value}"

    @property
    def github_oauth_redirect_uri(self) -> str:
        # Falls back to the CLIENT's public URL + its proxy prefix (/api/* ->
        # /v1/* via client/src/lib/proxy.ts), not main_server_url directly -
        # the session cookie must land on the client origin the browser
        # actually talks to, or the browser never sends it back (see
        # proxy.ts's own comment on this exact requirement).
        return self.oauth_redirect_uri or f"{self.next_public_app_url.rstrip('/')}/api/auth/github/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
