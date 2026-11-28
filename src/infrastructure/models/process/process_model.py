from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.models.core.timestamp_model import TimestampModel

if TYPE_CHECKING:
    from src.infrastructure.models.user.user_model import UserModel


class ProcessModel(TimestampModel):
    __tablename__ = "process"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True, comment="Unique identifier"
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("internal_user.id"), nullable=False, comment="User id"
    )

    process: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, comment="process name, ex: SMT, routing,..."
    )

    user: Mapped["UserModel"] = relationship(passive_deletes=True)
