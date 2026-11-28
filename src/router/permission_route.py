from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status
from sqlalchemy import and_, delete, func, select
from sqlalchemy.exc import IntegrityError

from src.api.dependencies.database_deps import AlchemySessionDeps
from src.dependencies import AuthorizeGuard
from src.domain.dtos.response_dtos import ApiCollectionResponse, ApiSingletonResponse
from src.domain.enums.authorities_enum import ERole
from src.domain.enums.endpoint_tag_enum import EApiTag
from src.domain.utils.pagination_helper import calculatePaginationParmas
from src.infrastructure.models.permission.permission_model import PermissionModel
from src.schema.permission import CreatePermissionSchema, PermissionSchema

router = APIRouter(prefix="/admin/permissions", tags=[EApiTag.PERMISSION])


@router.post("", name="Create Permission")
async def createPermission(
    data: CreatePermissionSchema, async_session: AlchemySessionDeps, response: Response
):
    try:
        async with async_session.begin():
            action = data.action.upper()
            resource = data.resource.upper()

            stmt = select(PermissionModel).where(
                and_(
                    PermissionModel.action == f"{action}:{resource}",
                    PermissionModel.resource == resource,
                )
            )

            result_set = await async_session.execute(stmt)
            permission = result_set.scalar_one_or_none()

            if permission is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Can not create duplicate permission!",
                )

            # Create permission
            permission = PermissionModel()
            permission.action = f"{data.action.upper()}:{data.resource.upper()}"
            permission.resource = data.resource.upper()

            async_session.add(permission)
            await async_session.refresh(permission)
            response.status_code = status.HTTP_201_CREATED

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    return ApiSingletonResponse(
        status="success",
        message="Permission created successfully.",
        data=PermissionSchema(
            id=permission.id, action=permission.action, resource=permission.resource
        ),
    )


@router.delete("", response_model=ApiSingletonResponse[None], name="Delete all permissions")
async def deleteAllPermissions(async_session: AlchemySessionDeps):
    try:
        async with async_session.begin():
            stmt = delete(PermissionModel)
            await async_session.execute(stmt)

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    return ApiSingletonResponse(
        status="success", message="All permissions were deleted successfullly.", data=None
    )


@router.delete(
    "/{permission_id}",
    response_model=ApiSingletonResponse[PermissionSchema],
    name="Delete a permission",
)
async def deletePermission(
    permission_id: Annotated[int, Path()], async_session: AlchemySessionDeps
):
    try:
        async with async_session.begin():
            stmt = select(PermissionModel).where(PermissionModel.id == permission_id)
            result_set = await async_session.execute(stmt)

            permission = result_set.scalar_one_or_none()

            if permission is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found!"
                )

            delete_permission = PermissionSchema(
                id=permission.id, action=permission.action, resource=permission.resource
            )
            await async_session.delete(permission)

        return ApiSingletonResponse(
            status="success",
            message="All permissions were deleted successfullly.",
            data=delete_permission,
        )

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )


@router.get(
    "",
    name="Get all permissions",
    response_model=ApiCollectionResponse[PermissionSchema],
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def getPermissions(async_session: AlchemySessionDeps):
    try:
        async with async_session.begin():
            stmt = select(PermissionModel).limit(800)

            aggregate_result_set = await async_session.execute(
                select(func.count(PermissionModel.id))
            )

            result_set = await async_session.execute(stmt)

            total = aggregate_result_set.scalar_one()
            permissions = result_set.scalars().all()

    except IntegrityError as expt_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    return ApiCollectionResponse(
        status="success",
        message="Retrieved permissions successfully.",
        error=None,
        data=permissions,
        metadata=calculatePaginationParmas(page=1, page_size=1000, total=total),
    )
