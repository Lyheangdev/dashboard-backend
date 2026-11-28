from fastapi import APIRouter

from src.api.dependencies.authentication_deps import AuthenticationDeps, AuthenticationServiceDeps
from src.api.dependencies.authorization_deps import AuthorizationDeps
from src.api.dependencies.local_authentication_deps import AuthFormDeps
from src.domain.dtos.auth.auth_dtos import AuthUserDto, LoginDto
from src.domain.dtos.response_dtos import ApiSingletonResponse
from src.domain.enums.authorities_enum import EPermission
from src.domain.enums.endpoint_tag_enum import EApiTag
from src.infrastructure.logging.config import get_logger

logger = get_logger("Auth Resource")
router = APIRouter(prefix="/auth", tags=[EApiTag.AUTH])


# !Obtain user information
@router.get(
    "/readme",
    response_model=ApiSingletonResponse[AuthUserDto],
    dependencies=[AuthorizationDeps(permission=EPermission.ACCOUNT_READ)],
    name="Get user information",
)
async def readMe(user: AuthenticationDeps):
    response_dto = AuthUserDto.model_validate(user)
    return ApiSingletonResponse(
        status="success", message="Retrieved user information success", data=response_dto
    )


# !Login with openApi docs
@router.post("/local/login", name="Authenticate a user through OpenApi Interface")
async def localOpenApiLogin(form: AuthFormDeps, authenticationService: AuthenticationServiceDeps):
    return await authenticationService.localLogin(form)


# !Login with any kind of client
@router.post(
    "/login",
    name="Authenticate a user",
    response_model=ApiSingletonResponse[AuthUserDto],
)
async def login(form: LoginDto, authenticationService: AuthenticationServiceDeps):
    user = await authenticationService.login(form)
    return ApiSingletonResponse(status="success", message="Login successfully.", data=user)


# !Logout with any kind of client
@router.get(
    "/logout",
    response_model=ApiSingletonResponse[None],
    name="Logot authenticated user | 注销登录用户",
)
async def logout(user: AuthenticationDeps, auth_service: AuthenticationServiceDeps):
    await auth_service.logout(email=user.email)
    return ApiSingletonResponse(status="success", message="Logout success.", data=None)
