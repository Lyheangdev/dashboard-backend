import jwt
from fastapi import HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr, TypeAdapter, ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.dapter.user_model_entity_adapter import user_model_entity_adapter
from src.domain.dtos.auth.auth_dtos import AuthUserDto, LocalAccessTokenDto, LoginDto
from src.domain.entities.user_entity import UserEntity
from src.domain.enums.authorities_enum import EResource
from src.domain.utils.cache.redis_helper import CacheManager
from src.domain.utils.security.jwt_security_helper import (
    JWT_ALGORITHSM,
    JWT_SECRET_KEY,
    generateToken,
)
from src.domain.utils.security.rate_limit_helper import RateLimiter
from src.infrastructure.logging.log_context import setActorContext
from src.infrastructure.repositories.user.user_repository import UserRepositoy

email_validator = TypeAdapter(type=EmailStr)


class AuthenticationService:
    def __init__(
        self,
        async_session: AsyncSession,
        request: Request,
        response: Response,
        redis: Redis,
        cache_manager: CacheManager,
    ):
        self.request = request
        self.response = response
        self.redis = redis
        self.async_session = async_session
        self.cache_manager = cache_manager

    def __checkDependenciesSupplied(self):
        if (
            self.async_session is None
            or self.request is None
            or self.response is None
            or self.redis is None
            or self.cache_manager is None
        ):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="[AutenticationService]: missing dependencies provided.",
            )

    async def __checkLoginAttemp(self, rate_limit_key: str, request: Request, redis: Redis):
        runChecker = RateLimiter(
            request_limit=3,
            time_window_seconds=5 * 60,
            custom_key=rate_limit_key,
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You got locked by system within 5 minutes!",
        )
        await runChecker(redis=redis, request=request)

    # OpenApi login
    async def localLogin(self, form: OAuth2PasswordRequestForm):
        """
        @description: login through openApi docs

        @params: form[username: str, password: str]

        @return: LocalAccessTokenDto
        """

        self.__checkDependenciesSupplied()
        email = form.username
        password = form.password
        rate_limit_key = f"rate_limit_{EResource.LOGIN.value.lower()}_{email}"

        try:
            email_validator.validate_python(email)
        except ValidationError:
            await self.__checkLoginAttemp(
                rate_limit_key=rate_limit_key, request=self.request, redis=self.redis
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid emial!")

        async with self.async_session.begin():
            repository = UserRepositoy(self.async_session)
            user_model = await repository.findUserByEmail(email)

        user = user_model_entity_adapter(user=user_model)

        if not user.hasUser:
            await self.__checkLoginAttemp(
                rate_limit_key=rate_limit_key, request=self.request, redis=self.redis
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        if not user.checkIsCredentialsVerified(email=email, password=password):
            await self.__checkLoginAttemp(
                rate_limit_key=rate_limit_key, request=self.request, redis=self.redis
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials!"
            )

        # Generate short-live 30 minutes access token
        access_token = generateToken(user_id=user.id, email=email)
        setActorContext(user_id=user.id)
        return LocalAccessTokenDto(access_token=access_token)

    async def login(self, form: LoginDto) -> AuthUserDto:
        """
        @description: Login any client device

        @params: form[email: str , password: str]

        @return: AuthUserDto
        """

        self.__checkDependenciesSupplied()

        email = form.email
        password = form.password
        rate_limit_key = f"rate_limit_{EResource.LOGIN.value.lower()}_{email}"

        async with self.async_session.begin():
            repo = UserRepositoy(self.async_session)
            user_model = await repo.findUserByEmail(email)

        user = user_model_entity_adapter(user=user_model)

        if not user.hasUser:
            await self.__checkLoginAttemp(
                rate_limit_key=rate_limit_key, request=self.request, redis=self.redis
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        if not user.checkIsCredentialsVerified(email=email, password=password):
            await self.__checkLoginAttemp(
                rate_limit_key=rate_limit_key, request=self.request, redis=self.redis
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalide credentials!"
            )

        if user.checkIsInactive:
            await self.__checkLoginAttemp(
                rate_limit_key=rate_limit_key, request=self.request, redis=self.redis
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please contact super admin to activate your account!",
            )

        if user.checkIsBanned:
            await self.__checkLoginAttemp(
                rate_limit_key=rate_limit_key, request=self.request, redis=self.redis
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Contact admin please, your account got banned!",
            )

        if not user.checkHasRole:
            await self.__checkLoginAttemp(
                rate_limit_key=rate_limit_key, request=self.request, redis=self.redis
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access restricted due to lack of role and permissions!",
            )

        access_token = generateToken(user_id=user.id, email=user.email)

        self.response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=1800,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
        )

        setActorContext(user_id=user.id)
        response_dto = AuthUserDto.model_validate(user)
        return response_dto

    async def logout(self, email: str | None):
        """
        @description: Logout system

        @params: email: str | None

        @return: None
        """
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unthenticated user is trying to logout!",
            )
        cache_key = f"{EResource.LOGIN.value}_{email}"
        await self.cache_manager.wipe_out_cache(key=cache_key)
        self.response.delete_cookie(
            key="access_token", httponly=True, secure=False, samesite="lax", path="/"
        )


class AuthenticationGuardService:
    def __init__(
        self,
        async_session: AsyncSession,
        cache_manager: CacheManager,
    ):
        self.async_session = async_session
        self.cache_manager = cache_manager

    def __checkDependenciesSupplied(self):
        if self.async_session is None or self.cache_manager is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="[AutenticationService]: missing dependencies provided.",
            )

    def __raise_credentials_error(self):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Something went wrong with your token !",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async def authenticate(
        self, *, openapi_access_token: str | None, client_access_token: str | None
    ) -> UserEntity:
        """
        @description: pre-check authenticated user from http-header attached token.

        @params: openapi_access_token: str | None, client_access_token: str | None

        @return: UserEntity
        """
        try:
            self.__checkDependenciesSupplied()
            access_token = openapi_access_token or client_access_token

            if access_token is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized access, please login!",
                )

            payload = jwt.decode(
                jwt=access_token,
                key=JWT_SECRET_KEY,
                algorithms=JWT_ALGORITHSM,
                options={"require": ["sub", "exp"]},
            )

            if payload.get("type", None) != "access":
                self.__raise_credentials_error()

            subject = payload.get("sub")
            email = payload.get("email", None)

            if (not isinstance(subject, str) or not subject.isdecimal()) or email is None:
                self.__raise_credentials_error()

            user_id = int(subject)
            email = str(email)

            cache_key = f"{EResource.LOGIN.value}_{email}"

            cache_data = await self.cache_manager.obtain_cache(
                key=cache_key, parse_schema=UserEntity
            )

            if cache_data is not None:
                return cache_data

            async with self.async_session.begin():
                repo = UserRepositoy(self.async_session)
                user_model = await repo.findUserById(user_id)

            user = user_model_entity_adapter(user_model)

            if not user.hasUser:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found!",
                )

            await self.cache_manager.save_into_cache(key=cache_key, payload=user)

        except (jwt.InvalidTokenError, ValueError):
            self.__raise_credentials_error()

        return user
