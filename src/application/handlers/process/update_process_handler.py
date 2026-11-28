from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.process.update_process_command import UpdateProcessCommand
from src.infrastructure.repositories.process.process_repository import ProcessRepositoy


class UpdateProcessHandler:
    def __init__(self, async_session: AsyncSession, repository: ProcessRepositoy):
        self.async_session = async_session
        self.repository = repository

    async def handle(self, command: UpdateProcessCommand): ...
