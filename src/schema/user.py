from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.lib.api_response import BasePagination, Pagination
from src.schema.role import RoleSchema

UserSortByField = Literal["email", "created_at"]


class UserPagination(Pagination):
    sort_by: UserSortByField | None = None
    search: str | None = Field(default=None, description="Search by email")


class BaseUserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    bio: str | None = None


class UserSchema(BaseUserSchema):
    id: int | None
    role: RoleSchema | None = None
    asset_identifier: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CreateUserSchema(BaseUserSchema):
    first_name: str = Field(min_length=1, max_length=20, description="User first name")
    last_name: str = Field(min_length=1, max_length=20, description="User last name")
    email: EmailStr = Field(description="User email address")
    password: str = Field(min_length=8, max_length=20, description="User password")
    bio: str | None = Field(default=None, max_length=255, description="User personal biology")


class UpdateUserSchema(BaseUserSchema):
    first_name: str | None = Field(default=None, max_length=20, description="User first name")
    last_name: str | None = Field(default=None, max_length=20, description="User last name")
    email: EmailStr | None = Field(default=None, description="User email address")
    bio: str | None = Field(default=None, max_length=255, description="User personal biology")


class SystemAccessQueryParams(BasePagination):
    role_id: int | None = Field(default=None)
