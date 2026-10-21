from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetSchema(BaseModel):
    model_config = ConfigDict({"from_attributes": True})

    file_name: str | None = None
    file_type: str | None = None
    file_size: int | None = None
    path: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
