from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from src.config.database import AlchemySession
from src.config.logging import print_log
from src.dependencies import AuthGuard, AuthorizeGuard
from src.lib.api_auth import hashMyPassword
from src.lib.api_enum import ApiTagEnum
from src.lib.api_response import (
    ApiCollectionResponse,
    ApiSingletonResponse,
    SortOrderEnum,
)
from src.lib.authority_enum import EAction, EAuditingStatus, EResource, ERole
from src.lib.user_enum import EUserStatus
from src.lib.utils import calculateOffset, calculatePaginationParmas, getFullName
from src.models.auditing_model import AuditingModel
from src.models.user_model import UserModel
from src.schema.role import RoleSchema
from src.schema.user import (
    CreateUserSchema,
    UpdateUserSchema,
    UserPagination,
    UserSchema,
    UserSortByField,
)

router = APIRouter(prefix="/admin/users", tags=[ApiTagEnum.SYSTEM_USER])

# Check whether exists sort field
sort_fields: dict[UserSortByField, InstrumentedAttribute] = {
    "created_at": UserModel.created_at,
    "email": UserModel.email,
}


@router.post(
    "",
    response_model=ApiSingletonResponse[UserSchema],
    name="Create a user | 创建具体用户数据",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN, ERole.ADMIN])],
)
async def create_user(
    payload: CreateUserSchema,
    cur_user: AuthGuard,
    async_session: AlchemySession,
    response: Response,
):
    try:
        print_log(
            name=EResource.USER.value,
            type="info",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to create a user",
        )

        # Check if the current user is absolutely new
        stmt = select(UserModel).where(UserModel.email == payload.email)
        result_set = await async_session.execute(stmt)

        user = result_set.scalar_one_or_none()

        if user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Cannot create duplicate user!"
            )

        fetch_creator_user = await async_session.execute(
            select(UserModel).where(UserModel.id == cur_user.id)
        )

        creator_user = fetch_creator_user.scalar_one_or_none()

        if creator_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Sorry, creator user not found!"
            )

        # Create the user
        userModel = UserModel()

        userModel.first_name = payload.first_name or None
        userModel.last_name = payload.last_name or None
        userModel.email = payload.email
        userModel.password = hashMyPassword(payload.password)
        userModel.bio = payload.bio
        userModel.code = payload.code
        userModel.creator = creator_user

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

        print_log(
            name=EResource.USER.value,
            type="info",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to create a user [ success ]",
        )

    except IntegrityError as expt_db:
        await async_session.rollback()

        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to create a user failed by database error.",
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
            code=userModel.code,
            status=userModel.status,
            isBanned=userModel.isBanned,
            asset_identifier=userModel.asset_identifier,
            created_at=userModel.created_at,
            updated_at=userModel.updated_at,
        ),
    )


@router.get(
    "",
    response_model=ApiCollectionResponse[UserSchema],
    description="Get all users data",
    name="Get all users | 获取所有用户数据",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN, ERole.ADMIN])],
)
async def get_users(
    async_session: AlchemySession,
    cur_user: AuthGuard,
    queryParams: Annotated[UserPagination, Query()],
):
    page = queryParams.page
    page_size = queryParams.page_size
    offset = calculateOffset(page=page, page_size=page_size)

    try:
        is_superadmin = cur_user.role.role == ERole.SUPERADMIN.value

        stmt = (
            select(UserModel)
            if is_superadmin
            else select(UserModel).where(UserModel.created_by_id == cur_user.id)
        )

        aggregate_stmt = (
            select(func.count(UserModel.id))
            if is_superadmin
            else select(func.count(UserModel.id)).where(UserModel.created_by_id == cur_user.id)
        )

        search = queryParams.search

        if search is not None:
            stmt = stmt.where(UserModel.email.ilike(f"%{search}%"))
            aggregate_stmt = aggregate_stmt.where(UserModel.email.ilike(f"%{search}%"))

        # * Prepare sort field
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

        # * Prepare pagination
        stmt = (
            stmt.offset(offset=offset)
            .limit(page_size)
            .options(selectinload(UserModel.roles))
            .options(selectinload(UserModel.asset))
            .options(selectinload(UserModel.creator))
        )
        result_set = await async_session.execute(stmt)

        users = result_set.scalars().all()
        aggregate_result_set = await async_session.execute(aggregate_stmt)
        total = aggregate_result_set.scalar_one()

        print_log(
            name=EResource.USER.value,
            type="info",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to get list of all users [success].",
        )

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
                    code=u.code,
                    status=u.status,
                    role=RoleSchema(id=u.roles[0].id, role=u.roles[0].role)
                    if len(u.roles) > 0
                    else None,
                    isBanned=u.isBanned,
                    created_at=u.created_at,
                    updated_at=u.created_at,
                    created_by=f"{u.creator.first_name} {u.creator.last_name}"
                    if u.creator is not None
                    else "System",
                )
                for u in users
            ]
            if len(users) > 0
            else [],
            metadata=calculatePaginationParmas(page=page, page_size=page_size, total=total),
        )

    except IntegrityError as expt_db:
        await async_session.rollback()

        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to get list of all users [falied].",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=expt_db._message(),
            headers={"DATABASE_ERROR": expt_db.code},
        )


