from sqlalchemy.ext.asyncio import AsyncSession

from src.application.queries.process.get_process_query import GetProcessQuery
from src.infrastructure.repositories.process.process_repository import ProcessRepositoy


class GetProcessHandler:
    def __init__(self, async_session: AsyncSession, repository: ProcessRepositoy):
        self.async_session = async_session
        self.repository = repository

    async def handle(self, query: GetProcessQuery): ...
