import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum

from fastapi import HTTPException, status
from pydantic import BaseModel
from redis.asyncio import Redis


class CacheManager:
    def __init__(self):
        self.redis = None

    def supplyRedis(self, redis: Redis):
        self.redis = redis

    def checkRedisInstance(self):
        if self.redis is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Not provide redis instance, please check!",
            )

    def serialize_payload(self, payload: BaseModel | object) -> str:
        if isinstance(payload, BaseModel):
            return payload.model_dump_json()

        if is_dataclass(payload):
            return json.dumps(
                asdict(payload),
                default=lambda obj: (
                    obj.isoformat()
                    if isinstance(obj, (date, datetime))
                    else obj.value
                    if isinstance(obj, Enum)
                    else str(obj)
                ),
            )
        raise TypeError(f"Unsupported payload type: {type(payload).__name__}")

    async def save_into_cache(
        self, *, key: str, payload: BaseModel, expery_time: int = 300
    ) -> None:
        self.checkRedisInstance()
        object_to_json = self.serialize_payload(payload=payload)
        await self.redis.set(name=key, value=object_to_json, ex=expery_time)

    async def wipe_out_cache(self, *, key: str) -> None:
        self.checkRedisInstance()
        await self.redis.delete(key)

    async def obtain_cache[T](self, *, key: str, parse_schema: type[T]) -> T | None:
        self.checkRedisInstance()
        payload = await self.redis.get(name=key)
        if payload is None:
            return None

        if issubclass(parse_schema, BaseModel):
            return parse_schema.model_validate_json(payload)

        if is_dataclass(parse_schema):
            return parse_schema(**json.loads(payload))

        return TypeError(f"Unsupported schema: {parse_schema}")

    async def obtain_cache_keys_by_patten(self, *, pattern: str | None = None) -> list[str]:
        self.checkRedisInstance()
        built_pattern = (
            self.redis.scan_iter() if pattern is None else self.redis.scan_iter(match=pattern)
        )
        return [key async for key in built_pattern]

    async def wipe_out_keys_by_pattern(self, *, pattern: str | None = None):
        self.checkRedisInstance()
        keys: list[str] = []
        if pattern is None:
            return
        async for key in self.redis.scan_iter(match=f"{pattern}"):
            if isinstance(key, str):
                keys.append(key)
        if len(keys) == 0:
            return
        await self.redis.delete(*keys)


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
    async def removeCache(*, redis_client: Redis, key: str):
        await redis_client.delete(key)

    @staticmethod
    async def getCache[T: BaseModel](
        *, redis_client: Redis, key: str, schema: type[T]
    ) -> T | None:
        payload = await redis_client.get(name=key)
        if payload is None:
            return None
        return schema.model_validate_json(payload)

    # @staticmethod
    # def mergeRedisCacheKey(*, key: ECacheKey, optional_key: str | None) -> str:
    #     return f"{key.value}_{optional_key}"

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
