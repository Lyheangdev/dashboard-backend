from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.config.database import AlchemySession
from src.lib.api_enum import ApiTagEnum
from src.lib.api_response import ApiCollectionResponse, ApiSingletonResponse
from src.models.permission_model import PermissionModel
from src.models.role_model import RoleModel
from src.schema.permission import PermissionSchema
from src.schema.role import CreateRoleSchema, RolePermission, RoleSchema, UpdateRoleSchema

router = APIRouter(prefix="/admin/roles", tags=[ApiTagEnum.ROLE])


@router.post(
    "",
    response_model=ApiSingletonResponse[RoleSchema],
    name="创建作用 ｜ Create role",
    description="Key Note: ***permission_ids*** is the optional field.",
)
async def createRole(payload: CreateRoleSchema, async_session: AlchemySession):
    role_entry = RoleModel()
    role_entry.role = payload.role.capitalize()

    try:
        result_set = await async_session.execute(
            select(RoleModel)
            .where(RoleModel.role == payload.role.capitalize())
            .options(selectinload(RoleModel.permissions))
        )

        role = result_set.scalar_one_or_none()

        # Check duplicate role
        if role is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Can not create duplicate role!"
            )

        if payload.permission_ids is not None and len(payload.permission_ids) > 0:
            permission_result_set = await async_session.execute(
                select(PermissionModel).where(
                    PermissionModel.id.in_(list(payload.permission_ids))
                )
            )

            permissions_result = permission_result_set.scalars().all()

            # Add permissons only if permissions consist
            if len(permissions_result) > 0:
                for permission in permissions_result:
                    role_entry.permissions.append(permission)

        created_permission = [
            PermissionSchema(id=pm.id, action=pm.action, resource=pm.resource)
            for pm in (role_entry.permissions or [])
            if pm is not None
        ]

        async_session.add(role_entry)
        await async_session.commit()
        await async_session.refresh(role_entry)

        return ApiSingletonResponse(
            status="success",
            message="Create role successfully.",
            data=RoleSchema(
                id=role_entry.id,
                role=role_entry.role,
                permissions=created_permission,
            ),
        )

    except IntegrityError as exp_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    except HTTPException as exp_http:
        raise exp_http


@router.get(
    "/{role_id}",
    response_model=ApiSingletonResponse[RoleSchema],
    name="获取具体作用 ｜ Get a role",
)
async def getRole(role_id: Annotated[int, Path()], async_session: AlchemySession):
    try:
        stmt = (
            select(RoleModel)
            .where(RoleModel.id == role_id)
            .options(selectinload(RoleModel.permissions))
        )
        result_set = await async_session.execute(stmt)
        role = result_set.scalar_one_or_none()

        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found role!")

        return ApiSingletonResponse(
            status="success",
            message="Retrieved role successfully.",
            data=RoleSchema(
                id=role.id,
                role=role.role,
                permissions=[
                    PermissionSchema(
                        id=permission.id, action=permission.action, resource=permission.resource
                    )
                    for permission in role.permissions
                    if permission is not None
                ],
            ),
        )

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    except HTTPException as expt_http:
        raise expt_http


@router.get("", response_model=ApiCollectionResponse[RoleSchema], name="获取作用 ｜ Get roles")
async def getRoles(async_session: AlchemySession):
    stmt = select(RoleModel).options(selectinload(RoleModel.permissions))
    try:
        result_set = await async_session.execute(stmt)
        roleModels = result_set.scalars().all()

        return ApiCollectionResponse(
            status="success", message="Retrieved roles successfully.", data=roleModels
        )

    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e._message(),
            headers={"DATABASE_ERROR": e.code},
        )


@router.post(
    "/{role_id}/permission",
    response_model=ApiSingletonResponse[RoleSchema],
    name="作用里面添加权限 ｜ Add permissions to role",
)
async def addRolePermission(
    role_id: Annotated[int, Path()], payload: RolePermission, async_session: AlchemySession
):
    try:
        stmt = (
            select(RoleModel)
            .where(RoleModel.id == role_id)
            .options(selectinload(RoleModel.permissions))
        )

        result_set = await async_session.execute(stmt)
        roleModel = result_set.scalar_one_or_none()

        if roleModel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found!")

        # Check if permissions are duplicate
        check_duplicate = any(
            permission.id in payload.permission_ids for permission in roleModel.permissions
        )

        if check_duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can not add duplicate permission!",
            )

        result_set = await async_session.execute(
            select(PermissionModel).where(PermissionModel.id.in_(list(payload.permission_ids)))
        )

        permissions = result_set.scalars().all()

        if len(permissions) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You ar trying to add non-existing permission!",
            )

        for permission in permissions:
            roleModel.permissions.append(permission)

        await async_session.commit()
        await async_session.refresh(roleModel)

        return ApiSingletonResponse(
            status="success",
            message="Add permission successfully",
            data=RoleSchema(
                id=roleModel.id,
                role=roleModel.role,
                permissions=[
                    PermissionSchema(
                        id=permission.id, action=permission.action, resource=permission.resource
                    )
                    for permission in (roleModel.permissions)
                    if permission is not None
                ]
                if len(roleModel.permissions) > 0
                else [],
            ),
        )

    except IntegrityError as expdb:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expdb._message(),
            headers={"DATABASE_ERROR": expdb.code},
        )

    except HTTPException as exphttp:
        raise exphttp


@router.delete(
    "/{role_id}",
    response_model=ApiSingletonResponse[RoleSchema],
    name="删除具体作用 | Delete a role",
)
async def deleteRole(role_id: Annotated[int, Path()], async_session: AlchemySession):
    try:
        stmt = (
            select(RoleModel)
            .where(RoleModel.id == role_id)
            .options(selectinload(RoleModel.permissions))
        )
        result_set = await async_session.execute(stmt)

        role = result_set.scalar_one_or_none()

        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found!")

        delete_role = RoleSchema(
            id=role.id,
            role=role.role,
            permissions=[
                PermissionSchema(
                    id=permission.id, action=permission.action, resource=permission.resource
                )
                for permission in role.permissions
            ],
        )

        await async_session.delete(role)
        await async_session.commit()

        return ApiSingletonResponse(
            status="success", message="Delete role successfully.", data=delete_role
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
    "/{role_id}", response_model=ApiSingletonResponse[RoleSchema], name="更新作用 ｜ Update role"
)
async def updateRole(
    role_id: Annotated[int, Path()],
    payload: UpdateRoleSchema,
    async_session: AlchemySession,
):
    try:
        stmt = select(RoleModel).where(RoleModel.id == role_id)

        result_set = await async_session.execute(stmt)
        roleModel = result_set.scalar_one_or_none()

        if roleModel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found!")

        # Check whether alter only role name
        if payload.role is not None:
            roleModel.role = payload.role.capitalize()

        # Attempt to save the change
        await async_session.commit()
        await async_session.refresh(roleModel)

        return ApiSingletonResponse(
            status="success",
            message="Update role successfully",
            data=RoleSchema(id=roleModel.id, role=roleModel.role),
        )

    except IntegrityError as expdb:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expdb._message(),
            headers={"DATABASE_ERROR": expdb.code},
        )

    except HTTPException as exphttp:
        raise exphttp


@router.delete(
    "/{role_id}/permission",
    response_model=ApiSingletonResponse[RoleSchema],
    name="删除全权限 ｜ Remove permissions from a role",
)
async def deleteRolePermission(
    role_id: Annotated[int, Path()],
    payload: RolePermission,
    async_session: AlchemySession,
):
    try:
        stmt = (
            select(RoleModel)
            .where(RoleModel.id == role_id)
            .options(selectinload(RoleModel.permissions))
        )

        result_set = await async_session.execute(stmt)
        roleModel = result_set.scalar_one_or_none()

        if len(roleModel.permissions) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No any permissions to delete!"
            )

        filter_permissions_to_delete = [
            permission
            for permission in roleModel.permissions
            if permission.id in payload.permission_ids
        ]

        if len(filter_permissions_to_delete) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not matched any permission to delete!",
            )

        for permission in filter_permissions_to_delete:
            roleModel.permissions.remove(permission)

        # Attempt to save the change
        await async_session.commit()
        await async_session.refresh(roleModel)

        return ApiSingletonResponse(
            status="success",
            message="Delete permission successfully",
            data=RoleSchema(
                id=roleModel.id,
                role=roleModel.role,
                permissions=[
                    PermissionSchema(
                        id=permission.id, action=permission.action, resource=permission.resource
                    )
                    for permission in (roleModel.permissions)
                    if permission is not None
                ]
                if len(roleModel.permissions) > 0
                else [],
            ),
        )

    except IntegrityError as expdb:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expdb._message(),
            headers={"DATABASE_ERROR": expdb.code},
        )

    except HTTPException as exphttp:
        raise exphttp


@router.delete(
    "", response_model=ApiSingletonResponse[None], name="删除全作用 ｜ Delete all roles"
)
async def deleteRoles(async_session: AlchemySession):
    stmt = delete(RoleModel)
    try:
        await async_session.execute(stmt)
        await async_session.commit()

    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e._message(),
            headers={"DATABASE_ERROR": e.code},
        )

    return ApiSingletonResponse(
        status="success", message="Delete all roles successfully.", data=None
    )
