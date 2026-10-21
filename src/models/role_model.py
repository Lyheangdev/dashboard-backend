from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import BaseModel
from src.models.role_permission_model import role_permission_model
from src.models.user_role_model import user_role_model

if TYPE_CHECKING:
    from src.models.permission_model import PermissionModel
    from src.models.user_model import UserModel


class RoleModel(BaseModel):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True, comment="Unique identifier"
    )
    role: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="Role, ex: Admin, Editor, Author so on"
    )

    permissions: Mapped[List["PermissionModel"]] = relationship(
        secondary=role_permission_model, back_populates="roles", passive_deletes=True
    )

    users: Mapped[List["UserModel"]] = relationship(
        secondary=user_role_model, back_populates="roles", passive_deletes=True
    )
