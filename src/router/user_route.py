from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from src.config.database import AlchemySession
from src.config.logging import get_logger
from src.dependencies import AuthGuard, AuthorizeGuard
from src.lib.api_auth import hashMyPassword
from src.lib.api_enum import ApiTagEnum
from src.lib.api_response import (
    ApiCollectionResponse,
    ApiSingletonResponse,
    SortOrderEnum,
)
from src.lib.authority_enum import EAction, EAuditingStatus, EResource, ERole
from src.lib.utils import calculateOffset, calculatePaginationParmas, combineLog, getFullName
from src.models.auditing_model import AuditingModel
from src.models.user_model import UserModel
from src.schema.user import (
    CreateUserSchema,
    UpdateUserSchema,
    UserPagination,
    UserSchema,
    UserSortByField,
)

logger = get_logger("User Resource")

router = APIRouter(
    prefix="/admin/users",
    tags=[ApiTagEnum.SYSTEM_USER]
)

# Check whether exists sort field
sort_fields: dict[UserSortByField, InstrumentedAttribute] = {
    "created_at": UserModel.created_at,
    "email": UserModel.email,
}


@router.post(
    "", response_model=ApiSingletonResponse[UserSchema], name="Create a user ｜ 创建具体用户数据",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])]
)
async def create_user(
    payload: CreateUserSchema,
    cur_user: AuthGuard,
    async_session: AlchemySession,
    response: Response,
):
    try:
        logger.info(
            combineLog(
                fname=cur_user.first_name,
                lname=cur_user.last_name,
                msg="attempts to create a user",
            )
        )
        # Check if the current user is absolutely new
        result_set = await async_session.execute(
            select(UserModel).where(UserModel.email == payload.email)
        )

        user = result_set.scalar_one_or_none()

        if user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Cannot create duplicate user!"
            )

        # Create the user
        userModel = UserModel()

        userModel.first_name = payload.first_name or None
        userModel.last_name = payload.last_name or None
        userModel.email = payload.email
        userModel.password = hashMyPassword(payload.password)
        userModel.bio = payload.bio
        userModel.created_by = getFullName(fname=cur_user.first_name, lname=cur_user.last_name)

        async_session.add(userModel)
        await async_session.flush()

        # Write audit log
        auditingModel = AuditingModel()
        auditingModel.user = getFullName(fname=cur_user.first_name, lname=cur_user.last_name)
        auditingModel.role = cur_user.role.role
        auditingModel.resource = EResource.USER.value
        auditingModel.action = EAction.WRITE.value
        auditingModel.status = EAuditingStatus.SUCCESS.value

        async_session.add(auditingModel)

        # Commit these two models to database
        await async_session.commit()
        await async_session.refresh(userModel)

        logger.info(
            combineLog(
                fname=cur_user.first_name,
                lname=cur_user.last_name,
                msg="attempts to create a user [ success ]",
            )
        )

    except IntegrityError as expt_db:
        await async_session.rollback()
        logger.exception(
            combineLog(
                fname=cur_user.first_name,
                lname=cur_user.last_name,
                msg="attempts to create a user failed by database error.",
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    response.status_code = status.HTTP_201_CREATED

    return ApiSingletonResponse(
        status="success",
        message="User created successfully.",
        data=UserSchema(
            id=userModel.id,
            first_name=userModel.first_name,
            last_name=userModel.last_name,
            email=userModel.email,
            bio=userModel.bio,
            asset_identifier=userModel.asset_identifier,
            created_at=userModel.created_at,
            updated_at=userModel.updated_at,
        ),
    )


@router.get(
    "",
    response_model=ApiCollectionResponse[UserSchema],
    response_model_exclude_none=True,
    description="Get all users data",
    name="Get all users ｜ 获取所有用户数据",
)
async def get_users(
    async_session: AlchemySession,
    queryParams: Annotated[UserPagination, Query()],
    response: Response,
):
    page = queryParams.page
    page_size = queryParams.page_size
    offset = calculateOffset(page=page, page_size=page_size)

    try:
        stmt = select(UserModel)
        aggregate_stmt = select(func.count(UserModel.id))

        search = queryParams.search
        if search is not None:
            stmt = stmt.where(UserModel.email.ilike(f"%{search}%"))
            aggregate_stmt = aggregate_stmt.where(UserModel.email.ilike(f"%{search}%"))

        sort_by = sort_fields.get(queryParams.sort_by)
        order_by = queryParams.order_by

        if sort_by is not None:
            sort_by = (
                sort_by.desc()
                if order_by is not None and order_by == SortOrderEnum.DESC
                else sort_by.asc()
            )
            stmt = stmt.order_by(sort_by)
        else:
            stmt = stmt.order_by(UserModel.id.asc())

        stmt = stmt.offset(offset=offset).limit(page_size).options(selectinload(UserModel.asset))

        result_set = await async_session.execute(stmt)
        users = result_set.scalars().all()

        aggregate_result_set = await async_session.execute(aggregate_stmt)
        total = aggregate_result_set.scalar_one()

        return ApiCollectionResponse(
            status="success",
            message="Retrieved users successfully.",
            error=None,
            data=[
                UserSchema(
                    id=u.id,
                    email=u.email,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    asset_identifier=u.asset.file_path if u.asset is not None else None,
                    bio=u.bio,
                    created_at=u.created_at,
                    updated_at=u.created_at,
                )
                for u in users
            ],
            metadata=calculatePaginationParmas(page=page, page_size=page_size, total=total),
        )

    except IntegrityError as expt_db:
        async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )

    except HTTPException as exp_http:
        raise exp_http


@router.get(
    "/{user_id}",
    response_model=ApiSingletonResponse[UserSchema],
    name="Get a user | 获取集体用户数据",
)
async def get_user(
    user_id: int,
    async_session: AlchemySession,
):
    try:
        stmt = (
            select(UserModel)
            .where(UserModel.id == user_id)
            .options(selectinload(UserModel.asset))
        )
        result_set = await async_session.execute(stmt)
        data = result_set.scalar_one_or_none()

        if data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        userDto = UserSchema(
            id=data.id,
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            bio=data.bio,
            asset_identifier=data.asset.file_path,
            created_at=data.created_at,
            updated_at=data.updated_at,
        )

    except IntegrityError as exp_db:
        async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    except HTTPException as exp_http:
        raise exp_http

    return ApiSingletonResponse(
        status="success",
        message="Retrieved user successfully.",
        data=userDto,
    )


@router.put(
    "/{user_id}",
    response_model=ApiSingletonResponse[UserSchema],
    response_model_exclude_unset=True,
    name="Update a user | 更新具体用户数据",
)
async def update_user(
    user_id: int, user: UpdateUserSchema, async_session: AlchemySession, response: Response
):
    try:
        stmt = select(UserModel).where(UserModel.id == user_id)

        result_set = await async_session.execute(stmt)
        user_model = result_set.scalar_one_or_none()

        filter_keys = {
            field: value
            for field, value in user.model_dump(exclude_unset=True, exclude_none=True).items()
            if value != ""
        }

        if user_model is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return ApiSingletonResponse(status="failed", message="User not found", data=None)

        if len(filter_keys.keys()) == 0:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return ApiSingletonResponse(status="failed", message="No update data.", data=None)

        for field, value in filter_keys.items():
            setattr(user_model, field, value)

        await async_session.commit()
        await async_session.refresh(user_model)

    except IntegrityError as exp_db:
        async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    except HTTPException as exp_http:
        raise exp_http

    return ApiSingletonResponse(
        status="success", message="Update user successfully.", data=user_model
    )


@router.delete(
    "/{user_id}",
    response_model=ApiSingletonResponse[UserSchema],
    name="Delete a user | 删除具体用户数据",
)
async def delete_user(user_id: int, async_session: AlchemySession, response: Response):
    try:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result_set = await async_session.execute(stmt)
        user_model = result_set.scalar_one_or_none()

        if user_model is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return ApiSingletonResponse(status="failed", message="User not found", data=None)

        user_data = UserSchema.model_validate(user_model)

        await async_session.delete(user_model)
        await async_session.commit()

    except IntegrityError as exp_db:
        async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    except HTTPException as exp_http:
        raise exp_http

    return ApiSingletonResponse(status="success", message="Delete successfully.", data=user_data)


# # Delete all users
@router.delete(
    "",
    response_model=ApiSingletonResponse[UserSchema],
    name="Delete all users | 删除整个用户数据",
)
async def delete_users(async_session: AlchemySession):
    try:
        stmt = delete(UserModel)
        await async_session.execute(stmt)
        await async_session.commit()

    except IntegrityError as exp_db:
        async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    except HTTPException as exp_http:
        raise exp_http

    return ApiSingletonResponse(status="success", message="Delete all users successfully.")
