from datetime import datetime
from typing import TYPE_CHECKING, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import BaseModel

if TYPE_CHECKING:
    from models.user_model import UserModel


class LineModel(BaseModel):
    __tablename__ = "production_line"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True, comment="Line unique identifier"
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("internal_user.id"), index=True, nullable=False, comment="User id"
    )
    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="Line name", index=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255), default=None, nullable=True, comment="Line description"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("Asia/Phnom_Penh")),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("Asia/Phnom_Penh")),
        onupdate=lambda: datetime.now(ZoneInfo("Asia/Phnom_Penh")),
    )

    user: Mapped["UserModel"] = relationship(back_populates="lines")

    def __repr__(self):
        return f"LineModel(id={self.id!r},name={self.name!r})"
