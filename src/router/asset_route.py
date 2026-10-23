from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.config.database import AlchemySession
from src.dependencies import AuthGuard
from src.lib.api_enum import ApiTagEnum
from src.lib.api_response import ApiSingletonResponse
from src.models.asset_model import AssetModel
from src.models.user_model import UserModel
from src.schema.asset import AssetSchema

router = APIRouter(prefix="/assets", tags=[ApiTagEnum.ASSETS])

UPLOAD_PATH = Path(__file__).resolve().parent.parent.parent / "assets"
UPLOAD_PATH.mkdir(parents=True, exist_ok=True)

# Allowed extension
allowed_exts = [".png", "jpg", "jpeg", "webp", "avif"]

# Allowed maximum 1KB
allowed_max_size = 1024 * 1024


@router.delete("/my-profile", response_model=ApiSingletonResponse[None], name="Delete my profile")
async def deleteFile(current_user: AuthGuard, async_session: AlchemySession):
    try:
        stmt = (
            select(UserModel)
            .where(UserModel.id == current_user.id)
            .options(selectinload(UserModel.asset))
        )

        result_set = await async_session.execute(stmt)
        user = result_set.scalar_one_or_none()

        if user.asset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No profile to delete!"
            )

        # Delete file from disk first
        file_name = user.asset.file_name
        file_dest_absolute_path = UPLOAD_PATH / file_name

        file_dest_absolute_path.unlink(missing_ok=True)

        # Trigger alchemy orm to delete database
        user.asset = None
        user.asset_identifier = None

        await async_session.commit()

        return ApiSingletonResponse(
            status="success", message="Delete profile successfully.", data=None
        )

    except IntegrityError as exp_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exp_db._message(),
            headers={"DATABASE_ERROR": exp_db.code},
        )

    except HTTPException as exp_http:
        raise exp_http


@router.put(
    "/my-profile", response_model=ApiSingletonResponse[AssetSchema], name="Update my profile"
)
async def uploadMyprofile(
    file: UploadFile, current_user: AuthGuard, async_session: AlchemySession
):
    try:
        # new file upload
        file_ext = Path(file.filename or "").suffix.lower()
        file_size = file.size

        if file_ext in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail=f"Systerm doesn't support this extension: {file_ext}",
            )

        if file_size > allowed_max_size:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="Your uploaded file is too big, allowed only maximum 1 MB.",
            )

        stmt = (
            select(UserModel)
            .where(UserModel.id == current_user.id)
            .options(selectinload(UserModel.asset))
        )

        result_set = await async_session.execute(stmt)
        user = result_set.scalar_one_or_none()

        if user.asset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found!"
            )

        old_file_name = user.asset.file_name
        file_dest_absolute_path = UPLOAD_PATH / old_file_name

        # omit old remove from disk
        file_dest_absolute_path.unlink(missing_ok=True)

        random_name = uuid4().hex
        file_name = f"svi_aec_{random_name}{file_ext}"
        file_dest_absolute_path = UPLOAD_PATH / file_name
        accessible_path = f"/assets/{file_name}"

        user.asset.file_name = file_name
        user.asset.file_size = file_size
        user.asset.file_type = file.content_type
        user.asset.file_extension = file_ext
        user.asset.file_path = accessible_path
        user.asset.updated_by = f"{current_user.first_name} {current_user.last_name}"

        user.asset_identifier = accessible_path

        await async_session.commit()
        await async_session.refresh(user, attribute_names=["asset"])

        with file_dest_absolute_path.open("wb") as upload_destination:
            while binary_chunk := await file.read(1024 * 1024):
                upload_destination.write(binary_chunk)

        return ApiSingletonResponse(
            status="success",
            message="Ok",
            data=AssetSchema(
                file_name=user.asset.file_name,
                file_type=user.asset.file_type,
                file_size=user.asset.file_size,
                path=user.asset.file_path,
                created_at=user.asset.created_at,
                updated_at=user.asset.updated_at,
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


@router.post(
    "/my-profile/upload",
    response_model=ApiSingletonResponse[AssetSchema],
    name="Upload my profile",
)
async def uploadFileByte(
    file: UploadFile, current_user: AuthGuard, async_session: AlchemySession
):

    file_ext = Path(file.filename or "").suffix.lower()
    file_size = file.size

    if file_ext in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=f"Systerm doesn't support this extension: {file_ext}",
        )

    if file_size > allowed_max_size:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Your uploaded file is too big, allowed only maximum 1 MB.",
        )

    random_name = uuid4().hex
    file_name = f"svi_aec_{random_name}{file_ext}"
    file_dest_absolute_path = UPLOAD_PATH / file_name

    accessible_path = f"/assets/{file_name}"

    try:
        stmt = (
            select(UserModel)
            .where(UserModel.id == current_user.id)
            .options(selectinload(UserModel.asset))
        )

        result_set = await async_session.execute(stmt)
        user = result_set.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something went wrong for this file upload!",
            )

        if user.asset is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This file is already uploaded by this user!",
            )

        # Create asset object
        asset = AssetModel()
        asset.file_name = file_name
        asset.file_size = file_size
        asset.file_type = file.content_type
        asset.file_extension = file_ext
        asset.file_path = accessible_path
        asset.created_by = f"{current_user.first_name} {current_user.last_name}"

        user.asset = asset
        user.asset_identifier = accessible_path
        await async_session.commit()
        await async_session.refresh(user, attribute_names=["asset"])

        with file_dest_absolute_path.open("wb") as upload_destination:
            while binary_chunk := await file.read(1024 * 1024):
                upload_destination.write(binary_chunk)

        return ApiSingletonResponse(
            status="success",
            message="Ok",
            data=AssetSchema(
                file_name=user.asset.file_name,
                file_type=user.asset.file_type,
                file_size=user.asset.file_size,
                path=user.asset.file_path,
                created_at=user.asset.created_at,
                updated_at=user.asset.updated_at,
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
