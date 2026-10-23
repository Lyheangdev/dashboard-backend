from pydantic import BaseModel
from redis.asyncio import Redis

from src.lib.redis_key_enum import RedisCacheKey

"""
@Description: Handle cache for redis and parse back as pydantic
"""


class RedisCache:
    @staticmethod
    async def setCache(
        *, redis_client: Redis, key: str, payload: BaseModel, exp: int | None = None
    ):
        parse_to_json = payload.model_dump_json()
        await redis_client.set(name=key, value=parse_to_json, ex=exp)

    @staticmethod
    async def getCache[T: BaseModel](
        *, redis_client: Redis, key: str, schema: type[T]
    ) -> T | None:
        payload = await redis_client.get(name=key)
        if payload is None:
            return None
        return schema.model_validate_json(payload)

    @staticmethod
    def mergeRedisCacheKey(*, key: RedisCacheKey, optional_key: str | None) -> str:
        return f"{key.value}{optional_key}"

    @staticmethod
    async def getRedisKeysByPattern(
        *, redis: Redis, search_pattern: str | None = None
    ) -> list[str]:

        built_pattern = (
            redis.scan_iter() if search_pattern is None else redis.scan_iter(match=search_pattern)
        )

        return [key async for key in built_pattern]

    @staticmethod
    async def removeRedisKeysByPattern(
        *, redis: Redis, search_pattern: str | None = None
    ) -> None:
        keys: list[str] = []

        if search_pattern is None:
            return

        async for key in redis.scan_iter(match=f"{search_pattern}"):
            if isinstance(key, str):
                keys.append(key)

        if len(keys) == 0:
            return

        await redis.delete(*keys)
