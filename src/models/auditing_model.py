from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import BaseModel


class AuditingModel(BaseModel):
    __tablename__ = "auditing"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True, comment="Unique identifier"
    )

    resource: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        comment="System resource, such role, permission so on"
    )

    action: Mapped[str] = mapped_column(
            String(80),
            nullable=False,
            comment="What action that user perform on the resource"
    )

    status: Mapped[int] = mapped_column(
                SmallInteger,
                nullable=False,
                comment="Status of the action have been made by user"
    )

    user: Mapped[str] = mapped_column(
                String(100),
                nullable=False,
                comment="Who dit the action"
        )

    role: Mapped[str] = mapped_column(
                String(50),
                nullable=False,
                comment="Role of the user"
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("Asia/Phnom_Penh")),
        index=True,
    )