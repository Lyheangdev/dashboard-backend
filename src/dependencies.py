from collections.abc import Callable
from typing import Annotated, Literal

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.config.database import AlchemySession
from src.config.logging import get_logger, print_log
from src.config.redis import RedisClient
from src.config.security import RateLimiter
from src.lib.api_auth import JWT_ALGORITHSM, JWT_SECRET_KEY
from src.lib.api_redis_cache import RedisCache
from src.lib.authority_enum import EPermission, ERole
from src.lib.redis_key_enum import RedisCacheKey
from src.lib.user_enum import EUserStatus
from src.models.role_model import RoleModel
from src.models.user_model import UserModel
from src.schema.permission import PermissionSchema
from src.schema.role import RoleSchema
from src.schema.user import UserSchema

authorization_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/local/login", auto_error=False)


def getBearerToken(token: Annotated[str, Depends(authorization_scheme)]):
    return token


Auth = Annotated[str, Depends(getBearerToken)]
AuthForm = Annotated[OAuth2PasswordRequestForm, Depends()]

logger = get_logger("Dependency")

"""
Descripton: System authentication, all the incoming request will reach to this guard 
for the firstest
"""


async def authGuard(
    token: Auth,
    async_session: AlchemySession,
    redis: RedisClient,
    access_token: Annotated[str | None, Cookie()] = None,
) -> UserSchema:

    raiseCredentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Something went wrong with your token !",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        system_token = token or access_token

        if system_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized access, please login!",
            )

        payload = jwt.decode(
            jwt=system_token,
            key=JWT_SECRET_KEY,
            algorithms=JWT_ALGORITHSM,
            options={"require": ["sub", "exp"]},
        )

        if payload.get("type", None) != "access":
            raise raiseCredentials

        subject = payload.get("sub")
        email = payload.get("email", None)

        if not isinstance(subject, str) or not subject.isdecimal():
            raise raiseCredentials

        if email is None:
            raise raiseCredentials

        user_id = int(subject)
        email = str(email)

    except (jwt.InvalidTokenError, ValueError):
        raise raiseCredentials

    try:
        cache_key = RedisCache.mergeRedisCacheKey(
            key=RedisCacheKey.LOGIN_CACHE_KEY, optional_key=email
        )

        cache_data = await RedisCache.getCache(
            redis_client=redis, key=cache_key, schema=UserSchema
        )

        if cache_data is not None:
            return cache_data

        stmt = select(UserModel).where(UserModel.id == user_id)
        stmt = stmt.options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))

        result_set = await async_session.execute(stmt)
        user = result_set.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized user!",
            )

        if bool(user.isBanned) or user.status == EUserStatus.INACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your user is in inactive mode or got banned!"
            )

        has_role = len(user.roles) > 0
        has_permission = len(user.roles[0].permissions) > 0 if has_role else False

        if not has_role or not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lack of role and permissions!",
            )

        if bool(user.isBanned) or user.status == EUserStatus.INACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your user is in inactive mode or got banned!",
            )

    except IntegrityError as exp_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    cache_data = UserSchema(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        bio=user.bio,
        asset_identifier=user.asset_identifier,
        isBanned=user.isBanned,
        status=user.status,
        code=user.code,
        created_at=user.created_at,
        updated_at=user.updated_at,
        role=RoleSchema(
            id=user.roles[0].id,
            role=user.roles[0].role,
            permissions=[
                PermissionSchema(
                    id=permission.id, action=permission.action, resource=permission.resource
                )
                for permission in user.roles[0].permissions
            ]
            if has_role and has_permission
            else [],
        )
        if has_role
        else None,
    )

    await RedisCache.setCache(redis_client=redis, key=cache_key, payload=cache_data)
    return cache_data


def authorizeGuard(
    *,
    roles: list[ERole] | None = None,
    permission: EPermission | None = None,
    operation: Literal["AND", "OR"] = "OR",
) -> Callable:
    async def authenticate(
        authenticatedUser: Annotated[UserSchema, Depends(authGuard)],
    ) -> None:
        try:
            if authenticatedUser is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden for Unthenticated user, please login!",
                )

            has_role = roles is not None and len(roles) > 0
            has_permission = permission is not None

            if not has_role and not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden access, lack of role and permission!",
                )

            user_role = authenticatedUser.role
            user_permissions = [p.action for p in authenticatedUser.role.permissions]

            flatted_role = [r.value.lower() for r in roles]

            isAllowed_for_current_role = (
                user_role.role.lower() in flatted_role if len(flatted_role) > 0 else False
            )

            isAllowed_for_current_permission = (
                permission.value in user_permissions if permission else False
            )

            granted_access_conditions = (
                (isAllowed_for_current_role and isAllowed_for_current_permission)
                if operation == "AND"
                else (isAllowed_for_current_role or isAllowed_for_current_permission)
            )

            if not granted_access_conditions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden!"
                )

        except IntegrityError as exp_db:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=exp_db._message(),
                headers={"DATABASE_ERROR": exp_db.code},
            )

    return authenticate


AuthGuard = Annotated[UserSchema, Depends(authGuard)]


def AuthorizeGuard(
    *,
    roles: list[ERole] | None = None,
    permission: EPermission | None = None,
    operation: Literal["AND", "OR"] = "OR",
):
    return Depends(authorizeGuard(roles=roles, permission=permission, operation=operation))


# Rate limiting | allow 50 requests per minutes
global_rate_limter = RateLimiter(request_limt=60, time_window_seconds=60)
GlobalRateLimiter = Depends(global_rate_limter)
