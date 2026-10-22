"""Index the RAG corpus into Qdrant outside the HTTP request path.

Render HTTP requests are short-lived (about 100s), so a full corpus re-index
can time out when triggered through ``POST /v1/index``. Run this script in a
Render job/shell instead:

    python scripts/index_corpus.py
    python scripts/index_corpus.py --corpus-url https://... --max-documents 500
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings  # noqa: E402
from app.core.logging import setup_logger  # noqa: E402
from app.embeddings.model import EmbeddingNotConfigured, get_embedding_manager  # noqa: E402
from app.indexing.corpus import index_chunks, load_corpus_from_url  # noqa: E402
from app.retrieval.qdrant_client import QdrantStore  # noqa: E402

DEFAULT_CORPUS_URL = (
    "https://huggingface.co/datasets/OMCHOKSI108/CodeSecAudit-RAG/"
    "resolve/main/rag/rag_corpus.jsonl.gz"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Index the RAG corpus into Qdrant.")
    parser.add_argument("--corpus-url", default=DEFAULT_CORPUS_URL)
    parser.add_argument("--max-documents", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=0)
    args = parser.parse_args()

    settings = get_settings()
    setup_logger(settings.redis_url)
    logger = logging.getLogger("rag_server")

    embed = get_embedding_manager(settings.rag_embedding_model)
    if not embed.is_ready:
        logger.error(
            "Embedding provider is not configured. Set EMBEDDING_API_BASE, "
            "EMBEDDING_MODEL and EMBEDDING_API_KEY."
        )
        return 2

    try:
        chunks = load_corpus_from_url(args.corpus_url)
        if args.max_documents > 0:
            chunks = chunks[: args.max_documents]
        if not chunks:
            logger.error("Corpus is empty; nothing to index")
            return 1

        qdrant = QdrantStore(
            settings.qdrant_url,
            settings.rag_collection_name,
            api_key=settings.qdrant_api_key,
        )
        batch_size = args.batch_size or settings.embedding_batch_size
        count = index_chunks(
            qdrant, embed, chunks, batch_size=batch_size,
            input_type="passage" if settings.embedding_send_input_type else None,
        )
        logger.info("Indexed %s chunks into %s", count, settings.rag_collection_name)
        return 0
    except EmbeddingNotConfigured as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI should surface the message
        logger.exception("Indexing failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
