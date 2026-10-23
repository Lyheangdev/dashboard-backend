from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AccessTokenScheme(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthLogin(BaseModel):
    email: EmailStr = Field(description="Mail for authenticating user into system")
    password: str = Field(
        min_length=8, max_length=20, description="Login password must be at least 8 characters"
    )


class AuthUserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str | None = None
    bio: str | None = None
    profile_url: str | None = None
    role: str | None = None
    isBanned: bool = False
    status: int | None = None
    code: str | None = None
    permissions: list[str] | None = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
