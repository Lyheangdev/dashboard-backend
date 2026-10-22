from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.config.database import AlchemySession
from src.lib.api_enum import ApiTagEnum
from src.lib.api_response import ApiCollectionResponse, ApiSingletonResponse
from src.lib.utils import calculateOffset
from src.models.role_model import RoleModel
from src.models.user_model import UserModel
from src.schema.permission import PermissionSchema
from src.schema.role import RoleSchema
from src.schema.user import SystemAccessQueryParams, UserSchema

router = APIRouter(
    prefix="/admin/system-access",
    tags=[ApiTagEnum.SYSTEM_ACCESS],
)


@router.post(
    "/user/{user_id}/role/{role_id}",
    response_model=ApiSingletonResponse[None],
    name="给用户添加作用 ｜ Add role to a user",
)
async def addUserRole(
    user_id: Annotated[int, Path()],
    role_id: Annotated[int, Path()],
    async_session: AlchemySession,
):
    try:
        stmt_user = (
            select(UserModel)
            .where(UserModel.id == user_id)
            .options(selectinload(UserModel.roles))
        )
        user_result = await async_session.execute(stmt_user)

        user = user_result.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        stmt_role = select(RoleModel).where(RoleModel.id == role_id)
        role_result = await async_session.execute(stmt_role)

        role = role_result.scalar_one_or_none()

        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found!")

        if len(user.roles) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Can not link duplicate user!"
            )

        user.roles.append(role)
        async_session.add(user)
        await async_session.commit()

        return ApiSingletonResponse(
            status="success",
            message=f"User {user.email} linked to role {role.role} successfully.",
            data=None,
        )

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )
    except HTTPException as expt_http:
        raise expt_http


@router.put(
    "/user/{user_id}/role/{role_id}",
    response_model=ApiSingletonResponse[None],
    name="Update user role",
)
async def updateUserRole(
    user_id: Annotated[int, Path()],
    role_id: Annotated[int, Path()],
    async_session: AlchemySession,
):
    try:
        stmt = (
            select(UserModel)
            .where(UserModel.id == user_id)
            .options(selectinload(UserModel.roles))
        )

        result_set = await async_session.execute(stmt)
        user = result_set.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        if len(user.roles) > 0:
            is_matched_role = any(role.id == role_id for role in user.roles)

            if is_matched_role:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Role is already in used!"
                )

            user.roles.clear()

        # Look up the role to be add
        result_set_role = await async_session.execute(
            select(RoleModel).where(RoleModel.id == role_id)
        )
        role = result_set_role.scalar_one_or_none()

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role is not found!"
            )

        # Attach current role for current user
        user.roles.append(role)

        await async_session.commit()
        await async_session.refresh(user)

        return ApiSingletonResponse(
            status="success",
            message=f"User {user.email} has been updated to role {role.role} successfully.",
            data=None,
        )

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )
    except HTTPException as expt_http:
        raise expt_http


@router.get(
    "/user/{user_id}", response_model=ApiSingletonResponse[UserSchema], name="A User and role"
)
async def getUserRole(user_id: Annotated[int, Path()], async_session: AlchemySession):
    try:
        stmt = (
            select(UserModel)
            .where(UserModel.id == user_id)
            .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
        )
        result_set = await async_session.execute(stmt)
        user = result_set.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

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

        return ApiSingletonResponse(
            status="success", message="Retrieved user and role successfully.", data=userDto
        )
    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )
    except HTTPException as expt_http:
        raise expt_http


@router.delete(
    "/user/{user_id}/",
    response_model=ApiSingletonResponse[None],
    name="Unlink user and role",
)
async def unLinkUserRole(
    user_id: Annotated[int, Path()],
    async_session: AlchemySession,
):

    try:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result_set = await async_session.execute(stmt)

        user = result_set.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        await async_session.delete(user)
        await async_session.commit()

        return ApiSingletonResponse(
            status="success", message="User has already been unlinked successfully.", data=None
        )

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )
    except HTTPException as expt_http:
        raise expt_http


@router.get(
    "",
    response_model=ApiCollectionResponse[UserSchema],
    name="Get users and roles",
)
async def getUsersRoles(
    query: Annotated[SystemAccessQueryParams, Query()], async_session: AlchemySession
):
    try:
        stmt = select(UserModel)

        if query.role_id is None:
            stmt = stmt.where(UserModel.roles.any())

        stmt_load_role_permissions = (
            selectinload(UserModel.roles).selectinload(RoleModel.permissions)
            if query.role_id is None
            else selectinload(UserModel.roles.and_(RoleModel.id == query.role_id)).selectinload(
                RoleModel.permissions
            )
        )

        # paginate
        stmt = stmt.offset(calculateOffset(query.page, query.page_size)).limit(query.page_size)

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

        return ApiCollectionResponse(
            status="success", message="Retrieved users' roles successfully.", data=user_schema
        )

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )
    except HTTPException as expt_http:
        raise expt_http


