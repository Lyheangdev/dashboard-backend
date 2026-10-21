from pydantic import BaseModel
from redis.asyncio import Redis

"""
@Description: Handle cache for redis and parse back as pydantic
"""


class RedisCache:
    @staticmethod
    async def setCache(
        *, redis_client: Redis, key: str, payload: BaseModel, exp: int | None = None
    ):
        parse_to_json = payload.model_dump_json()
        await redis_client.set(key=key, value=parse_to_json, ex=exp)

    @staticmethod
    async def getCache[T: BaseModel](
        *, redis_client: Redis, key: str, schema: type[T]
    ) -> T | None:
        payload = await redis_client.get(key)
        if payload is None:
            return None
        return schema.model_validate_json(schema)
