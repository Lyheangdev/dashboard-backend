import time

from fastapi import HTTPException, Request, status

from src.config.redis import RedisClient


class RateLimiter:
    REDIS_LUA_SCRIPT = """
        local current = redis.call('INCR',KEYS[1])

        if current == 1 then
            redis.call('EXPIRE',KEYS[1],ARGV[1])
        end

        return current
    """

    def __init__(
        self,
        request_limt: int = 60,
        time_window_seconds: int = 60,
        custom_key: str | None = None,
        status_code: int = status.HTTP_429_TOO_MANY_REQUESTS,
        detail: str = "Request reached limit!",
    ):
        self.requet_limt = request_limt
        self.time_window_seconds = time_window_seconds
        self.custom_key = custom_key
        self.status_code = status_code
        self.detail = detail

    async def __call__(self, request: Request, redis: RedisClient):
        request_client_ip = request.client.host

        """
            this time() produce the fixed scalar value per minutes, 
            no matter what whin the same minute, value is the same
        """
        time_window_in_minute = int(time.time() // self.time_window_seconds)

        redis_key = (
            f"rate_limte:{request_client_ip}:{time_window_in_minute}"
            if self.custom_key is None
            else self.custom_key
        )

        current_limit_count = await redis.eval(
            self.REDIS_LUA_SCRIPT, 1, redis_key, self.time_window_seconds
        )

        if current_limit_count > self.requet_limt:
            raise HTTPException(
                status_code=self.status_code,
                detail=self.detail,
            )
