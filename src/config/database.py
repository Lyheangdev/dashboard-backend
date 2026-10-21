
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config.logging import get_logger

logger = get_logger(__name__)


class BaseModel(DeclarativeBase):
    pass


class PostGresConnector:
    HOST = "localhost"
    PORT = 5432
    USERNAME = "minghua"
    PASSWORD = "progres_test"
    INITIAL_DATABASE = "dashboard_tst"

    CONNECTION_STRING = (
        f"postgresql+asyncpg://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{INITIAL_DATABASE}"
    )

    def __init__(self):
        
        logger.info("🏁 SQLALCHYMY Start initializing.")
        self.async_engine = create_async_engine(url=self.CONNECTION_STRING, echo=True)
        self.session_factory = async_sessionmaker(
            bind=self.async_engine, class_=AsyncSession, expire_on_commit=False
        )

    async def initilizeConnection(self):
        try:
            async with self.async_engine.connect() as connection:
                await connection.execute(text("SELECT 1"))

            logger.info("✅ Test postgres connection get successfully.")

        except Exception as e:
            logger.exception("‼️ Failed to start connecting with postgress database!")

            if self.async_engine is not None:
                await self.async_engine.dispose()
            raise e

    async def releaseAlchemyInstance(self):
        await self.async_engine.dispose()
        logger.info("🔚 SQLALCHYMY Released.")


# Share alchemy session dependency
async def alchemy_session(request: Request):
    alchemy_instance: PostGresConnector = request.app.state.alchemy_instance
    async with alchemy_instance.session_factory() as session:
        yield session


AlchemySession = Annotated[AsyncSession, Depends(alchemy_session)]
