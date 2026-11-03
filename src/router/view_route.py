from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.config.database import AlchemySession
from src.config.logging import print_log
from src.config.redis import RedisClient
from src.dependencies import AuthGuard, AuthorizeGuard
from src.lib.api_enum import ApiTagEnum
from src.lib.api_redis_cache import RedisCache, RedisCacheKey
from src.lib.api_response import ApiCollectionResponse, ApiSingletonResponse, BasePagination
from src.lib.authority_enum import EResource, ERole
from src.lib.utils import calculateOffset, calculatePaginationParmas
from src.models.user_model import UserModel
from src.models.view_model import ViewModel
from src.schema.view import (
    AddOrRemoveUserViewSchema,
    CreateViewSchema,
    UpdateViewSchema,
    UserMenuSchema,
    ViewSchema,
)

router = APIRouter(prefix="/menu", tags=[ApiTagEnum.MENU_VIEW])


@router.get(
    "",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN, ERole.ADMIN])],
    response_model=ApiCollectionResponse[ViewSchema],
    name="Get all views",
)
async def getAllViews(
    _: AuthGuard, pageble: Annotated[BasePagination, Query()], async_session: AlchemySession
):
    try:
        stmt_aggregate = select(func.count(ViewModel.id))
        stmt = (
            select(ViewModel)
            .offset(calculateOffset(page=pageble.page, page_size=pageble.page_size))
            .limit(pageble.page_size)
        )

        result_set_aggregate = await async_session.execute(stmt_aggregate)
        view_toal = result_set_aggregate.scalar_one()

        result_set = await async_session.execute(stmt)
        views = result_set.scalars().all()

    except IntegrityError as exp_db:
        await async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    return ApiCollectionResponse(
        status="success",
        message="Get all views successfully.",
        data=[
            ViewSchema(
                id=view.id, menu=view.menu, miscellaneous=view.miscellaneous, note=view.note
            )
            for view in views
        ],
        metadata=calculatePaginationParmas(
            page=pageble.page, page_size=pageble.page_size, total=view_toal
        ),
    )


@router.post(
    "",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
    response_model=ApiSingletonResponse[ViewSchema],
    name="Create Menu",
)
async def createMenu(
    payload: CreateViewSchema, cur_user: AuthGuard, async_session: AlchemySession
):
    try:
        stmt = select(ViewModel).where(ViewModel.menu == payload.menu.upper())
        result_set = await async_session.execute(stmt)
        view_data = result_set.scalar_one_or_none()

        if view_data is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Menu is already existed!"
            )

        viewModel = ViewModel()
        viewModel.menu = payload.menu.upper()
        viewModel.miscellaneous = payload.miscellaneous
        viewModel.note = payload.note

        async_session.add(viewModel)
        await async_session.commit()
        await async_session.refresh(viewModel)

    except IntegrityError as exp_db:
        await async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    print_log(
        name=EResource.VIEW.value,
        type="info",
        fname=cur_user.first_name,
        lname=cur_user.last_name,
        msg="attempts to create a view [success].",
    )

    return ApiSingletonResponse(
        status="success",
        message="Create menu successfully.",
        data=ViewSchema(
            id=viewModel.id,
            menu=viewModel.menu,
            miscellaneous=viewModel.miscellaneous,
            note=viewModel.note,
        ),
    )


