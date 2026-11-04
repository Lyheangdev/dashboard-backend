from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.config.logging import get_logger

"""
@Description: Redis service connection setup !
"""

logger = get_logger(__name__)


class RedisConnector:
    HOST = "localhost"
    PORT = 6379
    PASSWORD = "sviaec_dashboard"
    DECODE_RESPONSE = True

    def __init__(self):
        # Check whether redis client hasn't initialize

        self.redis_client = Redis(
            host=self.HOST,
            port=self.PORT,
            password=self.PASSWORD,
            decode_responses=self.DECODE_RESPONSE,
        )

        logger.info("✅ Redis start successfully.")

    async def releaseRedisClient(self):
        await self.redis_client.aclose()
        logger.info("🔚 Redis released.")

    async def initRedisConnection(self):
        try:
            await self.redis_client.ping()
            logger.info("✅ Redis connection is healthy.")

        except RedisError:
            logger.exception("⛔ Redis connection failed, check in [RedisConnector].")


async def redis_client(request: Request):
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
RedisClient = Annotated[Redis, Depends(redis_client)]
