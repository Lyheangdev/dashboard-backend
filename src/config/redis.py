import sys
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis

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

        logger.info("🏁 Redis start.")

    async def releaseRedisClient(self):
        await self.redis_client.aclose()
        logger.info("🔚 Redis released.")


def redis_client(request: Request):
    try:
        redis: RedisConnector = request.app.state.redis_instance
        yield redis.redis_client

    except Exception as error:
        raise error


# Redis client dependency
RedisClient = Annotated[Redis, Depends(redis_client)]
