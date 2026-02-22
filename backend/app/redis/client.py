"""
Redis async client — singleton pool with graceful fallback.

If Redis is unreachable the app continues to function (presence will degrade
to in-memory / always-offline).  All public helpers swallow connection errors
and return None so callers never crash.
"""

import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_pool: aioredis.ConnectionPool | None = None
_client: aioredis.Redis | None = None


async def init_redis() -> None:
    """Create the connection pool.  Call once at app startup."""
    global _pool, _client
    if not settings.REDIS_URL:
        logger.info("REDIS_URL is empty — Redis disabled")
        return
    try:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
        _client = aioredis.Redis(connection_pool=_pool)
        await _client.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — presence/pub-sub disabled", exc)
        _client = None


async def close_redis() -> None:
    """Close the pool.  Call once at app shutdown."""
    global _pool, _client
    if _client:
        await _client.aclose()
        _client = None
    if _pool:
        await _pool.aclose()
        _pool = None


def get_redis() -> aioredis.Redis | None:
    """Return the live Redis client, or None if unavailable."""
    return _client
