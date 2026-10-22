"""External embedding client for an OpenAI-compatible /embeddings API.

The RAG service intentionally does not ship a local model. Running
sentence-transformers locally pulled CUDA PyTorch (~3.5 GB) into the image.
Embeddings are now produced by an external provider, which keeps the service
image under the Render size budget and lets you swap providers without a rebuild.
"""

import logging
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger("rag_server")


class EmbeddingNotConfigured(RuntimeError):
    """Raised when no embedding provider is configured."""


class EmbeddingAPIError(RuntimeError):
    """Raised when the embedding provider fails or returns an invalid payload."""


class EmbeddingClient:
    def __init__(
        self,
        model_name: str,
        api_base: str,
        api_key: str = "",
        dimension: int = 1536,
        timeout: float = 30.0,
        batch_size: int = 64,
    ):
        self.model_name = model_name
        base = (api_base or "").rstrip("/")
        if not base:
            self.endpoint = ""
        elif base.endswith("/embeddings"):
            self.endpoint = base
        else:
            self.endpoint = f"{base}/embeddings"
        self.api_key = api_key
        self._dimension = dimension
        self.timeout = timeout
        self.batch_size = max(1, batch_size)
        self._http: Optional[httpx.Client] = None

    @property
    def is_ready(self) -> bool:
        return bool(self.endpoint and self.model_name)

    @property
    def dimension(self) -> int:
        return self._dimension

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=self.timeout)
        return self._http

    def encode(self, texts: list[str], input_type: Optional[str] = None) -> list[list[float]]:
        if not texts:
            return []
        if not self.is_ready:
            raise EmbeddingNotConfigured(
                "Embedding provider is not configured. Set EMBEDDING_API_BASE, "
                "EMBEDDING_MODEL and (if required) EMBEDDING_API_KEY."
            )

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            payload = {"model": self.model_name, "input": batch}
            if input_type:
                # NVIDIA NIM's asymmetric embedding models (e.g.
                # nvidia/nv-embedqa-e5-v5) need this to tell "query" text
                # apart from "passage" text; a plain OpenAI-compatible
                # provider ignores an extra field it doesn't recognize.
                payload["input_type"] = input_type
            try:
                response = self._client().post(self.endpoint, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                raise EmbeddingAPIError(f"Embedding request failed: {exc}") from exc

            if response.status_code >= 400:
                raise EmbeddingAPIError(
                    f"Embedding API returned {response.status_code}: {response.text[:300]}"
                )

            try:
                items = response.json().get("data") or []
                ordered = sorted(items, key=lambda item: item.get("index", 0))
                batch_vectors = [item["embedding"] for item in ordered]
            except (AttributeError, ValueError, KeyError, TypeError) as exc:
                raise EmbeddingAPIError("Embedding API returned an unexpected payload") from exc

            if len(batch_vectors) != len(batch) or not batch_vectors or not batch_vectors[0]:
                raise EmbeddingAPIError(
                    f"Embedding API returned {len(batch_vectors)} vectors for {len(batch)} inputs"
                )

            if self._dimension != len(batch_vectors[0]):
                logger.info(
                    "Embedding dimension detected as %s (configured %s)",
                    len(batch_vectors[0]),
                    self._dimension,
                )
                self._dimension = len(batch_vectors[0])

            vectors.extend(batch_vectors)

        return vectors


_client: Optional[EmbeddingClient] = None


def get_embedding_manager(model_name: Optional[str] = None) -> EmbeddingClient:
    """Return the process-wide embedding client (name kept for compatibility)."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = EmbeddingClient(
            model_name=model_name or settings.rag_embedding_model,
            api_base=settings.embedding_api_base,
            api_key=settings.embedding_api_key,
            dimension=settings.embedding_dim,
            timeout=settings.embedding_timeout,
            batch_size=settings.embedding_batch_size,
        )
    return _client
