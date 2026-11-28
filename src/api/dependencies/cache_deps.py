from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.domain.utils.cache.redis_helper import CacheManager
from src.infrastructure.cache.connection import RedisConnector
from src.infrastructure.logging.config import get_logger

logger = get_logger(__name__)


async def get_redis_client(request: Request):
    try:
        redis: RedisConnector = request.app.state.redis_instance
        await redis.redis_client.ping()
        return redis.redis_client

    except RedisError:
        logger.exception("⛔ Redis connection failed, check in [RedisConnector].")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service is unavailable or failed, check in [RedisConnector].",
        )


# Redis client dependency
RedisClientDeps = Annotated[Redis, Depends(get_redis_client)]


# Cache manager dependency
def get_cache_manager(request: Request, redis_client: RedisClientDeps):
    cache_manager: CacheManager = request.app.state.cache_manager
    cache_manager.supplyRedis(redis_client)
    return cache_manager


CacheManagerDeps = Annotated[CacheManager, Depends(get_cache_manager)]
