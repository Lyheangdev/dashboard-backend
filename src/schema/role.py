from typing import List, Optional

from pydantic import BaseModel, Field

from src.schema.permission import PermissionSchema


class BaseRoleSchema(BaseModel):
    role: str = Field(min_length=1, max_length=30, description="Role name")


class CreateRoleSchema(BaseRoleSchema):
    permission_ids: List[int] | None = Field(default=None, description="Permission ids")


class UpdateRoleSchema(BaseRoleSchema):
    role: str | None = Field(default=None, max_length=30, description="Role name")


class RolePermission(BaseModel):
    permission_ids: List[int] = Field(min_length=1, description="Permission ids")


class RoleSchema(BaseRoleSchema):
    id: int | None
    role: str | None = None
    permissions: Optional[List[PermissionSchema]] = Field(
        default_factory=list, description="List of permission"
    )
