from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import BaseModel
from src.models.role_permission_model import role_permission_model

if TYPE_CHECKING:
    from src.models.role_model import RoleModel


class PermissionModel(BaseModel):
    __tablename__ = "permission"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True, comment="Unique identifier"
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="Permission action ex: READ:LINE,WRITE:LINE so on.",
    )
    resource: Mapped[str] = mapped_column(
        String(40), nullable=False, comment="Resource, ex: line, project so on."
    )
    roles: Mapped[List["RoleModel"]] = relationship(
        secondary=role_permission_model,
        back_populates="permissions",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"Permission(id={self.id!r}, action={self.action!r}, resource={self.resource!r})"