"""
@Description: Use only for superadmin and admin invoked to check others users
"""


@router.get(
    "/{user_id}",
    response_model=ApiSingletonResponse[UserSchema],
    name="Get a user | 获取集体用户数据",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN, ERole.ADMIN])],
)
async def get_user(
    user_id: Annotated[int, Path()],
    cur_user: AuthGuard,
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
            code=data.code,
            status=data.status,
            isBanned=data.isBanned,
            asset_identifier=data.asset.file_path if data.asset is not None else None,
            created_at=data.created_at,
            updated_at=data.updated_at,
        )

        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to get a user [success].",
        )

    except IntegrityError as exp_db:
        await async_session.rollback()
        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to get a user [failed].",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

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
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN, ERole.ADMIN])],
)
async def update_user(
    user_id: Annotated[int, Path()],
    user: UpdateUserSchema,
    cur_user: AuthGuard,
    async_session: AlchemySession,
    response: Response,
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

        # Write audit log
        auditingModel = AuditingModel()
        auditingModel.user = getFullName(fname=cur_user.first_name, lname=cur_user.last_name)
        auditingModel.role = cur_user.role.role
        auditingModel.resource = EResource.USER.value
        auditingModel.action = EAction.UPDATE.value
        auditingModel.status = EAuditingStatus.SUCCESS.value

        await async_session.commit()
        await async_session.refresh(user_model)

        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to update a user [success].",
        )

    except IntegrityError as exp_db:
        async_session.rollback()
        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to update a user [failed].",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    return ApiSingletonResponse(
        status="success",
        message="Update user successfully.",
        data=UserSchema(
            id=user_model.id,
            first_name=user_model.first_name,
            last_name=user_model.last_name,
            code=user_model.code,
            status=user_model.status,
            isBanned=user_model.isBanned,
            bio=user_model.bio,
            asset_identifier=user_model.asset_identifier,
            email=user_model.email,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at,
        ),
    )


@router.delete(
    "/{user_id}",
    response_model=ApiSingletonResponse[UserSchema],
    name="Delete a user | 删除具体用户数据",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def delete_user(
    user_id: Annotated[int, Path()],
    cur_user: AuthGuard,
    async_session: AlchemySession,
    response: Response,
):
    try:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result_set = await async_session.execute(stmt)
        user_model = result_set.scalar_one_or_none()

        if user_model is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return ApiSingletonResponse(status="failed", message="User not found", data=None)

        user_data = UserSchema.model_validate(user_model)

        # Write audit log
        auditingModel = AuditingModel()
        auditingModel.user = getFullName(fname=cur_user.first_name, lname=cur_user.last_name)
        auditingModel.role = cur_user.role.role
        auditingModel.resource = EResource.USER.value
        auditingModel.action = EAction.DELETE.value
        auditingModel.status = EAuditingStatus.SUCCESS.value

        await async_session.delete(user_model)
        await async_session.commit()

        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to delete a user [success].",
        )

    except IntegrityError as exp_db:
        await async_session.rollback()
        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to delete a user [failed].",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    return ApiSingletonResponse(status="success", message="Delete successfully.", data=user_data)


