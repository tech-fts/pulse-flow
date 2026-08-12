from functools import lru_cache
from typing import AsyncGenerator

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_pool() -> ConnectionPool:
    """Lazily create and cache the Redis connection pool.

    ``lru_cache`` ensures the pool is a singleton created on first use,
    not at import time — so a missing Redis won't block app startup.
    """
    return ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis_client() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency: yields a Redis client backed by the shared pool."""
    client = Redis(connection_pool=_get_pool())
    try:
        yield client
    finally:
        await client.aclose()  # type: ignore[attr-defined]


async def get_redis() -> Redis:
    """Direct Redis client for workers and non-Depends call sites."""
    return Redis(connection_pool=_get_pool())
