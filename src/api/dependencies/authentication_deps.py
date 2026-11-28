from typing import Annotated

from fastapi import Cookie, Depends, Request, Response
from fastapi.security import OAuth2PasswordBearer

from src.api.dependencies.cache_deps import CacheManagerDeps, RedisClientDeps
from src.api.dependencies.database_deps import AlchemySessionDeps
from src.domain.entities.user_entity import UserEntity
from src.domain.services.authentication_service import (
    AuthenticationGuardService,
    AuthenticationService,
)

authorization_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/local/login", auto_error=False)


def getBearerToken(token: Annotated[str, Depends(authorization_scheme)]):
    return token


BearTokenAuthDeps = Annotated[str, Depends(getBearerToken)]


# Authentication service deps
async def get_authentication_service(
    request: Request,
    response: Response,
    redis: RedisClientDeps,
    async_session: AlchemySessionDeps,
    cache_manager: CacheManagerDeps,
):
    return AuthenticationService(
        request=request,
        response=response,
        redis=redis,
        async_session=async_session,
        cache_manager=cache_manager,
    )


AuthenticationServiceDeps = Annotated[AuthenticationService, Depends(get_authentication_service)]


# Authentication guard service deps
async def get_authentication_guard_service(
    openapi_access_token: BearTokenAuthDeps,
    async_session: AlchemySessionDeps,
    cache_manager: CacheManagerDeps,
    access_token: Annotated[str | None, Cookie()] = None,
) -> UserEntity:
    authenticationGuardService = AuthenticationGuardService(
        async_session=async_session, cache_manager=cache_manager
    )
    user = await authenticationGuardService.authenticate(
        openapi_access_token=openapi_access_token, client_access_token=access_token
    )
    return user


# -- This deps will provide userEntity obj
AuthenticationDeps = Annotated[UserEntity, Depends(get_authentication_guard_service)]
