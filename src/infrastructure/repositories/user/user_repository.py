from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.models.role.role_model import RoleModel
from src.infrastructure.models.user.user_model import UserModel


class UserRepositoy:
    def __init__(self, asyn_session: AsyncSession):
        self.session = asyn_session

    async def findUserByEmail(self, email: str) -> UserModel | None:
        stmt = (
            select(UserModel)
            .where(UserModel.email == email)
            .options(
                selectinload(UserModel.roles).selectinload(RoleModel.permissions),
                selectinload(UserModel.roles).selectinload(RoleModel.views),
            )
        )
        submit_script = await self.session.execute(stmt)
        return submit_script.scalar_one_or_none()

    async def findUserById(self, id: int) -> UserModel | None:
        stmt = (
            select(UserModel)
            .where(UserModel.id == id)
            .options(
                selectinload(UserModel.roles).selectinload(RoleModel.permissions),
                selectinload(UserModel.roles).selectinload(RoleModel.views),
            )
        )
        submit_script = await self.session.execute(stmt)
        return submit_script.scalar_one_or_none()
