from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.api.dependencies.cache_deps import RedisClientDeps
from src.api.dependencies.database_deps import AlchemySessionDeps
from src.dependencies import AuthGuard, AuthorizeGuard
from src.domain.dtos.response_dtos import (
    ApiCollectionResponse,
    ApiSingletonResponse,
    BasePagination,
)
from src.domain.enums.authorities_enum import EResource, ERole
from src.domain.enums.cach_key_enum import ECacheKey
from src.domain.enums.endpoint_tag_enum import EApiTag
from src.domain.utils.cache.redis_helper import RedisCache
from src.domain.utils.pagination_helper import calculateOffset, calculatePaginationParmas
from src.infrastructure.logging.config import print_log
from src.infrastructure.models.role.role_model import RoleModel
from src.infrastructure.models.view.view_model import ViewModel
from src.schema.view import (
    AddOrRemoveRoleViewSchema,
    CreateViewSchema,
    RoleMenuSchema,
    UpdateViewSchema,
    ViewSchema,
)

router = APIRouter(prefix="/admin/menus", tags=[EApiTag.MENU_VIEW])


@router.get(
    "",
    response_model=ApiCollectionResponse[ViewSchema],
    name="Get all menu",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN, ERole.ADMIN])],
)
async def getAllViews(
    _: AuthGuard, pageble: Annotated[BasePagination, Query()], async_session: AlchemySessionDeps
):
    try:
        async with async_session.begin():
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
    response_model=ApiSingletonResponse[ViewSchema],
    name="Create Menu",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def createMenu(
    payload: CreateViewSchema, cur_user: AuthGuard, async_session: AlchemySessionDeps
):
    try:
        async with async_session.begin():
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
            await async_session.refresh(viewModel)

    except IntegrityError as exp_db:
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
    response_model=ApiSingletonResponse[ViewSchema],
    name="Update view or menu",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def updateMenu(
    view_id: Annotated[int, Path()],
    payload: UpdateViewSchema,
    cur_user: AuthGuard,
    redis_client: RedisClientDeps,
    async_session: AlchemySessionDeps,
):
    try:
        async with async_session.begin():
            stmt = select(ViewModel).where(ViewModel.id == view_id)

            result_set = await async_session.execute(stmt)
            view_data = result_set.scalar_one_or_none()

            if view_data is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found!"
                )

            if view_data.menu == payload.menu:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Menu is already existed!"
                )

            filter_keys = {
                field: value
                for field, value in payload.model_dump(
                    exclude_unset=True, exclude_none=True
                ).items()
            }

            if len(filter_keys.keys()) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="No update field"
                )

            for field, value in filter_keys.items():
                setattr(view_data, field, str(value).upper() if field == "menu" else value)

            await async_session.flush(view_data)

            # -- Removing all cache associated with the following keys
            await RedisCache.removeRedisKeysByPattern(
                redis=redis_client, search_pattern=f"{ECacheKey.LOGIN.value}*"
            )

    except IntegrityError as exp_db:
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
    response_model=ApiSingletonResponse[None],
    name="Add some menus to the role",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN, ERole.ADMIN])],
)
async def addUserViews(
    payload: AddOrRemoveRoleViewSchema,
    redis_client: RedisClientDeps,
    cur_user: AuthGuard,
    async_session: AlchemySessionDeps,
):
    try:
        async with async_session.begin():
            stmt_user = (
                select(RoleModel)
                .where(RoleModel.id == payload.role_id)
                .options(selectinload(RoleModel.views))
            )

            result_stmt_role = await async_session.execute(stmt_user)
            role = result_stmt_role.scalar_one_or_none()

            if role is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Role not found!"
                )

                # check if add payload already exist
            for view_id in payload.view_ids:
                is_already_exist = any(view.id == view_id for view in (role.views or []))
                if is_already_exist:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Some menus is already existed!",
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
                role.views.append(view)

            await async_session.flush(role)

    except IntegrityError as exp_db:
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
        msg="attempts to add views for the role [success].",
    )
    return ApiSingletonResponse(status="success", message="Add some views to role successfully")


@router.delete(
    "{view_id}",
    response_model=ApiSingletonResponse[ViewSchema],
    name="Delete a particular view",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def deleteView(
    view_id: Annotated[int, Path()],
    cur_user: AuthGuard,
    redis_client: RedisClientDeps,
    async_session: AlchemySessionDeps,
):
    try:
        async with async_session.begin():
            stmt = select(ViewModel).where(ViewModel.id == view_id)
            result_set = await async_session.execute(stmt)
            view = result_set.scalar_one_or_none()

            if view is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="View not found!"
                )

            stale_view = ViewSchema(
                id=view.id, menu=view.menu, miscellaneous=view.miscellaneous, note=view.note
            )

            await async_session.delete(view)

            # -- delete all relate login cache
            await RedisCache.removeRedisKeysByPattern(
                redis=redis_client, search_pattern=f"{ECacheKey.LOGIN.value}*"
            )

    except IntegrityError as exp_db:
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
    response_model=ApiSingletonResponse[None],
    name="Delete all views",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN])],
)
async def deleteViews(
    redis_client: RedisClientDeps, cur_user: AuthGuard, async_session: AlchemySessionDeps
):
    try:
        async with async_session.begin():
            stmt = delete(ViewModel)
            await async_session.execute(stmt)

            # -- Removing all cache associated with the following keys | affected all login users
            await RedisCache.removeRedisKeysByPattern(
                redis=redis_client, search_pattern=f"{ECacheKey.LOGIN.value}*"
            )

    except IntegrityError as exp_db:
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


@router.get(
    "/roles",
    response_model=ApiCollectionResponse[RoleMenuSchema],
    name="Get roles link to the views",
    dependencies=[AuthorizeGuard(roles=[ERole.SUPERADMIN, ERole.ADMIN])],
)
async def userMenu(
    pageble: Annotated[BasePagination, Query()], async_session: AlchemySessionDeps
):
    try:
        async with async_session.begin():
            stmt = (
                select(RoleModel)
                .where(RoleModel.views.any())
                .offset(calculateOffset(page=pageble.page, page_size=pageble.page_size))
                .limit(pageble.page_size)
                .options(selectinload(RoleModel.views))
            )

            result_aggregate_role_menu = await async_session.execute(
                select(func.count(RoleModel.id)).where(RoleModel.views.any())
            )
            result_set = await async_session.execute(stmt)

            total_role_with_menu = result_aggregate_role_menu.scalar_one()
            roles = result_set.scalars().all()

    except IntegrityError as exp_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    return ApiCollectionResponse(
        status="success",
        message="Retrieved roles successfully.",
        data=[
            RoleMenuSchema(
                role_id=r.id,
                role=r.role,
                views=[
                    ViewSchema(id=v.id, menu=v.menu, miscellaneous=v.miscellaneous, note=v.note)
                    for v in r.views
                ],
            )
            for r in roles
        ]
        if len(roles) > 0
        else [],
        metadata=calculatePaginationParmas(
            page=pageble.page, page_size=pageble.page_size, total=total_role_with_menu
        ),
    )
