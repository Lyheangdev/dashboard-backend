from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import and_, delete, func, select
from sqlalchemy.exc import IntegrityError

from src.config.database import AlchemySession
from src.dependencies import authorizeGuard
from src.lib.api_enum import ApiTagEnum
from src.lib.api_response import ApiCollectionResponse, ApiError, ApiSingletonResponse
from src.lib.authority_enum import ERole
from src.lib.utils import calculatePaginationParmas
from src.models.permission_model import PermissionModel
from src.schema.permission import CreatePermissionSchema, PermissionSchema

router = APIRouter(prefix="/admin/permissions", tags=[ApiTagEnum.PERMISSION])


@router.post("", name="创建权限 ｜ Create Permission")
async def createPermission(
    data: CreatePermissionSchema, async_session: AlchemySession, response: Response
):

    try:
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
        await async_session.commit()
        await async_session.refresh(permission)

    except IntegrityError as e:
        await async_session.rollback()
        response.status_code = status.HTTP_409_CONFLICT
        return ApiSingletonResponse(
            status="failed",
            message="Something went wrong while trying to create this record!",
            data=None,
            error=ApiError(
                code=e.code or "ALCHEMY_EXCEPTION", message=None, details=e._message()
            ),
        )

    response.status_code = status.HTTP_201_CREATED
    return ApiSingletonResponse(
        status="success",
        message="Permission created successfully.",
        data=PermissionSchema(
            id=permission.id, action=permission.action, resource=permission.resource
        ),
    )


@router.delete(
    "", response_model=ApiSingletonResponse[None], name="删除全权限 | Delete all permissions"
)
async def deleteAllPermissions(async_session: AlchemySession):
    try:
        stmt = delete(PermissionModel)

        await async_session.execute(stmt)
        await async_session.commit()

        return ApiSingletonResponse(
            status="success", message="All permissions were deleted successfullly.", data=None
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
    "/{permission_id}",
    response_model=ApiSingletonResponse[PermissionSchema],
    name="删除具体权限 | Delete a permission",
)
async def deletePermission(permission_id: Annotated[int, Path()], async_session: AlchemySession):
    try:
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
        await async_session.commit()

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
    except HTTPException as expt_http:
        raise expt_http


@router.get(
    "",
    name="获取所有权限 ｜ Get all permissions",
    response_model=ApiCollectionResponse[PermissionSchema],
    dependencies=[Depends(authorizeGuard(roles=[ERole.ADMIN]))],
)
async def getPermissions(async_session: AlchemySession):
    stmt = select(PermissionModel).limit(1000)

    aggregate_result_set = await async_session.execute(select(func.count(PermissionModel.id)))
    result_set = await async_session.execute(stmt)

    total = aggregate_result_set.scalar_one()
    permissions = result_set.scalars().all()

    return ApiCollectionResponse(
        status="success",
        message="Retrieved permissions successfully.",
        error=None,
        data=permissions,
        metadata=calculatePaginationParmas(page=1, page_size=1000, total=total),
    )
