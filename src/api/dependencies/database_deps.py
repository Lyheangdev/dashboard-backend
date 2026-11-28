from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import PostGresConnector


# Share alchemy session dependency
async def get_alchemy_session(request: Request):
    alchemy_instance: PostGresConnector = request.app.state.alchemy_instance
    async with alchemy_instance.session_factory() as session:
        yield session


AlchemySessionDeps = Annotated[AsyncSession, Depends(get_alchemy_session)]
