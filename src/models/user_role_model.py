from sqlalchemy import Column, ForeignKey, Table

from src.config.database import BaseModel

user_role_model = Table(
    "user_role",
    BaseModel.metadata,
    Column(
        "user_id",
        ForeignKey("internal_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id", ForeignKey("role.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True
    ),
)