@router.put(
    "/{view_id}",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
    response_model=ApiSingletonResponse[ViewSchema],
    name="Update view or menu",
)
async def updateMenu(
    view_id: Annotated[int, Path()],
    payload: UpdateViewSchema,
    cur_user: AuthGuard,
    redis_client: RedisClient,
    async_session: AlchemySession,
):
    try:
        stmt = select(ViewModel).where(ViewModel.id == view_id)

        result_set = await async_session.execute(stmt)
        view_data = result_set.scalar_one_or_none()

        if view_data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found!")

        if view_data.menu == payload.menu:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Menu is already existed!"
            )

        filter_keys = {
            field: value
            for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items()
        }

        if len(filter_keys.keys()) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update field")

        for field, value in filter_keys.items():
            setattr(view_data, field, str(value).upper() if field == "menu" else value)

        await async_session.commit()
        await async_session.flush(view_data)

        # -- Removing all cache associated with the following keys
        await RedisCache.removeRedisKeysByPattern(
            redis=redis_client, search_pattern=f"{RedisCacheKey.LOGIN_CACHE_KEY}*"
        )

    except IntegrityError as exp_db:
        await async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    print_log(
        name=EResource.VIEW.value,
        type="info",
        fname=cur_user.first_name,
        lname=cur_user.last_name,
        msg="attempts to update a view [success].",
    )

    return ApiSingletonResponse(
        status="success",
        message="Update menu successfully.",
        data=ViewSchema(
            id=view_data.id,
            menu=view_data.menu,
            miscellaneous=view_data.miscellaneous,
            note=view_data.note,
        ),
    )


@router.post(
    "/add-view",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN, ERole.ADMIN])],
    response_model=ApiSingletonResponse[None],
    name="Add menu to the user",
)
async def addUserViews(
    payload: AddOrRemoveUserViewSchema,
    redis_client: RedisClient,
    cur_user: AuthGuard,
    async_session: AlchemySession,
):
    try:
        stmt_user = (
            select(UserModel)
            .where(UserModel.id == payload.user_id)
            .options(selectinload(UserModel.views))
        )

        result_stmt_user = await async_session.execute(stmt_user)
        user = result_stmt_user.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

            # check if add payload already exist
        for view_id in payload.view_ids:
            is_already_exist = any(view.id == view_id for view in (user.views or []))
            if is_already_exist:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Some menus is already existed!"
                )

        stmt_view = select(ViewModel).where(ViewModel.id.in_(payload.view_ids))
        result_stmt_view = await async_session.execute(stmt_view)
        views = result_stmt_view.scalars().all()

        if len(views) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found any menus which attempt to create!",
            )

        for view in views:
            user.views.append(view)

        await async_session.commit()
        await async_session.flush(user)

        # -- Removing cache login data of the user that we change their view
        cache_key = RedisCache.mergeRedisCacheKey(
            key=RedisCacheKey.LOGIN_CACHE_KEY, optional_key=user.email
        )
        await RedisCache.removeCache(redis_client=redis_client, key=cache_key)

    except IntegrityError as exp_db:
        await async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    print_log(
        name=EResource.VIEW.value,
        type="info",
        fname=cur_user.first_name,
        lname=cur_user.last_name,
        msg="attempts to add views for the user [success].",
    )

    return ApiSingletonResponse(status="success", message="Add some views to user successfully")


@router.delete(
    "{view_id}",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
    response_model=ApiSingletonResponse[ViewSchema],
    name="Delete a particular view",
)
async def deleteView(
    view_id: Annotated[int, Path()],
    cur_user: AuthGuard,
    redis_client: RedisClient,
    async_session: AlchemySession,
):
    try:
        stmt = select(ViewModel).where(ViewModel.id == view_id)
        result_set = await async_session.execute(stmt)
        view = result_set.scalar_one_or_none()

        if view is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="View not found!")

        stale_view = ViewSchema(
            id=view.id, menu=view.menu, miscellaneous=view.miscellaneous, note=view.note
        )

        await async_session.delete(view)
        await async_session.commit()

        # -- delete all relate login cache
        await RedisCache.removeRedisKeysByPattern(
            redis=redis_client, search_pattern=f"{RedisCacheKey.LOGIN_CACHE_KEY}*"
        )

    except IntegrityError as exp_db:
        await async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    print_log(
        name=EResource.VIEW.value,
        type="info",
        fname=cur_user.first_name,
        lname=cur_user.last_name,
        msg="attempts to delete all views [success].",
    )

    return ApiSingletonResponse(status="success", message="Delete successfully.", data=stale_view)


