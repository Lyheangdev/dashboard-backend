from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from src.api.dependencies.authentication_deps import AuthenticationDeps
from src.api.dependencies.authorization_deps import AuthorizationDeps
from src.api.dependencies.cache_deps import CacheManagerDeps
from src.domain.dtos.response_dtos import ApiSingletonResponse
from src.domain.enums.authorities_enum import ERole
from src.domain.enums.endpoint_tag_enum import EApiTag
from src.infrastructure.logging.config import get_logger
from src.infrastructure.logging.log_context import setActorContext

logger = get_logger("Cache Resource")
router = APIRouter(prefix="/auth", tags=[EApiTag.CACHE])


# !Get all redis cache
@router.get(
    "/cache_keys",
    response_model=ApiSingletonResponse[list[str]],
    dependencies=[AuthorizationDeps(roles=[ERole.SUPERADMIN])],
    name="Get all redis cache keys",
)
async def getAllRedisCacheKeys(user: AuthenticationDeps, cache_mananger: CacheManagerDeps):
    caches = await cache_mananger.obtain_cache_keys_by_patten(pattern=None)
    setActorContext(user_id=user.id)
    return ApiSingletonResponse(
        status="success", message="Retrieved all cache keys successfully.", data=caches
    )


@router.delete(
    "/cache_keys",
    response_model=ApiSingletonResponse[None],
    dependencies=[AuthorizationDeps(roles=[ERole.SUPERADMIN])],
    name="Wipe out redis cache keys used for unlock user",
)
async def removeCahceKey(
    user: AuthenticationDeps,
    cache_mananger: CacheManagerDeps,
    pattern: Annotated[str | None, Query()] = None,
):
    if pattern is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide email of the user you want to unlock!",
        )

    await cache_mananger.wipe_out_keys_by_pattern(pattern=f"*{pattern}*")
    setActorContext(user_id=user.id)
    return ApiSingletonResponse(status="success", message="User unlock successfully.", data=None)
