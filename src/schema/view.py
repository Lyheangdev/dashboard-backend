from pydantic import BaseModel, Field


class ViewSchema(BaseModel):
    id: int
    menu: str
    miscellaneous: str | None = None
    note: str | None = None


class CreateViewSchema(BaseModel):
    menu: str = Field(min_length=2, max_length=50, description="menu name")
    miscellaneous: str | None = Field(
        default=None, min_length=2, description="comma separated list, can use for submenu"
    )
    note: str | None = Field(default=None, min_length=1, description="Other remark for this menu")


class UpdateViewSchema(BaseModel):
    menu: str | None = Field(default=None, min_length=2, max_length=50, description="menu name")
    miscellaneous: str | None = Field(
        default=None, min_length=2, description="comma separated list, can use for submenu"
    )
    note: str | None = Field(default=None, min_length=1, description="Other remark for this menu")


class AddOrRemoveRoleViewSchema(BaseModel):
    role_id: int
    view_ids: list[int] = Field(min_length=1, description="list id of vew")


class RoleMenuSchema(BaseModel):
    role_id: int
    role: str
    views: list[ViewSchema] = Field(default_factory=list)
