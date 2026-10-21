from sqlalchemy import Column, ForeignKey, Table

from src.config.database import BaseModel

role_permission_model = Table(
    "role_permission",
    BaseModel.metadata,
    Column(
        "role_id", ForeignKey("role.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True
    ),
    Column(
        "permission_id",
        ForeignKey("permission.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    ),
)
