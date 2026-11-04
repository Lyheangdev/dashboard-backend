from sqlalchemy import Column, ForeignKey, Table

from src.config.database import BaseModel

user_view_model = Table(
    "user_view",
    BaseModel.metadata,
    Column(
        "user_id",
        ForeignKey("internal_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    ),
    Column(
        "view_id", ForeignKey("view.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True
    ),
)
