from enum import StrEnum


class RedisCacheKey(StrEnum):
    LOGIN_CACHE_KEY = "USR__README:"
    ROLE_CACHE_KEY = "USR_ROLE:"
    PERMISION_CACH_KEY = "USR_PERMISSION:"
