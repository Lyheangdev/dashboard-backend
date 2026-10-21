from fastapi import APIRouter, HTTPException, Response, status
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.config.database import AlchemySession
from src.config.logging import get_logger
from src.dependencies import AuthForm, AuthGuard
from src.lib.api_auth import generateToken, verifyPassword
from src.lib.api_enum import ApiTagEnum
from src.lib.api_response import ApiSingletonResponse
from src.models.role_model import RoleModel
from src.models.user_model import UserModel
from src.schema.auth import AccessTokenScheme, AuthLogin, AuthUser

email_validator = TypeAdapter(type=EmailStr)

logger = get_logger("Auth Resource")
router = APIRouter(prefix="/auth", tags=[ApiTagEnum.AUTH])


@router.get(
    "/readme",
    response_model=ApiSingletonResponse[AuthUser],
    name="Get user info | 获取本地用户数据",
)
async def getReadme(user: AuthGuard):
    full_name = f"{user.first_name} {user.last_name}"
    logger.info(f"{full_name} attempt to get user.")

    auth_user = AuthUser(
        id=user.id,
        full_name=f"{user.first_name or None} {user.last_name or None}",
        bio=user.bio,
        profile_url=user.asset_identifier,
        role=user.role.role if user.role is not None else None,
        permissions=[permission.action for permission in (user.role.permissions or [])]
        if user.role is not None and len(user.role.permissions) > 0
        else [],
        created_at=user.created_at,
        updated_at=user.updated_at,
    )

    logger.info(f"{full_name} attempt to get user success.")
    return ApiSingletonResponse(
        status="success", message="Retrived active user successfully", data=auth_user
    )


@router.post("/local/login", name="Authenticate a user through OpenApi Interface | 登陆用户")
async def localLogin(form: AuthForm, async_session: AlchemySession):
    try:
        email_validator.validate_python(form.username)

    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username must be a valid emial!"
        )

    stmt = select(UserModel).where(UserModel.email == form.username)
    result_set = await async_session.execute(stmt)
    user = result_set.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

    if user.email != form.username or not verifyPassword(form.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials!"
        )

    # Generate short-live 30 minutes access token
    access_token = generateToken(user.id)

    return AccessTokenScheme(access_token=access_token)


@router.post(
    "/login", response_model=ApiSingletonResponse[AuthUser], name="Authenticate a user | 登录用户"
)
async def login(payload: AuthLogin, async_session: AlchemySession, response: Response):
    try:
        stmt = (
            select(UserModel)
            .where(UserModel.email == payload.email)
            .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
        )
        result_set = await async_session.execute(stmt)

        user = result_set.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        if payload.email != user.email or not verifyPassword(payload.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalide credentials!"
            )

        has_role = len(user.roles) > 0

        access_token = generateToken(user.id)

        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=1800,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
        )

        return ApiSingletonResponse(
            status="success",
            message="Login successfully.",
            data=AuthUser(
                id=user.id,
                full_name=f"{user.last_name} {user.last_name}",
                bio=user.bio,
                role=user.roles[0].role if has_role else None,
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
    except HTTPException as expt_http:
        raise expt_http


@router.get(
    "/logout",
    response_model=ApiSingletonResponse[None],
    name="Logot authenticated user | 注销登录用户",
)
async def logout(response: Response):
    response.delete_cookie(
        key="access_token", httponly=True, secure=False, samesite="lax", path="/"
    )

    return ApiSingletonResponse(
        status="success", message="You are logout successfully.", data=None
    )
