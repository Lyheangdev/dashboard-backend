from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import BaseModel


class CoreModel(BaseModel):
    __abstract__ = True

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

    created_by: Mapped[Optional[str]] = mapped_column(String(50), default=None)

    updated_by: Mapped[Optional[str]] = mapped_column(String(50), default=None)
