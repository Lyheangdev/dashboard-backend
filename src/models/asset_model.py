from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.core_model import CoreModel

if TYPE_CHECKING:
    from src.models.user_model import UserModel


class AssetModel(CoreModel):
    __tablename__ = "asset"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True, comment="Unique identifier"
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("internal_user.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="Relation key",
    )

    file_name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="File upload name"
    )

    file_type: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="File upload extension"
    )

    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="File upload size")

    file_extension: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="File upload extension"
    )

    file_path: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="File access path"
    )

    user: Mapped["UserModel"] = relationship(
        back_populates="asset",
    )
