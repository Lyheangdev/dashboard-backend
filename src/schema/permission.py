from pydantic import BaseModel, ConfigDict, Field


class BasePermissionSchema(BaseModel):
    model_config = ConfigDict({"from_attributes": True})
    action: str = Field(min_length=1, max_length=50, description="action name")
    resource: str = Field(min_length=1, max_length=40, description="resource name")


class CreatePermissionSchema(BasePermissionSchema):
    pass


class PermissionSchema(BasePermissionSchema):
    id: int | None
    action: str | None = None
    resource: str | None = None
