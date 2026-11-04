from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import BaseModel
from src.models.user_view_model import user_view_model

if TYPE_CHECKING:
    from src.models.user_model import UserModel


class ViewModel(BaseModel):
    __tablename__ = "view"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True, comment="Unique identifier"
    )

    menu: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, comment="Menu, ex: Dashboard, Setting, Log"
    )

    miscellaneous: Mapped[str] = mapped_column(
        String(255), nullable=True, comment="other usuful hint"
    )

    note: Mapped[str] = mapped_column(String(80), nullable=True, comment="Other useful note")

    users: Mapped[List["UserModel"]] = relationship(
        secondary=user_view_model, back_populates="views", passive_deletes=True
    )
