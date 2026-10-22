"""Corpus loading and index ingestion."""

import gzip
import json
import logging
import uuid
from typing import Any, Optional

import httpx

logger = logging.getLogger("rag_server")


def load_corpus_from_url(url: str) -> list[dict[str, Any]]:
    logger.info(f"Downloading RAG corpus from {url}")
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        raw_bytes = resp.content

    if url.endswith(".gz"):
        raw_text = gzip.decompress(raw_bytes).decode("utf-8")
    else:
        raw_text = raw_bytes.decode("utf-8")

    chunks = []
    for line in raw_text.splitlines():
        line = line.strip()
        if line:
            chunks.append(json.loads(line))
    logger.info(f"Loaded {len(chunks)} documents from corpus")
    return chunks


def index_chunks(
    qdrant_store,
    embedding_mgr,
    chunks: list[dict[str, Any]],
    batch_size: int = 64,
    input_type: Optional[str] = None,
) -> int:
    try:
        from qdrant_client.http import models
    except ImportError:
        logger.error("qdrant-client is not installed")
        return 0

    client = qdrant_store.get_client()
    if not client:
        return 0

    total_indexed = 0
    collection_ready = False

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [b.get("content", "") or b.get("text", "") for b in batch]
        vectors = embedding_mgr.encode(texts, input_type=input_type)

        # The embedding dimension is only known after the provider responds.
        # Create/validate the collection on the first batch so the configured
        # default cannot clash with the provider's actual output.
        if not collection_ready:
            qdrant_store.ensure_collection(vector_dim=len(vectors[0]))
            collection_ready = True

        points = []
        for doc, vec in zip(batch, vectors):
            raw_id = str(doc.get("id") or "")
            try:
                doc_id = str(uuid.UUID(raw_id))
            except ValueError:
                doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_id)) if raw_id else str(uuid.uuid4())

            cwe_id = doc.get("cwe_id", "")
            cwe_list = [cwe_id] if isinstance(cwe_id, str) and cwe_id else (cwe_id or [])

            payload = {
                "original_id": raw_id,
                "title": doc.get("title", ""),
                "section": doc.get("section_title", "") or doc.get("section", ""),
                "content": doc.get("content", "") or doc.get("text", ""),
                "source_url": doc.get("source_file", "") or doc.get("source", ""),
                "cwe_ids": cwe_list,
                "corpus_version": "v1",
            }

            points.append(
                models.PointStruct(
                    id=doc_id,
                    vector=vec,
                    payload=payload,
                )
            )

        client.upsert(collection_name=qdrant_store.collection_name, points=points)
        total_indexed += len(points)

    logger.info(f"Successfully indexed {total_indexed} points into Qdrant")
    return total_indexed
