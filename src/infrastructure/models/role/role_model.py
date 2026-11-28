from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.connection import BaseModel
from src.infrastructure.models.junctions.role_permission_model import role_permission_model
from src.infrastructure.models.junctions.role_view_model import role_view_model
from src.infrastructure.models.junctions.user_role_model import user_role_model

if TYPE_CHECKING:
    from src.infrastructure.models.permission.permission_model import PermissionModel
    from src.infrastructure.models.user.user_model import UserModel
    from src.infrastructure.models.view.view_model import ViewModel


class RoleModel(BaseModel):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True, comment="Unique identifier"
    )

    role: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="Role, ex: Admin, Editor, Author so on"
    )

    remark: Mapped[str] = mapped_column(
        String(255), nullable=True, comment="More descriptive content about a role"
    )

    permissions: Mapped[List["PermissionModel"]] = relationship(
        secondary=role_permission_model, back_populates="roles", passive_deletes=True
    )

    users: Mapped[List["UserModel"]] = relationship(
        secondary=user_role_model, back_populates="roles", passive_deletes=True
    )

    views: Mapped[List["ViewModel"]] = relationship(
        secondary=role_view_model, back_populates="roles", passive_deletes=True
    )
