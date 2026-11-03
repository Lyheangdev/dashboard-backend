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


class AddOrRemoveUserViewSchema(BaseModel):
    user_id: int
    view_ids: list[int] = Field(min_length=1, description="list id of vew")


class UserMenuSchema(BaseModel):
    user_id: int
    first_name: str | None = None
    last_name: str | None = None
    email: str
    views: list[ViewSchema] = Field(default_factory=list)
