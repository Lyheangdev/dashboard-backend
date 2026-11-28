from typing import List, Optional

from pydantic import BaseModel, Field

from src.schema.permission import PermissionSchema
from src.schema.view import ViewSchema


class BaseRoleSchema(BaseModel):
    role: str = Field(min_length=1, max_length=30, description="Role name")


class CreateRoleSchema(BaseRoleSchema):
    remark: str | None = Field(default=None, max_length=255, description="Role remark")
    menus_ids: List[int] | None = Field(default=None, description="menu ids")
    permission_ids: List[int] | None = Field(default=None, description="Permission ids")


class UpdateRoleSchema(BaseModel):
    role: str | None = Field(default=None, max_length=30, description="Role name")
    remark: str | None = Field(default=None, max_length=255, description="Role remark")
    view_ids: Optional[List[int]] = Field(default_factory=list, description="List of menu_id")
    permission_ids: Optional[List[int]] = Field(
        default_factory=list, description="List of permission ids"
    )


class DeleteRoleSchema(BaseModel):
    roles_id: list[int] = Field(default_factory=list, min_length=1, description="role ids")


class RolePermission(BaseModel):
    permission_ids: List[int] = Field(min_length=1, description="Permission ids")


class RoleSchema(BaseRoleSchema):
    id: int | None
    role: str | None = None
    remark: str | None = None
    views: Optional[List[ViewSchema]] = Field(default_factory=list, description="List of menu")
    permissions: Optional[List[PermissionSchema]] = Field(
        default_factory=list, description="List of permission"
    )


class RoleUserSchema(BaseModel):
    id: int
    first_name: str | None
    last_name: str | None
    code: str | None
    email: str


class ConfigUsersRolesSchema(BaseModel):
    users: list[RoleUserSchema] = Field(default_factory=list, description="list of users")
    roles: list[RoleSchema] = Field(default_factory=list, description="list of roles")
