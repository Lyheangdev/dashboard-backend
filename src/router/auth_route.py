from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Query, Request, Response, status
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.config.database import AlchemySession
from src.config.logging import get_logger, print_log
from src.config.redis import RedisClient
from src.config.security import RateLimiter
from src.dependencies import AuthForm, AuthGuard, AuthorizeGuard
from src.lib.api_auth import generateToken, verifyPassword
from src.lib.api_enum import ApiTagEnum
from src.lib.api_redis_cache import RedisCache
from src.lib.api_response import ApiSingletonResponse
from src.lib.authority_enum import EResource, ERole
from src.models.role_model import RoleModel
from src.models.user_model import UserModel
from src.schema.auth import AccessTokenScheme, AuthLogin, AuthUserSchema

email_validator = TypeAdapter(type=EmailStr)

logger = get_logger("Auth Resource")
router = APIRouter(prefix="/auth", tags=[ApiTagEnum.AUTH])


@router.get(
    "/readme",
    response_model=ApiSingletonResponse[AuthUserSchema],
    name="Get user info | 获取本地用户数据",
)
async def getReadme(user: AuthGuard):

    # * Reuse cache from auth
    cache_data = AuthUserSchema(
        id=user.id,
        full_name=f"{user.first_name or None} {user.last_name or None}",
        bio=user.bio,
        profile_url=user.asset_identifier,
        code=user.code,
        status=user.status,
        isBanned=user.isBanned,
        role=user.role.role if user.role is not None else None,
        permissions=[permission.action for permission in (user.role.permissions or [])]
        if user.role is not None and len(user.role.permissions) > 0
        else [],
        created_at=user.created_at,
        updated_at=user.updated_at,
    )

    return ApiSingletonResponse(
        status="success", message="Retrived active user successfully", data=cache_data
    )


@router.post("/local/login", name="Authenticate a user through OpenApi Interface | 登陆用户")
async def localLogin(
    request: Request, redis: RedisClient, form: AuthForm, async_session: AlchemySession
):
    try:
        loginCheckAttempt = RateLimiter(
            request_limt=3,
            time_window_seconds=5 * 60,
            custom_key=f"{EResource.LOGIN.value}:{form.username}",
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You got locked by system!",
        )

        email_validator.validate_python(form.username)

    except ValidationError:
        if form.username != "superadmin@sviaec.com":
            await loginCheckAttempt(request=request, redis=redis)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username must be a valid emial!"
        )

    stmt = select(UserModel).where(UserModel.email == form.username)
    result_set = await async_session.execute(stmt)
    user = result_set.scalar_one_or_none()

    if user is None:
        if form.username != "superadmin@sviaec.com":
            await loginCheckAttempt(request=request, redis=redis)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

    if user.email != form.username or not verifyPassword(form.password, user.password):
        if form.username != "superadmin@sviaec.com":
            await loginCheckAttempt(request=request, redis=redis)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials!"
        )

    # Generate short-live 30 minutes access token
    access_token = generateToken(user_id=user.id, email=user.email)

    return AccessTokenScheme(access_token=access_token)


@router.post(
    "/login",
    response_model=ApiSingletonResponse[AuthUserSchema],
    name="Authenticate a user | 登录用户",
)
async def login(
    payload: AuthLogin,
    async_session: AlchemySession,
    request: Request,
    redis: RedisClient,
    response: Response,
):
    loginCheckAttempt = RateLimiter(
        request_limt=3,
        time_window_seconds=5 * 60,
        custom_key=f"{EResource.LOGIN.value}:{payload.email}",
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You got locked by system!",
    )

    try:
        stmt = (
            select(UserModel)
            .where(UserModel.email == payload.email)
            .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
        )

        result_set = await async_session.execute(stmt)
        user = result_set.scalar_one_or_none()

        if user is None:
            if payload.email != "superadmin@sviaec.com":
                await loginCheckAttempt(request=request, redis=redis)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        if payload.email != user.email or not verifyPassword(payload.password, user.password):
            if payload.email != "superadmin@sviaec.com":
                await loginCheckAttempt(request=request, redis=redis)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalide credentials!"
            )

        has_role = len(user.roles) > 0
        access_token = generateToken(user_id=user.id, email=user.email)

        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=1800,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
        )

        print_log(
            name=EResource.LOGIN.value,
            type="info",
            fname=user.first_name,
            lname=user.last_name,
            msg="User logged in [success].",
        )

        return ApiSingletonResponse(
            status="success",
            message="Login successfully.",
            data=AuthUserSchema(
                id=user.id,
                full_name=f"{user.last_name} {user.last_name}",
                bio=user.bio,
                role=user.roles[0].role if has_role else None,
                code=user.code,
                status=user.status,
                isBanned=user.isBanned,
                permissions=[permission.action for permission in (user.roles[0].permissions)]
                if has_role
                else [],
                profile_url=user.asset_identifier,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )

    except IntegrityError as expt_db:
        await async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )


@router.get(
    "/logout",
    response_model=ApiSingletonResponse[None],
    name="Logot authenticated user | 注销登录用户",
)
async def logout(cur_user: AuthGuard, response: Response):
    if cur_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unthenticated user is trying to logout!",
        )

    response.delete_cookie(
        key="access_token", httponly=True, secure=False, samesite="lax", path="/"
    )

    return ApiSingletonResponse(
        status="success", message="You are logout successfully.", data=None
    )


@router.get(
    "/cache_keys",
    response_model=ApiSingletonResponse[list[str]],
    name="Get all cache key",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def getCacheKeys(
    cur_user: AuthGuard, redis: RedisClient, search_pattern: Annotated[str | None, Query()] = None
):
    data_cache = await RedisCache.getRedisKeysByPattern(
        redis=redis, search_pattern=search_pattern
    )
    print_log(
        name=EResource.SYSTEM_ACCESS.value,
        type="info",
        fname=cur_user.first_name,
        lname=cur_user.last_name,
        msg="get all cache keys [success]",
    )
    return ApiSingletonResponse(
        status="success", message="Retrieved all cache keys successfully.", data=data_cache
    )


@router.delete(
    "/remove_cache_key",
    response_model=ApiSingletonResponse[None],
    name="Unlock login user",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def removeCahceKey(
    cur_user: AuthGuard, search_pattern: Annotated[str, Body], redis: RedisClient
):
    await RedisCache.removeRedisKeysByPattern(redis=redis, search_pattern=f"*{search_pattern}*")

    print_log(
        name=EResource.SYSTEM_ACCESS.value,
        type="info",
        fname=cur_user.first_name,
        lname=cur_user.last_name,
        msg="remove cache keys [success]",
    )
    return ApiSingletonResponse(status="success", message="Unlock successfully.", data=None)
