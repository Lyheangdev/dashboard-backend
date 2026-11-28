from sqlalchemy import Column, ForeignKey, Table

from src.infrastructure.database.connection import BaseModel

role_view_model = Table(
    "role_view",
    BaseModel.metadata,
    Column(
        "role_id",
        ForeignKey("role.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    ),
    Column(
        "view_id", ForeignKey("view.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True
    ),
)
