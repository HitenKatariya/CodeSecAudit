"""Qdrant client and vector operations manager."""

import logging
from typing import Any, Optional

logger = logging.getLogger("rag_server")


class QdrantStore:
    def __init__(
        self,
        qdrant_url: str,
        collection_name: str = "secure_guidance_v1",
        api_key: str = "",
    ):
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.api_key = api_key or None
        self._client: Optional[Any] = None

    def get_client(self) -> Optional[Any]:
        if self._client is None:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(
                    url=self.qdrant_url,
                    api_key=self.api_key,
                    timeout=15.0,
                    check_compatibility=False,
                )
            except Exception as e:
                logger.warning(f"Could not connect to Qdrant: {e}")
                return None
        return self._client

    def is_healthy(self) -> bool:
        client = self.get_client()
        if client is None:
            return False
        try:
            client.get_collections()
            return True
        except Exception:
            return False

    def ensure_collection(self, vector_dim: int) -> None:
        client = self.get_client()
        if not client:
            return
        if vector_dim <= 0:
            raise ValueError(f"Invalid embedding dimension: {vector_dim}")

        from qdrant_client.http import models

        if client.collection_exists(self.collection_name):
            info = client.get_collection(self.collection_name)
            params = info.config.params
            vectors = getattr(params, "vectors", None)
            existing_dim = getattr(vectors, "size", None)
            if existing_dim is not None and existing_dim != vector_dim:
                raise ValueError(
                    f"Qdrant collection '{self.collection_name}' has vector size "
                    f"{existing_dim}, but the embedding provider returned {vector_dim}. "
                    "Set RAG_COLLECTION_NAME to a new name (or delete the collection) "
                    "and re-index the corpus."
                )
            return

        logger.info(f"Creating Qdrant collection {self.collection_name} (dim={vector_dim})")
        client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=vector_dim,
                distance=models.Distance.COSINE,
            ),
        )

    def search(
        self,
        query_vector: list[float],
        top_k: int = 3,
        cwe_filter: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        client = self.get_client()
        if not client:
            return []
        from qdrant_client.http import models

        query_filter = None
        if cwe_filter:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="cwe_ids",
                        match=models.MatchValue(value=cwe_filter),
                    )
                ]
            )

        try:
            if hasattr(client, "collection_exists") and not client.collection_exists(self.collection_name):
                return []
            if hasattr(client, "query_points"):
                res = client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=top_k,
                )
                results = res.points
            elif hasattr(client, "search"):
                results = client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=top_k,
                )
            else:
                return []
        except Exception as exc:
            logger.warning(f"Qdrant search failed: {exc}")
            return []

        formatted = []
        for r in results:
            payload = r.payload or {}
            formatted.append({
                "score": float(r.score),
                "document_id": str(payload.get("original_id") or r.id),
                "guidance_text": payload.get("content", ""),
                "source_url": payload.get("source_url", ""),
                "section_title": payload.get("section", ""),
                "cwe_ids": payload.get("cwe_ids", []),
                "corpus_version": payload.get("corpus_version", "v1"),
            })
        return formatted

    def count(self) -> int:
        client = self.get_client()
        if not client:
            return 0
        try:
            info = client.get_collection(self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0
