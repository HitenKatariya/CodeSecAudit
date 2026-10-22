"""Redis job queue helpers for review jobs."""

import json
from typing import Any, Optional
from app.core.config import get_settings
from app.core.redis import get_redis_service

QUEUE_KEY = "queue:review"


async def enqueue_review_job(job_data: dict[str, Any]) -> None:
    settings = get_settings()
    redis_service = get_redis_service(settings.redis_url)
    client = await redis_service.get_async()
    await client.lpush(QUEUE_KEY, json.dumps(job_data))


async def dequeue_review_job(timeout: int = 5) -> Optional[dict[str, Any]]:
    settings = get_settings()
    redis_service = get_redis_service(settings.redis_url)
    client = await redis_service.get_async()
    item = await client.brpop(QUEUE_KEY, timeout=timeout)
    if item:
        _, raw = item
        return json.loads(raw)
    return None
