"""Internal authenticated client to rag-server."""

import logging
from typing import Optional
import httpx
from app.core.config import get_settings

logger = logging.getLogger("main_server")


async def query_rag_guidance(query: str, cwe_id: Optional[str] = None) -> tuple[str, str, bool]:
    settings = get_settings()
    url = f"{settings.rag_service_url.rstrip('/')}/v1/search"
    headers = {
        "X-Internal-RAG-Token": settings.rag_service_token,
        "Content-Type": "application/json",
    }
    payload = {"query": query, "top_k": 1, "cwe_id": cwe_id}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    top = results[0]
                    return top.get("guidance_text", ""), top.get("source_url", ""), True
            logger.warning(f"RAG service returned non-200 status: {resp.status_code}")
            return "", "", False
    except Exception as e:
        logger.warning(f"Failed to query RAG microservice: {e}")
        return "", "", False