@router.delete(
    "",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
    response_model=ApiSingletonResponse[None],
    name="Delete a view",
)
async def deleteViews(
    redis_client: RedisClient, cur_user: AuthGuard, async_session: AlchemySession
):
    try:
        stmt = delete(ViewModel)
        await async_session.execute(stmt)
        await async_session.commit()

        # -- Removing all cache associated with the following keys | affected all login users
        await RedisCache.removeRedisKeysByPattern(
            redis=redis_client, search_pattern=f"{RedisCacheKey.LOGIN_CACHE_KEY}*"
        )

    except IntegrityError as exp_db:
        await async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    print_log(
        name=EResource.VIEW.value,
        type="info",
        fname=cur_user.first_name,
        lname=cur_user.last_name,
        msg="attempts to delete all views [success].",
    )

    return ApiSingletonResponse(
        status="success", message="Delete all menu successfully.", data=None
    )


@router.delete(
    "/remove-view",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
    response_model=ApiSingletonResponse[None],
    name="Remove views from the user",
)
async def removeViewUser(
    payload: AddOrRemoveUserViewSchema,
    cur_user: AuthGuard,
    redis_client: RedisClient,
    async_session: AlchemySession,
):
    try:
        stmt = (
            select(UserModel)
            .where(UserModel.id == payload.user_id)
            .options(selectinload(UserModel.views))
        )

        result_set = await async_session.execute(stmt)
        user = result_set.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        if len(user.views) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No view to be remove!"
            )

        for view_id in payload.view_ids:
            already_exist = any(view.id == view_id for view in user.views)

        if not already_exist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cannot remove non-existing menu link to the current user!",
            )

        stmt_view = select(ViewModel).where(ViewModel.id.in_(payload.view_ids))
        result_set_view = await async_session.execute(stmt_view)

        views = result_set_view.scalars().all()

        for viewModel in views:
            user.views.remove(viewModel)

        await async_session.commit()

        # -- Removing cache login data of the user that we change their view
        cache_key = RedisCache.mergeRedisCacheKey(
            key=RedisCacheKey.LOGIN_CACHE_KEY, optional_key=user.email
        )
        await RedisCache.removeCache(redis_client=redis_client, key=cache_key)

    except IntegrityError as exp_db:
        await async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    print_log(
        name=EResource.VIEW.value,
        type="info",
        fname=cur_user.first_name,
        lname=cur_user.last_name,
        msg="attempts to remove views from the user [success].",
    )

    return ApiSingletonResponse(
        status="success", message="Remove menu from the user successfully.", data=None
    )


@router.get(
    "/users",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN, ERole.ADMIN])],
    response_model=ApiCollectionResponse[UserMenuSchema],
    name="Get Users link to views",
)
async def userMenu(pageble: Annotated[BasePagination, Query()], async_session: AlchemySession):
    try:
        stmt = (
            select(UserModel)
            .where(UserModel.views.any())
            .offset(calculateOffset(page=pageble.page, page_size=pageble.page_size))
            .limit(pageble.page_size)
            .options(selectinload(UserModel.views))
        )

        result_aggregate_user_menu = await async_session.execute(
            select(func.count(UserModel.id)).where(UserModel.views.any())
        )

        total_user_with_menu = result_aggregate_user_menu.scalar_one()

        result_set = await async_session.execute(stmt)
        users = result_set.scalars().all()

        return ApiCollectionResponse(
            status="success",
            message="Retrieved user menu successfully.",
            data=[
                UserMenuSchema(
                    user_id=u.id,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    email=u.email,
                    views=[
                        ViewSchema(
                            id=v.id, menu=v.menu, miscellaneous=v.miscellaneous, note=v.note
                        )
                        for v in u.views
                    ],
                )
                for u in users
            ]
            if len(users) > 0
            else [],
            metadata=calculatePaginationParmas(
                page=pageble.page, page_size=pageble.page_size, total=total_user_with_menu
            ),
        )

    except IntegrityError as exp_db:
        await async_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )
