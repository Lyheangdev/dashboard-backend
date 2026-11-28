from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.api.dependencies.database_deps import AlchemySessionDeps
from src.dependencies import AuthorizeGuard
from src.domain.dtos.response_dtos import ApiCollectionResponse, ApiSingletonResponse
from src.domain.enums.authorities_enum import ERole
from src.domain.enums.endpoint_tag_enum import EApiTag
from src.domain.utils.pagination_helper import calculatePaginationParmas
from src.infrastructure.models.permission.permission_model import PermissionModel
from src.infrastructure.models.role.role_model import RoleModel
from src.infrastructure.models.user.user_model import UserModel
from src.infrastructure.models.view.view_model import ViewModel
from src.schema.permission import PermissionSchema
from src.schema.role import (
    ConfigUsersRolesSchema,
    CreateRoleSchema,
    DeleteRoleSchema,
    RolePermission,
    RoleSchema,
    RoleUserSchema,
    UpdateRoleSchema,
)
from src.schema.view import ViewSchema

router = APIRouter(prefix="/admin/roles", tags=[EApiTag.ROLE])


@router.post(
    "",
    response_model=ApiSingletonResponse[None],
    name="Create role",
    description="Key Note: ***permission_ids*** is the optional field.",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def createRole(payload: CreateRoleSchema, async_session: AlchemySessionDeps):
    role_entry = RoleModel()
    role_entry.role = payload.role.capitalize()

    if payload.remark:
        role_entry.remark = payload.remark

    try:
        async with async_session.begin():
            result_set = await async_session.execute(
                select(RoleModel)
                .where(RoleModel.role == payload.role.capitalize())
                .options(selectinload(RoleModel.permissions), selectinload(RoleModel.views))
            )

            role = result_set.scalar_one_or_none()

            # Check duplicate role
            if role is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Can not create duplicate role!",
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

            if payload.menus_ids is not None and len(payload.menus_ids) > 0:
                menus_result_set = await async_session.execute(
                    select(ViewModel).where(ViewModel.id.in_(list(payload.menus_ids)))
                )

                menus_result = menus_result_set.scalars().all()

                # Add menu only if menus consist
                if len(menus_result) > 0:
                    for menu in menus_result:
                        role_entry.views.append(menu)

            async_session.add(role_entry)
            await async_session.flush()

    except IntegrityError as exp_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    return ApiSingletonResponse(
        status="success",
        message="Create role successfully.",
        data=None,
    )


# retrieved both user and role at the same endpoint
@router.get(
    "/config",
    response_model=ApiSingletonResponse[ConfigUsersRolesSchema],
    name="Get config users and roles",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def getConfigUserRole(async_session: AlchemySessionDeps):
    try:
        async with async_session.begin():
            users_stmt = select(
                UserModel.id,
                UserModel.first_name,
                UserModel.last_name,
                UserModel.email,
                UserModel.code,
            ).order_by(UserModel.created_at.desc())

            users_result = await async_session.execute(users_stmt)
            users = [
                RoleUserSchema(
                    id=int(u["id"]),
                    first_name=u["first_name"],
                    last_name=u["last_name"],
                    email=u["email"],
                    code=u["code"],
                )
                for u in users_result.mappings().all()
            ]

            # --- fetch roles
            roles_stmt = select(RoleModel.id, RoleModel.role)
            roles_result = await async_session.execute(roles_stmt)
            roles = [
                RoleSchema(id=int(r["id"]), role=r["role"]) for r in roles_result.mappings().all()
            ]

    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e._message(),
            headers={"DATABASE_ERROR": e.code},
        )

    return ApiSingletonResponse(
        status="success",
        message="Retrived config users & roles successfully.",
        data=ConfigUsersRolesSchema(users=users, roles=roles),
    )


@router.get(
    "/{role_id}",
    response_model=ApiSingletonResponse[RoleSchema],
    name="Get a role",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def getRole(role_id: Annotated[int, Path()], async_session: AlchemySessionDeps):
    try:
        async with async_session.begin():
            stmt = (
                select(RoleModel)
                .where(RoleModel.id == role_id)
                .options(selectinload(RoleModel.permissions), selectinload(RoleModel.views))
            )

            result_set = await async_session.execute(stmt)
            role = result_set.scalar_one_or_none()

            if role is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Not found role!"
                )

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    return ApiSingletonResponse(
        status="success",
        message="Retrieved role successfully.",
        data=RoleSchema(
            id=role.id,
            role=role.role,
            remark=role.remark,
            views=[
                ViewSchema(
                    id=view.id, menu=view.menu, miscellaneous=view.miscellaneous, note=view.note
                )
                for view in (role.views or [])
            ],
            permissions=[
                PermissionSchema(
                    id=permission.id, action=permission.action, resource=permission.resource
                )
                for permission in role.permissions
                if permission is not None
            ],
        ),
    )


@router.get(
    "",
    response_model=ApiCollectionResponse[RoleSchema],
    name="Get roles",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def getRoles(async_session: AlchemySessionDeps):
    try:
        async with async_session.begin():
            stmt = select(RoleModel).options(selectinload(RoleModel.permissions))
            result_set = await async_session.execute(stmt)
            roles = result_set.scalars().all()

    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e._message(),
            headers={"DATABASE_ERROR": e.code},
        )

    return ApiCollectionResponse(
        status="success",
        message="Retrieved roles successfully.",
        data=[
            RoleSchema(
                id=r.id,
                role=r.role,
                remark=r.remark,
                permissions=[
                    PermissionSchema(id=p.id, resource=p.resource, action=p.action)
                    for p in r.permissions
                ]
                if len(r.permissions)
                else [],
            )
            for r in roles
        ]
        if len(roles) > 0
        else [],
        error=None,
        metadata=calculatePaginationParmas(page=1, page_size=800, total=len(roles)),
    )


@router.post(
    "/{role_id}/permission",
    response_model=ApiSingletonResponse[RoleSchema],
    name="Add permissions to role",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def addRolePermission(
    role_id: Annotated[int, Path()], payload: RolePermission, async_session: AlchemySessionDeps
):
    try:
        async with async_session.begin():
            stmt = (
                select(RoleModel)
                .where(RoleModel.id == role_id)
                .options(selectinload(RoleModel.permissions))
            )

            result_set = await async_session.execute(stmt)
            roleModel = result_set.scalar_one_or_none()

            if roleModel is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Role not found!"
                )

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
                select(PermissionModel).where(
                    PermissionModel.id.in_(list(payload.permission_ids))
                )
            )

            permissions = result_set.scalars().all()

            if len(permissions) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You ar trying to add non-existing permission!",
                )

            for permission in permissions:
                roleModel.permissions.append(permission)

            await async_session.refresh(roleModel)

    except IntegrityError as expdb:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expdb._message(),
            headers={"DATABASE_ERROR": expdb.code},
        )

    return ApiSingletonResponse(
        status="success",
        message="Add permission successfully",
        data=RoleSchema(
            id=roleModel.id,
            role=roleModel.role,
            remark=roleModel.remark,
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


@router.delete(
    "/{role_id}",
    response_model=ApiSingletonResponse[None],
    name="Delete a role",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def deleteRole(role_id: Annotated[int, Path()], async_session: AlchemySessionDeps):
    try:
        async with async_session.begin():
            stmt = select(RoleModel).where(RoleModel.id == role_id)

            result_set = await async_session.execute(stmt)
            role = result_set.scalar_one_or_none()

            if role is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Role not found!"
                )

            await async_session.delete(role)

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    return ApiSingletonResponse(status="success", message="Delete role successfully.", data=None)


@router.put(
    "/{role_id}",
    response_model=ApiSingletonResponse[None],
    name="Update role",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def updateRole(
    role_id: Annotated[int, Path()],
    payload: UpdateRoleSchema,
    async_session: AlchemySessionDeps,
):
    try:
        async with async_session.begin():
            stmt = (
                select(RoleModel)
                .where(RoleModel.id == role_id)
                .options(selectinload(RoleModel.views), selectinload(RoleModel.permissions))
            )

            result_set = await async_session.execute(stmt)
            role = result_set.scalar_one_or_none()

            if role is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Role not found!"
                )

            viewsResult = await async_session.execute(
                select(ViewModel).where(ViewModel.id.in_(payload.view_ids))
            )

            views = viewsResult.scalars().all()

            if len(views) >= 0:
                role.views.clear()
                role.views.extend(views)

            permissionsResults = await async_session.execute(
                select(PermissionModel).where(PermissionModel.id.in_(payload.permission_ids))
            )

            permissions = permissionsResults.scalars().all()

            if len(permissions) >= 0:
                role.permissions.clear()
                role.permissions.extend(permissions)

            # Check whether alter only role name
            if payload.role is not None:
                role.role = payload.role.capitalize()

            if payload.remark is not None:
                role.remark = payload.remark

            # Attempt to save the change
            await async_session.flush()

    except IntegrityError as expdb:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expdb._message(),
            headers={"DATABASE_ERROR": expdb.code},
        )

    return ApiSingletonResponse(
        status="success",
        message="Update role successfully",
        data=None,
    )


@router.delete(
    "/{role_id}/permission",
    response_model=ApiSingletonResponse[RoleSchema],
    name="Remove permissions from a role",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def deleteRolePermission(
    role_id: Annotated[int, Path()],
    payload: RolePermission,
    async_session: AlchemySessionDeps,
):
    try:
        async with async_session.begin():
            stmt = (
                select(RoleModel)
                .where(RoleModel.id == role_id)
                .options(selectinload(RoleModel.permissions))
            )

            result_set = await async_session.execute(stmt)
            roleModel = result_set.scalar_one_or_none()

            if len(roleModel.permissions) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No any permissions to delete!",
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
            await async_session.refresh(roleModel)

    except IntegrityError as expdb:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expdb._message(),
            headers={"DATABASE_ERROR": expdb.code},
        )

    return ApiSingletonResponse(
        status="success",
        message="Delete permission successfully",
        data=RoleSchema(
            id=roleModel.id,
            role=roleModel.role,
            permissions=[
                PermissionSchema(
                    id=permission.id,
                    action=permission.action,
                    resource=permission.resource,
                )
                for permission in (roleModel.permissions)
                if permission is not None
            ]
            if len(roleModel.permissions) > 0
            else [],
        ),
    )


# delete any role
@router.delete(
    "",
    response_model=ApiSingletonResponse[None],
    name="Delete all roles",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def deleteRoles(payload: DeleteRoleSchema, async_session: AlchemySessionDeps):
    try:
        if not bool(len(payload.roles_id)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Please provide role ids"
            )

        async with async_session.begin():
            stmt = delete(RoleModel).where(RoleModel.id.in_(payload.roles_id))
            await async_session.execute(stmt)

    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e._message(),
            headers={"DATABASE_ERROR": e.code},
        )

    return ApiSingletonResponse(
        status="success", message="Delete some roles successfully.", data=None
    )
