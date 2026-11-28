import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.api.dependencies.cache_deps import RedisClientDeps
from src.api.dependencies.database_deps import AlchemySessionDeps
from src.dependencies import AuthorizeGuard
from src.domain.dtos.response_dtos import ApiCollectionResponse, ApiSingletonResponse
from src.domain.enums.authorities_enum import ERole
from src.domain.enums.cach_key_enum import ECacheKey
from src.domain.enums.endpoint_tag_enum import EApiTag
from src.domain.utils.cache.redis_helper import RedisCache
from src.domain.utils.pagination_helper import calculateOffset
from src.infrastructure.models.role.role_model import RoleModel
from src.infrastructure.models.user.user_model import UserModel
from src.schema.permission import PermissionSchema
from src.schema.role import RoleSchema
from src.schema.user import SystemAccessQueryParams, SystemAccessUserRole, UserSchema

router = APIRouter(
    prefix="/admin/system-access",
    tags=[EApiTag.SYSTEM_ACCESS],
)


@router.post(
    "",
    response_model=ApiSingletonResponse[None],
    name="Add a user to a role",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def addUserRole(
    payload: SystemAccessUserRole,
    async_session: AlchemySessionDeps,
):
    try:
        async with async_session.begin():
            stmt_user = (
                select(UserModel)
                .where(UserModel.id == payload.user_id)
                .options(selectinload(UserModel.roles))
            )
            user_result = await async_session.execute(stmt_user)

            user = user_result.scalar_one_or_none()

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
                )

            stmt_role = select(RoleModel).where(RoleModel.id == payload.role_id)
            role_result = await async_session.execute(stmt_role)

            role = role_result.scalar_one_or_none()

            if role is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Role not found!"
                )

            if len(user.roles) > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Can not link duplicate user!"
                )

            user.roles.append(role)
            async_session.add(user)

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    return ApiSingletonResponse(
        status="success",
        message=f"User {user.email} linked to role {role.role} successfully.",
        data=None,
    )


@router.put(
    "",
    response_model=ApiSingletonResponse[None],
    name="Change or update role for the user",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def updateUserRole(
    payload: SystemAccessUserRole,
    redis: RedisClientDeps,
    async_session: AlchemySessionDeps,
):
    try:
        stmt = (
            select(UserModel)
            .where(UserModel.id == payload.user_id)
            .options(selectinload(UserModel.roles))
        )

        result_set = await async_session.execute(stmt)
        user = result_set.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        old_role = user.roles[0].role if len(user.roles) > 0 else "N/A"

        # When the role is unlink, force. user to relogin
        cache_key = RedisCache.mergeRedisCacheKey(key=ECacheKey.LOGIN, optional_key=user.email)

        if len(user.roles) > 0:
            is_matched_role = any(role.id == payload.role_id for role in user.roles)

            if is_matched_role:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Role is already in used!"
                )

            user.roles.clear()

        # Look up the role to be add
        result_set_role = await async_session.execute(
            select(RoleModel).where(RoleModel.id == payload.role_id)
        )
        role = result_set_role.scalar_one_or_none()

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role is not found!"
            )

        data = {
            "type": "UNLINK_USER",
            "message": {
                "code": user.code,
                "email": user.email,
                "old_role": old_role,
                "new_role": role.role,
            },
        }

        await redis.publish("LINE_POST", message=json.dumps(data))
        await RedisCache.removeCache(redis_client=redis, key=cache_key)

        # Attach current role for current user
        user.roles.append(role)
        await async_session.commit()
        await async_session.refresh(user)

    except IntegrityError as expt_db:
        await async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    return ApiSingletonResponse(
        status="success",
        message=f"User {user.email} has been updated to role {role.role} successfully.",
        data=None,
    )


@router.get(
    "/user/{user_id}",
    response_model=ApiSingletonResponse[UserSchema],
    name="Retrive the user that linked to the role",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def getUserRole(user_id: Annotated[int, Path()], async_session: AlchemySessionDeps):
    try:
        async with async_session.begin():
            stmt = (
                select(UserModel)
                .where(UserModel.id == user_id)
                .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
            )
            result_set = await async_session.execute(stmt)
            user = result_set.scalar_one_or_none()

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
                )

            permissionDtos = (
                [
                    PermissionSchema(
                        id=permision.id, action=permision.action, resource=permision.resource
                    )
                    for permision in user.roles[0].permissions
                ]
                if user.roles[0] is not None
                else []
            )

            roleDto = RoleSchema(
                id=user.roles[0].id, role=user.roles[0].role, permissions=permissionDtos
            )

            userDto = UserSchema(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                bio=user.bio,
                asset_identifier=user.asset_identifier,
                created_at=user.created_at,
                updated_at=user.updated_at,
                role=roleDto,
            )

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    return ApiSingletonResponse(
        status="success", message="Retrieved user and role successfully.", data=userDto
    )


# --- Check this
@router.delete(
    "/user/{user_id}",
    response_model=ApiSingletonResponse[None],
    name="Unlink the user from the role",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def unLinkUserRole(
    user_id: Annotated[int, Path()],
    redis: RedisClientDeps,
    async_session: AlchemySessionDeps,
):
    try:
        async with async_session.begin():
            stmt = (
                select(UserModel)
                .where(UserModel.id == user_id)
                .options(selectinload(UserModel.roles))
            )
            result_set = await async_session.execute(stmt)

            user = result_set.scalar_one_or_none()

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
                )

            cache_key = RedisCache.mergeRedisCacheKey(
                key=ECacheKey.LOGIN, optional_key=user.email
            )

            # When the role is unlink, force. user to relogin
            await RedisCache.removeCache(redis_client=redis, key=cache_key)
            user.roles.clear()
            await async_session.flush()

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    return ApiSingletonResponse(
        status="success", message="User has already been unlinked successfully.", data=None
    )


@router.get(
    "",
    response_model=ApiCollectionResponse[UserSchema],
    name="Retrieve all binding users",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def getUsersRoles(
    query: Annotated[SystemAccessQueryParams, Query()], async_session: AlchemySessionDeps
):
    try:
        async with async_session.begin():
            stmt = select(UserModel)

            if query.role_id is None:
                stmt = stmt.where(UserModel.roles.any())

            stmt_load_role_permissions = (
                selectinload(UserModel.roles).selectinload(RoleModel.permissions)
                if query.role_id is None
                else selectinload(
                    UserModel.roles.and_(RoleModel.id == query.role_id)
                ).selectinload(RoleModel.permissions)
            )

            # paginate
            stmt = stmt.offset(calculateOffset(query.page, query.page_size)).limit(
                query.page_size
            )

            if query.role_id is not None:
                stmt = stmt.where(UserModel.roles.any(RoleModel.id == query.role_id))

            stmt = stmt.options(stmt_load_role_permissions)

            result_set = await async_session.execute(stmt)
            users_roles = result_set.scalars().all()

            user_schema = (
                [
                    UserSchema(
                        id=user.id,
                        email=user.email,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        bio=user.bio,
                        asset_identifier=user.asset_identifier,
                        role=RoleSchema(id=user.roles[0].id, role=user.roles[0].role)
                        if len(user.roles) > 0.0
                        else None,
                        created_at=user.created_at,
                        updated_at=user.updated_at,
                    )
                    for user in list(users_roles)
                ]
                if len(users_roles) > 0
                else []
            )

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    return ApiCollectionResponse(
        status="success", message="Retrieved users' roles successfully.", data=user_schema
    )
