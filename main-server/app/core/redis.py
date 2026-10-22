"""Redis connection pool, session manager, rate limiter, and log streamer."""

import json
from typing import Any, Optional
import redis
import redis.asyncio as aioredis


class RedisService:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._async_client: Optional[aioredis.Redis] = None
        self._sync_client: Optional[redis.Redis] = None

    def get_sync(self) -> redis.Redis:
        if self._sync_client is None:
            self._sync_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        return self._sync_client

    async def get_async(self) -> aioredis.Redis:
        if self._async_client is None:
            self._async_client = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._async_client

    async def is_healthy(self) -> bool:
        try:
            client = await self.get_async()
            return await client.ping()
        except Exception:
            return False

    async def set_session(self, session_id: str, data: dict[str, Any], ttl_seconds: int = 86400) -> None:
        client = await self.get_async()
        await client.setex(f"session:{session_id}", ttl_seconds, json.dumps(data))

    async def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        client = await self.get_async()
        raw = await client.get(f"session:{session_id}")
        return json.loads(raw) if raw else None

    async def delete_session(self, session_id: str) -> None:
        client = await self.get_async()
        await client.delete(f"session:{session_id}")

    async def is_webhook_processed(self, delivery_id: str, ttl_seconds: int = 86400) -> bool:
        client = await self.get_async()
        key = f"webhook:{delivery_id}"
        is_new = await client.set(key, "1", nx=True, ex=ttl_seconds)
        return not bool(is_new)

    async def check_rate_limit(self, scope: str, key: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        client = await self.get_async()
        redis_key = f"rate:{scope}:{key}"
        current = await client.incr(redis_key)
        if current == 1:
            await client.expire(redis_key, window_seconds)
        return current <= max_requests

    async def tail_log_stream(self, stream_key: str, limit: int = 100) -> list[dict[str, Any]]:
        client = await self.get_async()
        try:
            entries = await client.xrevrange(stream_key, count=limit)
            results = []
            for entry_id, fields in entries:
                results.append({"id": entry_id, **fields})
            return results
        except Exception:
            return []


_redis_service: Optional[RedisService] = None


def get_redis_service(redis_url: str) -> RedisService:
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService(redis_url)
    return _redis_service
