from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.core_model import CoreModel
from src.models.user_role_model import user_role_model

if TYPE_CHECKING:
    from src.models.asset_model import AssetModel
    from src.models.line_model import LineModel
    from src.models.role_model import RoleModel


class UserModel(CoreModel):
    __tablename__ = "internal_user"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True, comment="User unique identifier"
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(20), default=None, nullable=True, comment="User first name"
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(20), default=None, nullable=True, comment="User last name"
    )
    email: Mapped[str] = mapped_column(
        String(60), unique=True, nullable=False, index=True, comment="User email address"
    )
    password: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="User hashed password"
    )

    bio: Mapped[Optional[str]] = mapped_column(String(255), default=None, nullable=True)

    asset_identifier: Mapped[Optional[str]] = mapped_column(
        String(255), default=None, nullable=True
    )

    code: Mapped[Optional[str]] = mapped_column(
        String(40),
        nullable=True,
        unique=True,
    )

    isBanned: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True, server_default="false"
    )

    status: Mapped[int] = mapped_column(
        SmallInteger, default=0, nullable=False, index=True, server_default="0"
    )

    asset: Mapped["AssetModel"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False, passive_deletes=True
    )

    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("internal_user.id"), nullable=True
    )

    creator: Mapped["UserModel"] = relationship(
        back_populates="created_users", remote_side="UserModel.id"
    )

    created_users: Mapped[List["UserModel"]] = relationship(back_populates="creator")

    lines: Mapped[List["LineModel"]] = relationship(back_populates="user")
    roles: Mapped[List["RoleModel"]] = relationship(
        secondary=user_role_model, back_populates="users", passive_deletes=True
    )

    def __repr__(self):
        id = f"id={self.id!r}"
        first_name = f"first_name={self.first_name!r}"
        last_name = f"last_name={self.last_name!r}"
        return f"UserModel({id},{first_name},{last_name})"