#! all users
@router.delete(
    "",
    response_model=ApiSingletonResponse[UserSchema],
    name="Delete all users | 删除整个用户数据",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def delete_users(cur_user: AuthGuard, async_session: AlchemySession):
    try:
        stmt = delete(UserModel)

        # Write audit log
        auditingModel = AuditingModel()
        auditingModel.user = getFullName(fname=cur_user.first_name, lname=cur_user.last_name)
        auditingModel.role = cur_user.role.role
        auditingModel.resource = EResource.USER.value
        auditingModel.action = EAction.DELETE_ALL.value
        auditingModel.status = EAuditingStatus.SUCCESS.value

        await async_session.execute(stmt)
        await async_session.commit()

        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to delete all [success].",
        )

    except IntegrityError as exp_db:
        await async_session.rollback()
        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to delete all [failed].",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    return ApiSingletonResponse(status="success", message="Delete all users successfully.")


@router.put(
    "/{user_id}/status",
    response_model=ApiSingletonResponse[None],
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
    name="Approve or disapprove user",
)
async def updateUserStatus(
    user_id: Annotated[int, Path()],
    user_status: Annotated[EUserStatus, Query()],
    cur_user: AuthGuard,
    async_session: AlchemySession,
):
    status_text = "Active" if user_status == 1 else "Inactive"

    try:
        stmt = (select(UserModel)).where(UserModel.id == user_id)
        result_set = await async_session.execute(stmt)

        user = result_set.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        if user.status == user_status:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User is already in {status_text} mode!",
            )

        user_email = user.email
        user.status = user_status

        # Write audit log
        auditingModel = AuditingModel()
        auditingModel.user = getFullName(fname=cur_user.first_name, lname=cur_user.last_name)
        auditingModel.role = cur_user.role.role
        auditingModel.resource = EResource.USER.value
        auditingModel.action = EAction.UPDATE_STATUS.value
        auditingModel.status = EAuditingStatus.SUCCESS.value

        await async_session.commit()
        await async_session.flush()

        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to change user status [success].",
        )

    except IntegrityError as exp_db:
        await async_session.rollback()
        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg="attempts to change user status [failed].",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    return ApiSingletonResponse(
        status="success",
        message=f"User: {user_email} has already updated status to {status_text}",
    )


@router.put(
    "/{user_id}/accessibility",
    response_model=ApiSingletonResponse[None],
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
    name="Ban or unban user",
)
async def updateUserAccessibility(
    user_id: Annotated[int, Path()],
    isBan: Annotated[bool, Query()],
    cur_user: AuthGuard,
    async_session: AlchemySession,
):
    ban_text = "banned" if isBan else "unbanned"

    try:
        stmt = (select(UserModel)).where(UserModel.id == user_id)
        result_set = await async_session.execute(stmt)

        user = result_set.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        if user.isBanned == isBan:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User {user.email} has alread been in {ban_text} mode!",
            )

        user_email = user.email
        user.isBanned = isBan

        # Write audit log
        auditingModel = AuditingModel()
        auditingModel.user = getFullName(fname=cur_user.first_name, lname=cur_user.last_name)
        auditingModel.role = cur_user.role.role
        auditingModel.resource = EResource.USER.value
        auditingModel.action = EAction.BAN.value if isBan else EAction.UNBAN.value
        auditingModel.status = EAuditingStatus.SUCCESS.value

        await async_session.commit()
        await async_session.flush()

        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg=f"attempts to {ban_text} [success].",
        )

    except IntegrityError as exp_db:
        await async_session.rollback()
        print_log(
            name=EResource.USER.value,
            type="execption",
            fname=cur_user.first_name,
            lname=cur_user.last_name,
            msg=f"attempts to {ban_text} [failed].",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    return ApiSingletonResponse(
        status="success",
        message=f"User: {user_email} has already {ban_text} by system.",
    )
